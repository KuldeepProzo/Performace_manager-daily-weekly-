import os
import smtplib
import csv
import time
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.utils import formataddr

# Load env
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
exclude_emails = {
   "kuldeep.thakran@prozo.com",
   "ankit.rakhecha@prozo.com"
 }

if not EMAIL_USERNAME or not EMAIL_PASSWORD:
    raise ValueError("EMAIL_USERNAME or EMAIL_PASSWORD not set in environment variables")

TMP_DIR = "/tmp" if os.name != "nt" else os.path.join(os.getcwd(), "tmp")
os.makedirs(TMP_DIR, exist_ok=True)

def sanitize(value):
    """Remove newlines and extra spaces to make CSV cleaner"""
    if value is None:
        return ""
    return str(value).replace("\n", " ").replace("\r", " ").strip()

def send_email_with_csv(to_email, deals, role="OWNER", metrics=None):
    if not deals:
        print(f"⚠️ No deals to send to {to_email}")
        return

    csv_file = generate_csv(deals, to_email, role)
    body = build_email_body(role=role, recipient=to_email, metrics=metrics)
    send_email_with_attachment(to_email, body, csv_file, role=role)

    # Clean up the file
    try:
        os.remove(csv_file)
    except Exception as e:
        print(f"⚠️ Could not delete file {csv_file}: {e}")

def extract_name_from_email(email):
    """Extracts and formats a first name from an email like kuldeep.thakran@prozo.com -> Kuldeep"""
    if not email:
        return "there"
    name_part = email.split("@")[0]
    first_name = name_part.split(".")[0].capitalize()
    return first_name

def build_email_body(role="OWNER", recipient=None, metrics=None):
    name = extract_name_from_email(recipient)
    today_str = datetime.today().strftime("%d %b %Y")
    metrics = metrics or {}

    if role == "SUMMARY":
        return f"""
<p>Hi {name} 👋,</p>

<p>Please find attached the consolidated MQL performance summary for all deal owners.</p>

<p>🚨 Action Summary:</p>

<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; font-family: Arial, sans-serif; font-size: 14px;">
<tr><th>Metric</th><th>Count</th><th>Status</th></tr>
<tr><td>🕒 First Engagement Pending (1+ Days)</td><td>{sum(stats.get("first_engagement_pending", 0)
    for owner_email, stats in metrics.items()
    if owner_email not in exclude_emails)}</td><td style='color: red;'>⚠️ Follow-up Needed</td></tr>
<tr><td>⏱️ 1st → 2nd Engagement Delay</td><td>{sum(stats.get("engagement_gap_1_2", 0)
    for owner_email, stats in metrics.items()
    if owner_email not in exclude_emails)}</td><td style='color: orange;'>⚠️ Delay</td></tr>
<tr><td>⏱️ 2nd → 3rd Engagement Delay</td><td>{sum(stats.get("engagement_gap_2_3", 0)
    for owner_email, stats in metrics.items()
    if owner_email not in exclude_emails)}</td><td style='color: orange;'>⚠️ Delay</td></tr>
<tr><td>🚫 No Activity in Last 3 Days</td><td>{sum(stats.get("no_activity_3_days", 0)
    for owner_email, stats in metrics.items()
    if owner_email not in exclude_emails)}</td><td style='color: red;'>🔴 Inactive</td></tr>
<tr><td>💡 Revived Cold/Warm Deals</td><td>{sum(stats.get("revived_cold_warm", 0)
    for owner_email, stats in metrics.items()
    if owner_email not in exclude_emails)}</td><td style='color: green;'>🟢 Active Again</td></tr>
<tr><td>♻️ Stage Reversal: Hot → Warm</td><td>{sum(stats.get("hot_to_warm", 0)
    for owner_email, stats in metrics.items()
    if owner_email not in exclude_emails)}</td><td>OK</td></tr>
<tr><td>♻️ Stage Reversal: Warm → Cold</td><td>{sum(stats.get("warm_to_cold", 0)
    for owner_email, stats in metrics.items()
    if owner_email not in exclude_emails)}</td><td>OK</td></tr>
<tr><td>♻️ Stage Reversal: Hot → Cold</td><td>{sum(stats.get("hot_to_cold", 0)
    for owner_email, stats in metrics.items()
    if owner_email not in exclude_emails)}</td><td>OK</td></tr>
</table>

<p>This summary will help in identifying patterns across the pipeline
and ensure timely interventions by team leaders.</p>

<p>Warm regards,<br>
Prozo Performance Manager</p>
"""

    return f"""
<p>Hi {name} 👋,</p>

<p>Here’s your daily performance snapshot on Hot Deals from HubSpot as of {today_str}.</p>

<p>🚨 Action Summary:</p>

<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; font-family: Arial, sans-serif; font-size: 14px;">
<tr><th>Metric</th><th>Count</th><th>Status</th></tr>
<tr><td>🕒 First Engagement Pending (1+ Days)</td><td>{metrics.get('first_engagement_pending', 0)}</td><td style='color: red;'>⚠️ Follow-up Needed</td></tr>
<tr><td>⏱️ 1st → 2nd Engagement Delay</td><td>{metrics.get('engagement_gap_1_2', 0)}</td><td style='color: orange;'>⚠️ Delay</td></tr>
<tr><td>⏱️ 2nd → 3rd Engagement Delay</td><td>{metrics.get('engagement_gap_2_3', 0)}</td><td style='color: orange;'>⚠️ Delay</td></tr>
<tr><td>🚫 No Activity in Last 3 Days</td><td>{metrics.get('no_activity_3_days', 0)}</td><td style='color: red;'>🔴 Inactive</td></tr>
<tr><td>💡 Revived Cold/Warm Deals</td><td>{metrics.get('revived_cold_warm', 0)}</td><td style='color: green;'>🟢 Active Again</td></tr>
<tr><td>♻️ Stage Reversal: Hot → Warm</td><td>{metrics.get('hot_to_warm', 0)}</td><td>OK</td></tr>
<tr><td>♻️ Stage Reversal: Warm → Cold</td><td>{metrics.get('warm_to_cold', 0)}</td><td>OK</td></tr>
<tr><td>♻️ Stage Reversal: Hot → Cold</td><td>{metrics.get('hot_to_cold', 0)}</td><td>OK</td></tr>
</table>

<p>📎 Please refer to the attached file for detailed deal-level insights.<br>
🔖<strong>Reminder:</strong> Any stage reversal must be accompanied by a task. Otherwise, please move such deals to <strong>LOST</strong>.</p>

<p>Warm regards,<br>
Prozo Performance Manager</p>
"""

