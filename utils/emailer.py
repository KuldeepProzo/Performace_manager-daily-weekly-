import smtplib
import os
import io
import csv
import time
import traceback
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr
from dotenv import load_dotenv

load_dotenv()

# 🔐 Load and sanitize secrets
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME", "").strip().replace("\n", "").replace("\r", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "").strip().replace("\n", "").replace("\r", "")
SUMMARY_RECEIVER = "kuldeep.thakran@prozo.com".strip()

# 🐞 Debug: Print sanitized secrets info
print(f"📨 EMAIL_USERNAME: {EMAIL_USERNAME}")
print(f"🔒 EMAIL_PASSWORD Length: {len(EMAIL_PASSWORD)}")
print(f"📬 SUMMARY_RECEIVER: {SUMMARY_RECEIVER}")


def build_email_body(owner_email, counters, is_summary=False):
    name = "Kuldeep" if owner_email.lower() == SUMMARY_RECEIVER else owner_email.split("@")[0].split(".")[0].capitalize()
    stats = counters.get(owner_email, {})

    if is_summary:
        intro = f"""Hi {name},<br><br>
Here's the summary report for all Hot Deals flagged this week.<br><br>"""
    else:
        intro = f"""Hi {name},<br><br>
Please find below your weekly diligence report for <b>Hot Deals</b>, highlighting gaps in data quality and commercial hygiene.<br>
This is critical for ensuring every Hot Deal is dealroom-ready and qualified for conversion.<br><br>
🛑 <b>Diligence Gaps Identified</b><br><br>"""

    stats_html = f"""
1. 🧍‍♂️ Hot Deals Missing 2+ Contacts: <b>{stats.get("X1_HotDealsMissingContacts", 0)}</b><br>
2. 🪪 Hot Deals Missing Designations: <b>{stats.get("X2_HotDealsMissingDesignations", 0)}</b><br>
3. 💰 Hot Deals with No Valid MBR (&lt; ₹1,000): <b>{stats.get("X3_HotDealsLowMBR", 0)}</b><br>
4. ❓ Deals with No Deal Type: <b>{stats.get("X4_DealsMissingType", 0)}</b><br><br>
📎 The attached sheet lists each flagged deal, ownership, and exact missing details.<br>
Please update them within the week to keep your pipeline clean and leadership-ready.<br><br>
Thanks,<br>Prozo Performance Manager
"""
    return intro + stats_html

def create_csv_content(alerts, grouped_deals, owner_email):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Deal Name", "", "Owner Email", "","Deal Type", "No. of Contacts", "Amount", "Alerts", "", "", "","",""])

    for alert in alerts.get(owner_email, []):
        deal_id = alert["deal_id"]
        deal = next((d for d in grouped_deals.get(owner_email, []) if d["id"] == deal_id), {})
        writer.writerow([
            deal.get("name", ""),
            "",
            deal.get("owner_email", ""),
            "",
            deal.get("deal_type", ""),
            deal.get("num_associated_contacts", ""),
            deal.get("amount", ""),
            "; ".join(alert.get("alerts", [])),
            "", "", "","",""
        ])

    return output.getvalue()

def send_email_with_attachment(to_email, body_html, csv_content, role="OWNER"):
    today_str = datetime.now().strftime("%d %b %Y")
    subject = {
        "SUMMARY": f"📢 SUMMARY || HOT DEALS PERFORMANCE || {today_str}",
        "OWNER": f"⚠️ TESTING || Hot Deals Performance || {today_str}"
    }.get(role, f"📢 Deal Alert Summary – {today_str}")

    from_email = formataddr(("Prozo Performance Manager", EMAIL_USERNAME))
    to_email_clean = to_email.strip().replace("\n", "").replace("\r", "")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr(("Prozo Performance Manager", EMAIL_USERNAME))
    msg["To"] = "kuldeep.thakran@prozo.com"
    msg.set_content("This is a multi-part message in HTML and CSV.")
    msg.add_alternative(body_html, subtype="html")

    print(f"📤 From: {from_email}")
    print(f"📥 To: {to_email_clean}")
    

    msg.add_attachment(
        csv_content.encode("utf-8"),
        maintype="application",
        subtype="octet-stream",
        filename="deal_alerts.csv"
    )

    # Retry sending the email once on failure
    for attempt in range(2):
        try:
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
                server.starttls()
                server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
                server.send_message(msg)
            print(f"✅ Email sent to {to_email}")
            return
        except Exception as e:
            print(f"❌ Attempt {attempt + 1}: Failed to send email to {to_email}: {e}")
            if attempt == 0:
                print("⏳ Retrying in 5 seconds...")
                time.sleep(5)
            else:
                raise

def safe_send_email(email, alerts, grouped_deals, role="OWNER", counters=None):
    try:
        body = build_email_body(email, counters, is_summary=(role == "SUMMARY"))
        csv_content = create_csv_content(alerts, grouped_deals, email)
        send_email_with_attachment(email, body, csv_content, role=role)
    except Exception as e:
        print(f"❌ Final failure: Could not send email to {email}: {e}")

def export_and_email(alerts, counters, grouped_deals):
    # 1️⃣ Send per-owner reports
    for owner_email, alert_list in alerts.items():
        if not alert_list:
            continue
        safe_send_email(owner_email, alerts, grouped_deals, role="OWNER", counters=counters)

    # 2️⃣ Summary for Kuldeep
    combined_alerts = {SUMMARY_RECEIVER: []}
    combined_deals = {SUMMARY_RECEIVER: []}

    for owner_email, alert_list in alerts.items():
        combined_alerts[SUMMARY_RECEIVER].extend(alert_list)
        combined_deals[SUMMARY_RECEIVER].extend(grouped_deals.get(owner_email, []))

    safe_send_email(SUMMARY_RECEIVER, combined_alerts, combined_deals, role="SUMMARY", counters=counters)
