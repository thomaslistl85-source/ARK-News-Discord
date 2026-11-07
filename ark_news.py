
import os
import re
import json
import time
import hashlib
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator


APP_ID = 2399830
WEBHOOK = os.environ["DISCORD_WEBHOOK_URL"]
TEST_DISCORD = os.getenv("TEST_DISCORD", "0") == "1"

STEAM_STATE = Path("ark_news_state.json")
PATCH_STATE = Path("ark_patch_state.json")

STEAM_API = (
    "https://api.steampowered.com/"
    "ISteamNews/GetNewsForApp/v2/"
)

PATCH_PAGES = {
    "server": {
        "name": "ARK ASA Server-Patchnotes",
        "url": (
            "https://survivetheark.com/index.php?/"
            "forums/topic/773786-asa-server-patch-notes-"
            "server-v966-updated-10282026/"
        )
    },
    "client": {
        "name": "ARK ASA PC-Patchnotes",
        "url": (
            "https://survivetheark.com/index.php?/"
            "forums/topic/708761-asa-pc-patch-notes-"
            "client-v947-updated-09302026/"
        )
    }
}

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 ARK-News-Discord/1.0"
})


def load_state(path):
    if not path.exists():
        return None

    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path, data):
    path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


def send_discord(message):
    response = session.post(
        WEBHOOK,
        json={
            "content": message[:2000],
            "allowed_mentions": {"parse": []}
        },
        timeout=30
    )
    response.raise_for_status()
    print("Discord-Nachricht gesendet.")


def translate(text):
    if not text:
        return ""

    try:
        translator = GoogleTranslator(
            source="auto",
            target="de"
        )

        result = []

        for start in range(0, len(text), 3000):
            chunk = text[start:start + 3000]
            result.append(
                translator.translate(chunk) or chunk
            )
            time.sleep(2)

        return "\n".join(result)

    except Exception as error:
        print("Übersetzung fehlgeschlagen:", error)
        return text


def make_message(header, title, content, url):
    prefix = f"{header}\n\n**{title}**\n\n"
    suffix = f"\n\n🔗 Vollständige Meldung:\n{url}"

    space = max(0, 2000 - len(prefix) - len(suffix))

    if len(content) > space:
        content = content[:max(0, space - 3)] + "..."

    return (prefix + content + suffix)[:2000]


def check_steam():
    print("Prüfe Steam-News ...")

    response = session.get(
        STEAM_API,
        params={
            "appid": APP_ID,
            "count": 20,
            "maxlength": 0
        },
        timeout=30
    )
    response.raise_for_status()

    news = response.json()["appnews"]["newsitems"]
    state = load_state(STEAM_STATE)

    if state is None:
        save_state(
            STEAM_STATE,
            {"seen": [item["gid"] for item in news]}
        )
        print("Steam: Erstbestand gespeichert.")
        return

    seen = set(state.get("seen", []))

    for item in reversed(news):
        gid = item["gid"]

        if gid in seen:
            continue

        title = translate(item.get("title", "ARK-News"))

        raw_content = item.get("contents", "")
        content = re.sub(r"\[/?[^\]]+\]", "", raw_content)
        content = translate(content[:6000])

        message = make_message(
            "🦖 **Neue offizielle ARK-News**",
            title,
            content,
            item.get("url", "")
        )

        send_discord(message)
        seen.add(gid)

        save_state(
            STEAM_STATE,
            {"seen": sorted(seen)}
        )

        print("Steam-News veröffentlicht:", title)


def get_patch_text(url):
    response = session.get(url, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    # Nur den ersten Forumsbeitrag auswerten.
    post = soup.select_one(
        "article .cPost_content, "
        "article .ipsType_richText, "
        ".cPost_content, "
        ".ipsType_richText"
    )

    if post is None:
        raise RuntimeError(
            "Patchnotes-Inhalt nicht gefunden."
        )

    for element in post.select(
        "script, style, blockquote"
    ):
        element.decompose()

    text = post.get_text(
        separator="\n",
        strip=True
    )

    text = re.sub(r"\n{3,}", "\n\n", text)

    if len(text) < 100:
        raise RuntimeError(
            "Patchnotes-Inhalt ist zu kurz."
        )

    return text


def check_patchnotes():
    print("Prüfe offizielle Patchnotes ...")

    state = load_state(PATCH_STATE)
    first_run = state is None

    if first_run:
        state = {}

    for key, page in PATCH_PAGES.items():
        try:
            text = get_patch_text(page["url"])

            digest = hashlib.sha256(
                text.encode("utf-8")
            ).hexdigest()

            previous = state.get(key)

            if previous == digest:
                print(page["name"], "unverändert.")
                continue

            if first_run or previous is None:
                state[key] = digest
                save_state(PATCH_STATE, state)

                print(
                    page["name"],
                    "erstmalig gespeichert."
                )
                continue

            # Der erste Abschnitt enthält normalerweise
            # die neuesten Änderungen.
            excerpt = text[:2400]
            translated = translate(excerpt)

            message = make_message(
                "🔧 **Offizielle ARK-Patchnotes aktualisiert**",
                page["name"],
                translated,
                page["url"]
            )

            send_discord(message)

            state[key] = digest
            save_state(PATCH_STATE, state)

            print(
                "Patchnotes veröffentlicht:",
                page["name"]
            )

        except Exception as error:
            print(
                "Fehler bei",
                page["name"],
                ":",
                error
            )


def main():
    if TEST_DISCORD:
        send_discord(
            "🦖 **ARK-News-Bot – Funktionstest**\n\n"
            "✅ Discord-Verbindung funktioniert.\n"
            "🇩🇪 Deutscher Test erfolgreich.\n"
            "🔧 Patchnotes-Überwachung ist eingerichtet."
        )

    # Beide Quellen unabhängig prüfen.
    try:
        check_steam()
    except Exception as error:
        print("Steam-Fehler:", error)

    check_patchnotes()

    print("ARK-News-Prüfung abgeschlossen.")


if __name__ == "__main__":
    main()

