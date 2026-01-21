"""
ROLLBACK CRM IMPORT

This script reverses the damage from the bad CRM import:
1. Clears CRM fields from existing companies that were wrongly updated
2. Deletes all newly inserted CRM-only companies (negative company_id)

Run with: python3 rollback_crm_import.py
"""

from supabase import create_client
from datetime import datetime

# Configuration
SUPABASE_URL = "https://gpjoypslbrpvnhqzvacc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imdwam95cHNsYnJwdm5ocXp2YWNjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTM3MDQxNTAsImV4cCI6MjA2OTI4MDE1MH0.u0hGzIKziSPz2i576NhuyCetV6_iQwCoft7FIjDJCiI"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def main():
    print("=" * 70)
    print("ROLLBACK CRM IMPORT")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Step 1: Find all companies that were marked as imported from CRM
    print("\n📊 Finding affected companies...")

    result = supabase.table('companies').select('id, company_id, name, imported_from_crm').eq('imported_from_crm', True).execute()

    affected = result.data if result.data else []
    print(f"   Found {len(affected)} companies marked as CRM imported")

    # Separate into: newly inserted (negative IDs) vs updated existing (positive IDs)
    new_inserts = [c for c in affected if c['company_id'] < 0]
    updated_existing = [c for c in affected if c['company_id'] > 0]

    print(f"   - New inserts (to DELETE): {len(new_inserts)}")
    print(f"   - Updated existing (to CLEAR CRM fields): {len(updated_existing)}")

    # Show sample of updated existing companies
    if updated_existing:
        print("\n   Sample of existing companies that were wrongly updated:")
        for c in updated_existing[:10]:
            print(f"      - {c['name']} (ID: {c['company_id']})")

    # Ask to proceed
    print(f"\n⚠️  This will:")
    print(f"   - DELETE {len(new_inserts)} newly inserted companies")
    print(f"   - CLEAR CRM fields from {len(updated_existing)} existing companies")
    response = input("\nProceed with rollback? (y/n): ").strip().lower()

    if response != 'y':
        print("Aborted.")
        return

    # Step 2: Delete newly inserted companies (negative company_id)
    print("\n🗑️  Deleting newly inserted CRM companies...")
    delete_count = 0
    delete_errors = []

    for company in new_inserts:
        try:
            supabase.table('companies').delete().eq('id', company['id']).execute()
            delete_count += 1
            if delete_count % 100 == 0:
                print(f"   Deleted {delete_count}/{len(new_inserts)}...")
        except Exception as e:
            delete_errors.append({'name': company['name'], 'error': str(e)})

    print(f"   ✅ Deleted {delete_count} companies")
    if delete_errors:
        print(f"   ❌ {len(delete_errors)} delete errors")

    # Step 3: Clear CRM fields from existing companies
    print("\n🧹 Clearing CRM fields from existing companies...")

    # Fields to clear (set to NULL)
    clear_fields = {
        'lead_status': None,
        'channel': None,
        'language': None,
        'priority': None,
        'province': None,
        'sub_type': None,
        'business_type': None,
        'parent_company': None,
        'suppliers': None,
        'crm_notes': None,
        'activations': None,
        'external_account_number': None,
        'products_proposed': None,
        'products_sampled': None,
        'products_listed': None,
        'products_won': None,
        'contact_person_role': None,
        'contact_2_name': None,
        'contact_2_role': None,
        'contact_2_email': None,
        'contact_2_phone': None,
        'contact_3_name': None,
        'contact_3_role': None,
        'contact_3_email': None,
        'contact_3_phone': None,
        'imported_from_crm': False,
        'crm_import_date': None
    }

    clear_count = 0
    clear_errors = []

    for company in updated_existing:
        try:
            supabase.table('companies').update(clear_fields).eq('company_id', company['company_id']).execute()
            clear_count += 1
            if clear_count % 50 == 0:
                print(f"   Cleared {clear_count}/{len(updated_existing)}...")
        except Exception as e:
            clear_errors.append({'name': company['name'], 'error': str(e)})

    print(f"   ✅ Cleared CRM fields from {clear_count} companies")
    if clear_errors:
        print(f"   ❌ {len(clear_errors)} clear errors")

    # Summary
    print("\n" + "=" * 70)
    print("ROLLBACK COMPLETE")
    print("=" * 70)
    print(f"   Deleted: {delete_count} new CRM companies")
    print(f"   Cleared: {clear_count} existing companies")
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
