from datetime import datetime, timedelta

def analyze_deals(deal_list):
    alerts_by_deal = {}
    metrics_by_owner = {}

    for deal in deal_list:
        deal_id = deal.get("id")
        deal_name = deal.get("name", "N/A")
        owner_email = deal.get("owner_email", "").lower()
        raw_type = deal.get("deal_type", "").lower()

        # Normalize deal type
        if raw_type == "true":
            deal_type = "hot"
        elif raw_type == "false":
            deal_type = "warm"
        elif raw_type == "cold":
            deal_type = "cold"
        else:
            deal_type = "unknown"

        last_activity_str = deal.get("last_activity")
        owner_assigned_str = deal.get("owner_assignment_date")
        engagements = deal.get("engagements", [])
        deal_type_history = deal.get("deal_type_history", [])

        alerts = []
        metrics = metrics_by_owner.setdefault(owner_email, {
            "first_engagement_pending": [0,[]],
            "engagement_gap_1_2": [0,[]],
            "engagement_gap_2_3": [0,[]],
            "no_activity_3_days": [0,[]],
            "revived_cold_warm": [0,[]],
            "hot_to_warm": [0,[]],
            "warm_to_cold": [0,[]],
            "hot_to_cold": [0,[]],
        })
                
        
        # Convert assignment date (if present)
        assigned_dt = None
        if owner_assigned_str and owner_assigned_str != "N/A":
            try:
                assigned_dt = datetime.strptime(owner_assigned_str[:19], "%Y-%m-%dT%H:%M:%S")
            except Exception as e:
                print(f"❌ Error parsing owner assignment date: {e}")

        # Filter engagements AFTER assignment date
        engagement_ts = []
        if assigned_dt:
            for ts in engagements:
                try:
                    ts_dt = datetime.fromtimestamp(ts / 1000)
                    if ts_dt >= assigned_dt:
                        engagement_ts.append(ts_dt)
                except Exception as e:
                    print(f"❌ Error parsing engagement timestamp: {e}")



        # Save for CSV export
        engagement_dates = {}
        if len(engagement_ts) >= 1:
            engagement_dates["first"] = engagement_ts[0].strftime("%Y-%m-%d %H:%M")
        if len(engagement_ts) >= 2:
            engagement_dates["second"] = engagement_ts[1].strftime("%Y-%m-%d %H:%M")
        if len(engagement_ts) >= 3:
            engagement_dates["third"] = engagement_ts[2].strftime("%Y-%m-%d %H:%M")
        deal["engagement_dates"] = engagement_dates


        days_since_last_activity = ""
        if last_activity_str and last_activity_str != "N/A":
            try:
                 last_dt = datetime.strptime(last_activity_str[:10], "%Y-%m-%d")
                 days_since_last_activity = (datetime.utcnow() - last_dt).days
            except Exception as e:
                 print(f"❌ Error calculating days since last activity: {e}")
                 days_since_last_activity = "N/A"

        else:
            days_since_last_activity = "N/A"

        deal["days_since_last_activity"] = days_since_last_activity

        try:
            raw_last = deal.get("last_activity")
            if raw_last and raw_last != "N/A":
                dt = datetime.strptime(raw_last[:19], "%Y-%m-%dT%H:%M:%S")
                deal["last_activity_fr"] = dt.strftime("%Y-%m-%d %H:%M")
            else:
                deal["last_activity_fr"] = "N/A"
        except Exception as e:
            print(f"❌ Error formatting last activity: {e}")
            deal["last_activity_fr"] = "N/A"

        # X1: First engagement pending
        if deal_type == "hot" and owner_assigned_str and owner_assigned_str != "N/A":
            try:
                assigned = datetime.strptime(owner_assigned_str[:19], "%Y-%m-%dT%H:%M:%S")
                if not engagements and datetime.utcnow() - assigned > timedelta(days=1):
                    alerts.append("First engagement pending (1+ days)")
                    metrics["first_engagement_pending"][0] += 1
                    metrics["first_engagement_pending"][1].append(deal_name)
            except Exception as e:
                print(f"❌ Error parsing owner assignment date: {e}")

        # X2/X3: Engagement gaps
        if deal_type == "hot":
            try:
                if len(engagement_ts) >= 2:
                    t1 = engagement_ts[0]
                    t2 = engagement_ts[1]
                    gap1 = (t2 - t1).total_seconds() / 86400
                    if gap1 > 2:
                         alerts.append("Delay between 1st & 2nd engagement")
                         metrics["engagement_gap_1_2"][0] += 1
                         metrics["engagement_gap_1_2"][1].append(deal_name)

                if len(engagement_ts) >= 3:
                    t3 = engagement_ts[2]
                    t2 = engagement_ts[1]
                    gap2 = (t3 - t2).total_seconds() / 86400  # t2 is still valid here
                    if gap2 > 2:
                       alerts.append("Delay between 2nd & 3rd engagement")
                       metrics["engagement_gap_2_3"][0] += 1
                       metrics["engagement_gap_2_3"][1].append(deal_name)
            except Exception as e:
                print(f"❌ Error computing engagement gaps for deal {deal.get('id', 'unknown')}: {e}")

        # X4: Inactive hot deals
        if deal_type == "hot" and last_activity_str and last_activity_str != "N/A":
            try:
                last_dt = datetime.strptime(last_activity_str[:10], "%Y-%m-%d")
                if datetime.utcnow() - last_dt > timedelta(days=3):
                    alerts.append("No Activity in Last 3 Days")
                    metrics["no_activity_3_days"][0] += 1
                    metrics["no_activity_3_days"][1].append(deal_name)
            except Exception as e:
                print(f"❌ Error parsing last activity date: {e}")

        # X5: Revived cold/warm
        if deal_type in ["cold", "warm"] and last_activity_str and last_activity_str != "N/A":
            try:
                last_dt = datetime.strptime(last_activity_str[:10], "%Y-%m-%d")
                if datetime.utcnow() - last_dt <= timedelta(days=1):
                    alerts.append("Revived Cold/Warm Deal")
                    metrics["revived_cold_warm"][0] += 1
                    metrics["revived_cold_warm"][1].append(deal_name)
            except Exception as e:
                print(f"❌ Error parsing revival activity: {e}")

        # X6–X8: Stage reversal detection
        deal["stage_change"] = "N/A"
        if isinstance(deal_type_history, list) and len(deal_type_history) >= 2:
            try:
                valid_entries = [entry for entry in deal_type_history if isinstance(entry, dict) and "timestamp" in entry and "value" in entry]
                if len(valid_entries) >= 2:
                    sorted_history = sorted(valid_entries, key=lambda x: x["timestamp"])
                    last = sorted_history[-1]
                    prev = sorted_history[-2]

                    last_time = datetime.fromisoformat(last["timestamp"].replace("Z", "+00:00"))
                    now = datetime.utcnow().replace(tzinfo=last_time.tzinfo)

                    if now - last_time <= timedelta(hours=24):
                        def normalize(val):
                            if val == "true": return "hot"
                            if val == "false": return "warm"
                            if val == "cold": return "cold"
                            return "unknown"

                        from_val = normalize(prev["value"].lower())
                        to_val = normalize(last["value"].lower())

                        if from_val != to_val:
                            change = f"{from_val} → {to_val}"
                            alerts.append(f"Stage Reversal: {change}")
                            deal["stage_change"] = change

                            if from_val == "hot" and to_val == "warm":
                                metrics["hot_to_warm"][0] += 1
                                metrics["hot_to_warm"][1].append(deal_name)
                            elif from_val == "warm" and to_val == "cold":
                                metrics["warm_to_cold"][0] += 1
                                metrics["warm_to_cold"][1].append(deal_name)
                            elif from_val == "hot" and to_val == "cold":
                                metrics["hot_to_cold"][0] += 1
                                metrics["hot_to_cold"][1].append(deal_name)

                            print(f"✅ Detected stage change for deal {deal_id}: {change}")
                        else:
                            print(f"🔍 No real stage change for deal {deal_id} (from {from_val} to {to_val})")
                    else:
                        print(f"🕒 Stage change is older than 24h for deal {deal_id}")
            except Exception as e:
                print(f"❌ Error parsing stage history: {e}")

        if alerts:
            alerts_by_deal[deal_id] = alerts

    return alerts_by_deal, metrics_by_owner
