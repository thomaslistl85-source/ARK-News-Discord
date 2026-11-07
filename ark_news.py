
import os
import json
import time
from pathlib import Path

import requests
from deep_translator import GoogleTranslator


# =====================================
# EINSTELLUNGEN
# =====================================

APP_ID = 2399830

WEBHOOK = os.environ["DISCORD_WEBHOOK_URL"]

STATE_FILE = Path("ark_news_state.json")

API = (
    "https://api.steampowered.com/"
    "ISteamNews/GetNewsForApp/v2/"
)

TEST_DISCORD = os.getenv("TEST_DISCORD", "0") == "1"


# =====================================
# DISCORD-NACHRICHT SENDEN
# =====================================

def send_discord(message):
    response = requests.post(
        WEBHOOK,
        json={
            "content": message,
            "allowed_mentions": {"parse": []}
        },
        timeout=30
    )

    response.raise_for_status()
    print("Discord-Nachricht erfolgreich gesendet.")


# =====================================
# ÜBERSETZUNG
# =====================================

def translate(text):
    if not text:
        return ""

    try:
        translator = GoogleTranslator(
            source="auto",
            target="de"
        )

        parts = []

        for start in range(0, len(text), 4500):
            part = text[start:start + 4500]

            translated = translator.translate(part)
            parts.append(translated or part)

            time.sleep(2)

        return "".join(parts)

    except Exception as e:
        print("Übersetzung fehlgeschlagen:", e)
        return text


# =====================================
# ARK-NEWS ABRUFEN
# =====================================

def main():

    # Manueller Discord-Test
    if TEST_DISCORD:
        send_discord(
            "🦖 **ARK-News-Bot – Funktionstest**\n\n"
            "✅ Verbindung zu Discord erfolgreich!\n"
            "🇩🇪 Diese Testnachricht ist auf Deutsch.\n"
            "📢 Der ARK-News-Bot ist einsatzbereit.\n\n"
            "Automatische Prüfung: alle 30 Minuten."
        )

        print("Discord-Test abgeschlossen.")

    # News von Steam abrufen
    response = requests.get(
        API,
        params={
            "appid": APP_ID,
            "count": 20,
            "maxlength": 0
        },
        timeout=30
    )

    response.raise_for_status()

    news = response.json()["appnews"]["newsitems"]

    # Bereits bekannte Nachrichten laden
    if STATE_FILE.exists():
        state = json.loads(
            STATE_FILE.read_text(encoding="utf-8")
        )

        seen = set(state.get("seen", []))

    else:
        seen = set()

        # Beim ersten Start keine alten News posten
        seen.update(item["gid"] for item in news)

        print("Erster Start: Alte News gespeichert.")

    # Neue ARK-News verarbeiten
    for item in reversed(news):

        gid = item["gid"]

        if gid in seen:
            continue

        title = translate(
            item.get("title", "ARK-News")
        )

        content = translate(
            item.get("contents", "")
        )

        url = item.get("url", "")

        header = "🦖 **Neue offizielle ARK-News**\n\n"
        footer = f"\n\n🔗 {url}"
        title_line = f"**{title}**\n\n"

        available = (
            2000
            - len(header)
            - len(title_line)
            - len(footer)
        )

        if available < 0:
            title = title[:150] + "..."
            title_line = f"**{title}**\n\n"

            available = (
                2000
                - len(header)
                - len(title_line)
                - len(footer)
            )

        if len(content) > available:
            content = content[:max(0, available - 3)] + "..."

        message = header + title_line + content + footer

        send_discord(message)

        seen.add(gid)

        # Nachrichtenstand speichern
        STATE_FILE.write_text(
            json.dumps(
                {"seen": sorted(seen)},
                indent=2
            ),
            encoding="utf-8"
        )

        print("Veröffentlicht:", title)

    # Nachrichtenstand speichern
    STATE_FILE.write_text(
        json.dumps(
            {"seen": sorted(seen)},
            indent=2
        ),
        encoding="utf-8"
    )

    print("ARK-News-Prüfung abgeschlossen.")


if __name__ == "__main__":
    main()
