
import os
import json
import time
from pathlib import Path

import requests
from deep_translator import GoogleTranslator

# Einstellungen
APP_ID = 2399830
WEBHOOK = os.environ["DISCORD_WEBHOOK_URL"]
STATE_FILE = Path("ark_news_state.json")

API = "https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/"

# Übersetzung
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

            # Pause zwischen Übersetzungsanfragen
            time.sleep(2)

        return "".join(parts)

    except Exception as e:
        print("Übersetzung fehlgeschlagen:", e)
        return text


def main():
    # Offizielle ARK-News abrufen
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

    # Bereits veröffentlichte Nachrichten laden
    if STATE_FILE.exists():
        state = json.loads(
            STATE_FILE.read_text(encoding="utf-8")
        )
        seen = set(state.get("seen", []))

    else:
        seen = set()

        # Beim ersten Start alte News nicht posten
        seen.update(item["gid"] for item in news)

        print("Erster Start: Vorhandene News gespeichert.")

    # Neue Nachrichten verarbeiten
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

        # Discord: maximal 2000 Zeichen
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

        # Nachricht an Discord senden
        result = requests.post(
            WEBHOOK,
            json={
                "content": message,
                "allowed_mentions": {
                    "parse": []
                }
            },
            timeout=30
        )

        result.raise_for_status()

        # Nachricht als veröffentlicht markieren
        seen.add(gid)

        print("Veröffentlicht:", title)

        # Nachrichtenstand direkt speichern
        STATE_FILE.write_text(
            json.dumps(
                {"seen": sorted(seen)},
                indent=2
            ),
            encoding="utf-8"
        )

    # Auch beim ersten Start speichern
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

