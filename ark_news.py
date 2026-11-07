
import os
import json
from pathlib import Path

import requests
from deep_translator import GoogleTranslator

APP_ID = 2399830
WEBHOOK = os.environ["DISCORD_WEBHOOK_URL"]
STATE_FILE = Path("ark_news_state.json")

API = "https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/"


def translate(text):
    if not text:
        return ""

    try:
        translator = GoogleTranslator(source="auto", target="de")
        # Übersetzung in Abschnitten wegen der Zeichenbegrenzung
        parts = []
        for start in range(0, len(text), 4000):
            parts.append(translator.translate(text[start:start + 4000]))
        return "".join(parts)
    except Exception as e:
        print("Übersetzung fehlgeschlagen:", e)
        return text


def main():
    response = requests.get(
        API,
        params={"appid": APP_ID, "count": 20, "maxlength": 0},
        timeout=30
    )
    response.raise_for_status()
    news = response.json()["appnews"]["newsitems"]

    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        seen = set(state.get("seen", []))
    else:
        seen = set()
        # Beim ersten Start keine alten Nachrichten posten
        seen.update(item["gid"] for item in news)
        print("Erster Start: Vorhandene News gespeichert.")

    for item in reversed(news):
        gid = item["gid"]

        if gid in seen:
            continue

        title = translate(item.get("title", "ARK-News"))
        content = translate(item.get("contents", ""))
        url = item.get("url", "")

        # Discord erlaubt maximal 2000 Zeichen pro Nachricht
        # Etwas Platz für Überschrift und Link reservieren
        header = "🦖 **Neue offizielle ARK-News**\n\n"
        footer = f"\n\n🔗 {url}"
        title_line = f"**{title}**\n\n"

        available = 2000 - len(header) - len(title_line) - len(footer)

        if available < 0:
            title = title[:150] + "..."
            title_line = f"**{title}**\n\n"
            available = 2000 - len(header) - len(title_line) - len(footer)

        if len(content) > available:
            content = content[:max(0, available - 3)] + "..."

        message = header + title_line + content + footer

        result = requests.post(
            WEBHOOK,
            json={
                "content": message,
                "allowed_mentions": {"parse": []}
            },
            timeout=30
        )
        result.raise_for_status()

        seen.add(gid)
        print("Veröffentlicht:", title)

    STATE_FILE.write_text(
        json.dumps({"seen": sorted(seen)}, indent=2),
        encoding="utf-8"
    )
    print("ARK-News-Prüfung abgeschlossen.")


if __name__ == "__main__":
    main()

