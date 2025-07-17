from dotenv import load_dotenv
load_dotenv()

from utils.fetch_deals import get_all_deals_grouped_by_owner
from utils.analyze import analyze_deals
from utils.emailer import export_and_email

if __name__ == "__main__":
    print("🚀 Fetching all deals...")
    grouped_deals = get_all_deals_grouped_by_owner()

    if not grouped_deals:
        print("⚠️ No deals found.")
        exit()

    print("🧠 Analyzing deals...")
    alerts, counters = analyze_deals(grouped_deals)

    print("📧 Sending emails to owners and summary to Kuldeep...")
    export_and_email(alerts, counters ,grouped_deals)
