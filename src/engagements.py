import os
import requests
from bs4 import BeautifulSoup

HUBSPOT_TOKEN = os.getenv("HUBSPOT_TOKEN")
HEADERS = {
    "Authorization": f"Bearer {HUBSPOT_TOKEN}"
}

def fetch_engagements_for_deal(deal_id, deal_name=None):
    url = f"https://api.hubapi.com/engagements/v1/engagements/associated/deal/{deal_id}/paged?limit=100"
    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            print(f"❌ Failed to fetch engagements for deal {deal_name or deal_id}: {response.status_code}")
            return [], "N/A"

        data = response.json()
        results = data.get("results", [])

        timestamps = []
        notes = []

        for item in results:
            eng = item.get("engagement", {})
            meta = item.get("metadata", {})

            ts = eng.get("timestamp")
            if ts:
                timestamps.append(ts)

                if eng.get("type") == "NOTE" and meta.get("body"):
                    # Extract readable text from HTML using BeautifulSoup
                    soup = BeautifulSoup(meta["body"], "html.parser")
                    note_text = soup.get_text().strip()
                    notes.append({
                        "timestamp": ts,
                        "body": note_text
                    })

        timestamps = sorted(timestamps)
        notes = sorted(notes, key=lambda x: x["timestamp"])

        # Return the latest note if available
        last_note = notes[-1]["body"] if notes else "N/A"

        if deal_name:
            print(f"📌 Deal {deal_name} has {len(timestamps)} engagement(s) and latest note: {last_note[:80]}...")
        else:
            print(f"📌 Deal {deal_id} has {len(timestamps)} engagement(s)")

        return timestamps, last_note

    except Exception as e:
        print(f"❌ Exception while fetching engagements for deal {deal_name or deal_id}: {e}")
        return [], "N/A"
