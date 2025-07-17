def analyze_deals(grouped_deals):
    alerts = {}
    counters = {}

    for owner, deals in grouped_deals.items():
        print(f"\n🔍 Analyzing deals for: {owner}")
        alerts[owner] = []
        counters[owner] = {
            'X1_HotDealsMissingContacts': 0,
            'X2_HotDealsMissingDesignations': 0,
            'X3_HotDealsLowMBR': 0,
            'X4_DealsMissingType': 0
        }

        for deal in deals:
            deal_alerts = []

            deal_type = (deal.get('deal_type') or '').strip().lower()
            amount = float(deal.get('amount', 0)) if deal.get('amount') not in [None, '', 'N/A'] else 0.0
            contacts = deal.get('associated_contacts', [])
            num_contacts = int(deal.get('num_associated_contacts', 0))

            print(f"\n➡️ Checking Deal: {deal['name']} (Type: {deal_type}, Amount: {amount}, Contacts: {num_contacts})")

            # Alert: Missing deal type
            if not deal_type or deal_type == 'n/a':
                counters[owner]['X4_DealsMissingType'] += 1
                deal_alerts.append("❗ Missing Deal Type")

            # Analyze cold deals instead of hot
            if deal_type == 'true':
                # Alert 1: Missing 2+ contacts
                if num_contacts < 2:
                    counters[owner]['X1_HotDealsMissingContacts'] += 1
                    deal_alerts.append("👤 Less than 2 associated contacts")

                # Alert 2: Missing designations
                missing_designations = [
                    f"{c['firstname']} {c['lastname']}" for c in contacts
                    if not c.get('jobtitle') or str(c['jobtitle']).strip().lower() in ['none', '']
                ]
                if missing_designations:
                    counters[owner]['X2_HotDealsMissingDesignations'] += 1
                    for name in missing_designations:
                        deal_alerts.append(f"🪪 Missing designation for {name.strip()}")

                # Alert 3: Low MBR
                if amount < 1000:
                    counters[owner]['X3_HotDealsLowMBR'] += 1
                    deal_alerts.append("💰 MBR less than ₹1,000")

            if deal_alerts:
                print(f"\n🚨 Alerts for Deal: {deal['name']} (ID: {deal['id']})")
                for alert in deal_alerts:
                    print(f"- {alert}")

                alerts[owner].append({
                    "deal_name":deal['name'],
                    "deal_id": deal['id'],
                    "deal_name": deal['name'],
                    "alerts": deal_alerts
                })

    return alerts, counters
