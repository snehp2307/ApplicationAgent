"""
============================================
BULK AI JOB OUTREACH BOT
============================================
Main entry point. One command, full automation.

Usage:
    python main.py

Then enter:
    - Target job role (e.g., "Data Analyst")
    - Location (optional, press Enter to skip)

The bot will automatically:
    1. Search 100-300 companies
    2. Find HR/careers emails
    3. Validate and deduplicate emails
    4. Research each company with AI
    5. Write personalized emails with Mistral AI
    6. Send in batches with resume attached
    7. Log everything to CSV
"""

import sys
import time
from datetime import datetime

# Validate config before anything else
from config import validate_config
from graph import build_outreach_graph
from csv_logger import log_activity


def print_banner():
    """Print the startup banner."""
    print("\n" + "=" * 60)
    print("   🤖 BULK AI JOB OUTREACH BOT")
    print("   Powered by LangChain + LangGraph + Mistral AI")
    print("=" * 60)
    print("   One run. 100-300 companies. Full automation.")
    print("=" * 60)


def get_user_input():
    """Get job role and location from user."""
    print("\n📋 SETUP")
    print("-" * 40)

    job_role = input("   Enter target job role (e.g., Data Analyst): ").strip()
    if not job_role:
        print("   ❌ Job role is required!")
        sys.exit(1)

    location = input("   Enter preferred location (press Enter for any): ").strip()

    print(f"\n   ✅ Role: {job_role}")
    print(f"   ✅ Location: {location or 'Any / Remote'}")
    print()

    # Confirm before starting
    confirm = input("   🚀 Start bulk outreach? (y/n): ").strip().lower()
    if confirm != "y":
        print("   Cancelled. Exiting.")
        sys.exit(0)

    return job_role, location


def main():
    """Main execution function."""
    print_banner()

    # Step 1: Validate configuration
    print("\n⚙️  CONFIGURATION CHECK")
    print("-" * 40)
    validate_config()

    # Step 2: Get user input
    job_role, location = get_user_input()

    # Step 3: Build the LangGraph pipeline
    print("\n🔧 Building outreach pipeline...")
    app = build_outreach_graph()
    print("   ✅ Pipeline ready!\n")

    # Log the start
    log_activity("=" * 50)
    log_activity("NEW OUTREACH SESSION STARTED")
    log_activity(f"Role: {job_role}")
    log_activity(f"Location: {location or 'Any'}")
    log_activity(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Step 4: Run the pipeline
    start_time = time.time()

    print("🚀 STARTING BULK OUTREACH PIPELINE")
    print("=" * 60)

    # Initial state
    initial_state = {
        "job_role": job_role,
        "location": location,
        "companies": [],
        "total_found": 0,
        "validated_count": 0,
        "emails_generated": 0,
        "total_sent": 0,
        "total_failed": 0,
        "sent_companies": [],
        "failed_companies": [],
        "logging_complete": False,
    }

    # Execute the full pipeline
    try:
        final_state = app.invoke(initial_state)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user. Partial results may be saved.")
        log_activity("SESSION INTERRUPTED BY USER")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Pipeline error: {e}")
        log_activity(f"PIPELINE ERROR: {e}")
        raise

    # Step 5: Print final summary
    elapsed = time.time() - start_time
    elapsed_min = elapsed / 60

    print("\n" + "=" * 60)
    print("   🎉 BULK OUTREACH COMPLETE!")
    print("=" * 60)
    print(f"   📊 FINAL RESULTS:")
    print(f"      Job Role:          {job_role}")
    print(f"      Location:          {location or 'Any'}")
    print(f"      Companies Found:   {final_state.get('total_found', 0)}")
    print(f"      Emails Validated:  {final_state.get('validated_count', 0)}")
    print(f"      Emails Generated:  {final_state.get('emails_generated', 0)}")
    print(f"      Emails Sent:       {final_state.get('total_sent', 0)}")
    print(f"      Emails Failed:     {final_state.get('total_failed', 0)}")
    print(f"      Total Time:        {elapsed_min:.1f} minutes")
    print()
    print(f"   📁 OUTPUT FILES:")
    print(f"      output/sent_log.csv")
    print(f"      output/failed_log.csv")
    print(f"      output/companies_found.csv")
    print(f"      output/activity_log.txt")
    print("=" * 60)

    log_activity(f"SESSION COMPLETED in {elapsed_min:.1f} minutes")


if __name__ == "__main__":
    main()
