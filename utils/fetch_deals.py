import os
import time
import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

load_dotenv()

HUBSPOT_TOKEN = os.getenv("HUBSPOT_TOKEN")
BASE_URL = "https://api.hubapi.com"

HEADERS = {
    "Authorization": f"Bearer {HUBSPOT_TOKEN}",
    "Content-Type": "application/json"
}

# Setup retry session
def requests_retry_session():
    retry_strategy = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

session = requests_retry_session()

def get_owner_email_map():
    url = f"{BASE_URL}/crm/v3/owners"
    res = session.get(url, headers=HEADERS)
    return {owner["id"]: owner["email"] for owner in res.json().get("results", [])}

def get_all_deals_grouped_by_owner():
    url = f"{BASE_URL}/crm/v3/objects/deals"
    limit = 100
    after = None
    all_deals = []

    while True:
        params = {
            "limit": limit,
            "properties": "dealname,hubspot_owner_id,deal_type__hot__warm___cold_,amount,num_associated_contacts"
        }
        if after:
            params["after"] = after

        res = session.get(url, headers=HEADERS, params=params)
        res.raise_for_status()
        data = res.json()
        all_deals.extend(data.get("results", []))
        after = data.get("paging", {}).get("next", {}).get("after")
        if not after:
            break
        time.sleep(0.4)

    print(f"📦 Fetched {len(all_deals)} total deals")

    owners = get_owner_email_map()
    grouped = {}

    for i, deal in enumerate(all_deals, 1):
        props = deal.get('properties', {})
        owner_id = props.get('hubspot_owner_id')
        owner_email = owners.get(owner_id, 'unknown@prozo.com')

        # Get associated contact IDs
        contact_url = f"{BASE_URL}/crm/v3/objects/deals/{deal['id']}/associations/contacts"
        contact_res = session.get(contact_url, headers=HEADERS, params={"limit": 100})
        contact_ids = [r['id'] for r in contact_res.json().get('results', [])]

        # Fetch contact details
        contacts = []
        for cid in contact_ids:
            try:
                contact_detail_url = f"{BASE_URL}/crm/v3/objects/contacts/{cid}"
                detail_res = session.get(contact_detail_url, headers=HEADERS, params={
                    "properties": "firstname,lastname,email,jobtitle"
                })
                c = detail_res.json().get("properties", {})
                contacts.append({
                    "firstname": c.get("firstname", ""),
                    "lastname": c.get("lastname", ""),
                    "email": c.get("email", ""),
                    "jobtitle": c.get("jobtitle", "")
                })
                time.sleep(0.4)
            except Exception as e:
                print(f"⚠️ Failed to fetch contact {cid}: {e}")
                continue

        deal_data = {
            "id": deal.get("id"),
            "name": props.get("dealname", "No Name"),
            "owner_email": owner_email,
            "deal_type": props.get("deal_type__hot__warm___cold_") or "N/A",
            "amount": props.get("amount") or "N/A",
            "num_associated_contacts": props.get("num_associated_contacts") or 0,
            "associated_contacts": contacts
        }

        print(f"\n📦 Deal {i}")
        print(f"🆔 ID: {deal_data['id']}")
        
       # print(f"📛 Name: {deal_data['name']}")
        #print(f"👤 Owner Email: {deal_data['owner_email']}")
        #print(f"🔖 Deal Type: {deal_data['deal_type']}")
        #print(f"💰 Amount: ₹{deal_data['amount']}")
        #print(f"👥 Total Contacts: {len(contacts)} (API) / {deal_data['num_associated_contacts']} (Property)")
        #for contact in contacts:
         #   print(f"   - {contact['firstname']} {contact['lastname']} | {contact['email']} | {contact['jobtitle']}")   

        grouped.setdefault(owner_email, []).append(deal_data)

        # Delay to prevent rate limit
        time.sleep(0.4)
        if i % 10 == 0:
            time.sleep(3)

    print(f"\n✅ Grouped {len(all_deals)} deals by {len(grouped)} owners")
    return grouped
