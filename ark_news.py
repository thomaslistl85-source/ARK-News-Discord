
import os
import requests

WEBHOOK = os.environ["DISCORD_WEBHOOK_URL"]

NEWS_API = (
    "https://api.steampowered.com/"
    "ISteamNews/GetNewsForApp/v2/"
)

response = requests.get(
    NEWS_API,
    params={
        "appid": 2399830,
        "count": 5,
        "maxlength": 0
    },
    timeout=30
)
response.raise_for_status()

news = response.json()["appnews"]["newsitems"]

if not news:
    print("Keine ARK-News gefunden.")
    raise SystemExit(0)

# Vorläufig nur die neueste Meldung anzeigen.
# Noch keine Nachricht an Discord senden.
latest = news[0]

print("ARK-News erfolgreich abgerufen:")
print("Titel:", latest["title"])
print("Link:", latest["url"])
print("Discord-Webhook vorhanden:", bool(WEBHOOK))
