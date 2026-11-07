
import os
import json
from pathlib import Path

import requests
from deep_translator import GoogleTranslator

APP_ID = 2399830
WEBHOOK = os.environ["DISCORD_WEBHOOK_URL"]
STATE_FILE = Path("ark_news_state.json")

API = "https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/"

response = requests.get(
    API,
    params={"appid": APP_ID, "count": 20, "maxlength": 0},
    timeout=30,
)
response.raise_for_status()

news = response.json()["appnews"]["newsitems"]

# Bereits veröffentlichte News laden
if STATE_FILE.exists():
    state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    seen = set(state.get("seen", []))
else:
    seen = set()

# Beim ersten Start nur vorhandene Meldungen merken.
# Keine alten Nachrichten nachträglich posten.
if not STATE_FILE.exists():
    seen.update(item["gid"] for item in news)
    print("Erster Start: Vorhandene News gespeichert.")
else:
    for item in reversed(news):
        gid = item["gid"]

        if gid in seen:
            continue

       
            title = item["title"]
            url = item["url"]

            try:
                title = GoogleTranslator(
                    source="auto",
                    target="de"
                ).translate(title)
            except Exception as e:
                print(f"Übersetzung fehlgeschlagen: {e}")

            message = (
                "🦖 **Neue offizielle ARK-News**\n\n"
                f"**{title}**\n\n"
                f"🔗 {url}"
            )


        result = requests.post(
            WEBHOOK,
            json={
                "content": message,
                "allowed_mentions": {"parse": []},
            },
            timeout=30,
        )
        result.raise_for_status()

        seen.add(gid)
        print("Veröffentlicht:", title)

STATE_FILE.write_text(
    json.dumps({"seen": sorted(seen)}, indent=2),
    encoding="utf-8",
)

print("ARK-News-Prüfung abgeschlossen.")

# Einmaliger Discord-Übersetzungstest
if os.environ.get("TEST_DISCORD") == "1":
    response = requests.post(
        WEBHOOK,
        json={
            "content": (
                "🦖 ARK News Translation Test\n"
                "The ARK servers are back online. "
                "A new update is available."
            ),
            "allowed_mentions": {"parse": []},
        },
        timeout=30,
    )
    response.raise_for_status()
    print("Discord-Testnachricht gesendet.")
