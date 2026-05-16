"""
============================================
BULK AI JOB OUTREACH BOT
============================================
Main entry point. One command, full automation.

Usage:
    python main.py

Then enter:
    - Target job role (e.g., "Data Analyst")
    - Location (optional)
    - Experience level (Fresher / Experienced)
    - Years of experience (if experienced)
    - Key skills
    - Preferred industry (optional)

The bot will automatically:
    1. Search 100-300 companies matched to your level
    2. Find HR/careers emails
    3. Validate and deduplicate emails
    4. Research each company with AI
    5. Write realistic personalized emails with Mistral AI
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


def get_user_input() -> dict:
    """
    Collect detailed candidate profile from the user.
    Returns a dict with all profile fields for the pipeline.
    """
    print("\n📋 CANDIDATE PROFILE")
    print("-" * 50)

    # 1. Job role (required)
    job_role = input("   1. Target job role (e.g., Data Analyst): ").strip()
    if not job_role:
        print("   ❌ Job role is required!")
        sys.exit(1)

    # 2. Location (optional)
    location = input("   2. Preferred location (press Enter for any): ").strip()

    # 3. Experience level
    print("\n   3. Experience level:")
    print("      [1] Fresher / Entry-level")
    print("      [2] Experienced")
    exp_choice = input("      Select (1 or 2): ").strip()

    if exp_choice == "2":
        experience_level = "experienced"
        # 4. Years of experience
        while True:
            years_input = input("   4. Years of experience (e.g., 1, 2, 3, 5): ").strip()
            try:
                years_of_experience = int(years_input)
                if years_of_experience < 1:
                    print("      ⚠ Enter at least 1 year.")
                    continue
                break
            except ValueError:
                print("      ⚠ Enter a valid number.")
    else:
        experience_level = "fresher"
        years_of_experience = 0

    # 5. Key skills (required)
    skills_input = input("   5. Key skills (comma-separated, e.g., Python, SQL, Excel): ").strip()
    if not skills_input:
        print("   ❌ At least one skill is required!")
        sys.exit(1)
    skills = [s.strip() for s in skills_input.split(",") if s.strip()]

    # 6. Preferred industry (optional)
    industry = input("   6. Preferred industry (press Enter to skip): ").strip()

    # Build seniority label for display and search
    if experience_level == "fresher":
        seniority = "Fresher / Entry-Level"
    elif years_of_experience <= 2:
        seniority = f"Junior ({years_of_experience} yr)"
    elif years_of_experience <= 5:
        seniority = f"Mid-Level ({years_of_experience} yrs)"
    else:
        seniority = f"Senior ({years_of_experience} yrs)"

    # Confirmation
    print("\n" + "-" * 50)
    print("   📝 YOUR PROFILE:")
    print(f"      Role:        {job_role}")
    print(f"      Location:    {location or 'Any / Remote'}")
    print(f"      Level:       {seniority}")
    print(f"      Skills:      {', '.join(skills)}")
    print(f"      Industry:    {industry or 'Any'}")
    print("-" * 50)

    confirm = input("\n   🚀 Start bulk outreach? (y/n): ").strip().lower()
    if confirm != "y":
        print("   Cancelled. Exiting.")
        sys.exit(0)

    return {
        "job_role": job_role,
        "location": location,
        "experience_level": experience_level,
        "years_of_experience": years_of_experience,
        "skills": skills,
        "industry": industry,
        "seniority": seniority,
    }


def main():
    """Main execution function."""
    print_banner()

    # Step 1: Validate configuration
    print("\n⚙️  CONFIGURATION CHECK")
    print("-" * 40)
    validate_config()

    # Step 2: Get user profile
    profile = get_user_input()

    # Step 3: Build the LangGraph pipeline
    print("\n🔧 Building outreach pipeline...")
    app = build_outreach_graph()
    print("   ✅ Pipeline ready!\n")

    # Log the start
    log_activity("=" * 50)
    log_activity("NEW OUTREACH SESSION STARTED")
    log_activity(f"Role: {profile['job_role']}")
    log_activity(f"Location: {profile['location'] or 'Any'}")
    log_activity(f"Level: {profile['seniority']}")
    log_activity(f"Skills: {', '.join(profile['skills'])}")
    log_activity(f"Industry: {profile['industry'] or 'Any'}")
    log_activity(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Step 4: Run the pipeline
    start_time = time.time()

    print("🚀 STARTING BULK OUTREACH PIPELINE")
    print("=" * 60)

    # Initial state — includes full candidate profile
    initial_state = {
        "job_role": profile["job_role"],
        "location": profile["location"],
        "experience_level": profile["experience_level"],
        "years_of_experience": profile["years_of_experience"],
        "skills": profile["skills"],
        "industry": profile["industry"],
        "seniority": profile["seniority"],
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
    print(f"      Job Role:          {profile['job_role']}")
    print(f"      Level:             {profile['seniority']}")
    print(f"      Location:          {profile['location'] or 'Any'}")
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
