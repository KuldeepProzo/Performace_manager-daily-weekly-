import os
import requests
import time

HUBSPOT_TOKEN = os.getenv("HUBSPOT_TOKEN")
HEADERS = {
    "Authorization": f"Bearer {HUBSPOT_TOKEN}",
    "Content-Type": "application/json"
}

OWNER_EMAIL_CACHE = {}

# Dealstage values to skip
IGNORED_DEALSTAGES = {
    # Warehousing
    "996085343", "996085344", "996089867",
    
    # D2C Freight
    "995921567", "995921568", "996140196",
    
    # Tech
    "995964762", "995964763", "995964768",
    
    # PTL
    "998316459", "998316458", "998351476"
}

def safe_get(url, headers, max_retries=3):
    wait_times = [5, 10, 20]  # exponential backoff
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                return response
            elif response.status_code == 429:
                print(f"⏳ Rate limit hit (attempt {attempt+1}), retrying in {wait_times[attempt]}s...")
                time.sleep(wait_times[attempt])
            else:
                print(f"⚠️ Error {response.status_code} for {url}")
                return response
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed (attempt {attempt+1}): {e}")
            time.sleep(wait_times[attempt])
    return None

def get_owner_email(owner_id):
    if not owner_id:
        return None
    if owner_id in OWNER_EMAIL_CACHE:
        return OWNER_EMAIL_CACHE[owner_id]

    url = f"https://api.hubapi.com/crm/v3/owners/{owner_id}"
    response = safe_get(url, HEADERS)
    if response and response.status_code == 200:
        email = response.json().get("email")
        OWNER_EMAIL_CACHE[owner_id] = email
        return email
    else:
        print(f"❌ Failed to get email for owner {owner_id}")
        return None

def fetch_deal_type_history(deal_id):
    url = f"https://api.hubapi.com/crm/v3/objects/deals/{deal_id}?propertiesWithHistory=deal_type__hot__warm___cold_"
    response = safe_get(url, HEADERS)
    print(f"🔍 Debug for Deal ID {deal_id} | Status: {response.status_code if response else 'None'}")
    if not response or response.status_code != 200:
        return []

    return [
        {"value": item.get("value"), "timestamp": item.get("timestamp")}
        for item in response.json()
        .get("propertiesWithHistory", {})
        .get("deal_type__hot__warm___cold_", [])
    ]

def get_recent_deals_grouped_by_owner():
    print("📡 Fetching *all* marketing deals...")

    url = "https://api.hubapi.com/crm/v3/objects/deals/search"
    all_deals = []
    after = None

    while True:
        payload = {
            "filterGroups": [{
                "filters": [{
                    "propertyName": "source_of_the_deal",
                    "operator": "EQ",
                    "value": "Marketing"
                }]
            }],
            "properties": [
                "dealname",
                "hubspot_owner_id",
                "hs_lastmodifieddate",
                "notes_last_updated",
                "deal_type__hot__warm___cold_",
                "hubspot_owner_assigneddate",
                "source_of_the_deal",
                "dealstage"
            ],
            "limit": 100
        }
        if after:
            payload["after"] = after

        response = None
        for attempt in range(3):
            try:
                response = requests.post(url, headers=HEADERS, json=payload, timeout=30)
                print(f"🔁 Status: {response.status_code}")
                if response.status_code == 200:
                    break
                elif response.status_code == 429:
                    print(f"⏳ Rate limit hit while fetching deals. Retrying in 5s...")
                    time.sleep(5)
                else:
                    print("❌ Error fetching deals:", response.text)
                    return {}
            except requests.exceptions.RequestException as e:
                print(f"❌ Request error: {e}")
                time.sleep(5)

        if not response or response.status_code != 200:
            break

        data = response.json()
        all_deals.extend(data.get("results", []))
        after = data.get("paging", {}).get("next", {}).get("after")
        if not after:
            break
        time.sleep(1)  # Delay between pages

    grouped = {}

    for index, deal in enumerate(all_deals):
        props = deal.get("properties", {})
        owner_id = props.get("hubspot_owner_id")
        if not owner_id:
            continue

        owner_email = get_owner_email(owner_id)
        if not owner_email:
            continue

        dealstage = str(props.get("dealstage", ""))
        if dealstage in IGNORED_DEALSTAGES:
            print(f"⏭️ Ignored deal '{props.get('dealname')}' (ID: {deal.get('id')}) for owner '{owner_email}' due to dealstage {dealstage}")
            continue

        time.sleep(0.8)  # Delay between each deal fetch

        if index > 0 and index % 10 == 0:
            print("⏳ Pausing for 2s every 10 deals...")
            time.sleep(2)

        deal_type_history = fetch_deal_type_history(deal["id"])

        deal_data = {
            "id": deal.get("id"),
            "name": props.get("dealname", "No Name"),
            "owner_id": owner_id,
            "owner_email": owner_email,
            "last_modified": props.get("hs_lastmodifieddate") or "N/A",
            "last_activity": props.get("notes_last_updated") or "N/A",
            "deal_type": props.get("deal_type__hot__warm___cold_") or "N/A",
            "owner_assignment_date": props.get("hubspot_owner_assigneddate") or "N/A",
            "deal_source": props.get("source_of_the_deal"),
            "deal_type_history": deal_type_history,
            "deal_stage": dealstage
        }

        print("\n📦 Deal Details")
        print(f"🆔 ID: {deal_data['id']}")
        '''
        print(f"📛 Name: {deal_data['name']}")
        print(f"👤 Owner Email: {deal_data['owner_email']}")
        print(f"👤 Owner ID: {deal_data['owner_id']}")
        print(f"🕑 Last Modified: {deal_data['last_modified']}")
        print(f"📅 Last Activity: {deal_data['last_activity']}")
        print(f"🔖 Deal Type: {deal_data['deal_type']}")
        print(f"📥 Owner Assigned Date: {deal_data['owner_assignment_date']}")
        print(f"👌 Deal Source: {deal_data['deal_source']}")
        print(f"📶 Deal Stage: {deal_data['deal_stage']}")
        print("🕓 Deal Type History:")
        if deal_data["deal_type_history"]:
            for entry in deal_data["deal_type_history"]:
                print(f"   - {entry['timestamp']}: {entry['value']}")     '''
        else:
            print("   - No history found")

        grouped.setdefault(owner_email, []).append(deal_data)

    print(f"\n✅ Found {len(all_deals)} marketing deals grouped by {len(grouped)} owners")
    return grouped