def generate_csv(deals, recipient, role):
    filename = f"alerts_{role.lower()}_{recipient.replace('@', '_at_').replace('.', '_').strip()}.csv"
    filepath = os.path.join(TMP_DIR, filename)

    with open(filepath, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, quoting=csv.QUOTE_ALL)
        writer.writerow([
            "Deal Name", "Deal Owner Email", "Deal Type", "Last Activity Date",
            "Days Since Last Activity", "First Engagement Date", "Second Engagement Date",
            "Third Engagement Date", "Stage Change", "Alerts", "","","", "Latest Note", "","",""
        ])

        for deal in deals:
            raw_type = deal.get("deal_type", "").lower()
            if raw_type == "true":
                deal_type_display = "🔴 hot"
            elif raw_type == "false":
                deal_type_display = "🔵 warm"
            elif raw_type == "cold":
                deal_type_display = "🟢 cold"
            else:
                deal_type_display = "unknown"

            first_eng = sanitize(deal.get("engagement_dates", {}).get("first"))
            second_eng = sanitize(deal.get("engagement_dates", {}).get("second"))
            third_eng = sanitize(deal.get("engagement_dates", {}).get("third"))

            writer.writerow([
                sanitize(deal.get("name")),
                sanitize(deal.get("owner_email")),
                sanitize(deal_type_display),
                sanitize(deal.get("last_activity_fr")),
                sanitize(deal.get("days_since_last_activity")),
                first_eng,
                second_eng,
                third_eng,
                sanitize(deal.get("stage_change", "N/A")),
                sanitize(", ".join(deal.get("alerts", []))),
                "","","",
                sanitize(deal.get("last_note")),
                "","",""
            ])

    return filepath

def send_email_with_attachment(to_email, body, file_path, role="OWNER"):
    today_str = datetime.now().strftime("%d %b %Y")
    subject = {
        "SUMMARY": f"🚨 MQL Performance Summary Report || {today_str}",
        "OWNER": f"⚠️ Your HubSpot To-Do || Hot Deals Performance Summary || {today_str} "
    }.get(role, f"📢 Deal Alert Summary – {today_str}")

    msg = MIMEMultipart()
    msg["Subject"] = subject.strip()
    msg["From"] = formataddr(("Prozo Performance Manager", EMAIL_USERNAME.strip()))
    msg["To"] = to_email.strip()
    msg.attach(MIMEText(body, "html"))

    try:
        with open(file_path, "rb") as file:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(file.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(file_path)}")
            msg.attach(part)
    except Exception as e:
        print(f"❌ Failed to attach file: {e}")
        raise

    for attempt in range(2):  # Try once, retry once if it fails
        try:
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
                server.starttls()
                server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
                server.send_message(msg)
            print(f"✅ Email sent to {to_email}")
            return  # Exit after success
        except Exception as e:
            print(f"❌ Attempt {attempt + 1}: Failed to send email to {to_email}: {e}")
            if attempt == 0:
                print("⏳ Retrying in 5 seconds...")
                time.sleep(5)
            else:
                raise  # Final failure, let the main retry logic handle it
