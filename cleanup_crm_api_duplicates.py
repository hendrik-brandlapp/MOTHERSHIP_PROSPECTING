#!/usr/bin/env python3
"""
Cleanup CRM API Duplicates Script

This script identifies and removes duplicate companies that were synced from
the Duano CRM API (data_sources=['douano_crm_api']). These are duplicates of
CORE companies that have different IDs.

The CRM API uses different company IDs than the CORE API (which is used for invoices).
This creates duplicates when:
1. Companies are synced from invoices (CORE IDs)
2. Companies are also synced from CRM API (CRM IDs)

Run with: python3 cleanup_crm_api_duplicates.py
"""

import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: Missing SUPABASE_URL or SUPABASE_KEY in environment")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def main():
    print("=" * 70)
    print("🧹 CLEANUP CRM API DUPLICATES")
    print("=" * 70)

    # Step 1: Find all CRM API only companies
    print("\n📊 Step 1: Finding CRM API only companies...")

    crm_api_companies = []
    offset = 0
    batch_size = 1000

    while True:
        result = supabase.table('companies').select(
            'id, company_id, name, public_name, data_sources'
        ).range(offset, offset + batch_size - 1).execute()

        if not result.data:
            break

        for c in result.data:
            if c.get('data_sources') == ['douano_crm_api']:
                crm_api_companies.append(c)

        if len(result.data) < batch_size:
            break
        offset += batch_size

    print(f"   Found {len(crm_api_companies)} CRM API only companies")

    if not crm_api_companies:
        print("\n✅ No CRM API duplicates to clean up!")
        return

    # Step 2: Show examples
    print("\n📋 Examples of CRM API duplicates:")
    for c in crm_api_companies[:10]:
        print(f"   - {c['name']} (CRM ID: {c['company_id']})")

    if len(crm_api_companies) > 10:
        print(f"   ... and {len(crm_api_companies) - 10} more")

    # Step 3: Confirm deletion
    print(f"\n⚠️  Ready to DELETE {len(crm_api_companies)} CRM API duplicate companies")
    print("   These are duplicates with CRM IDs (not CORE IDs)")
    print("   They don't have invoice data and show as duplicates in the UI")

    response = input("\nProceed with deletion? (yes/no): ").strip().lower()

    if response != 'yes':
        print("Aborted.")
        return

    # Step 4: Delete CRM API duplicates
    print("\n🗑️  Deleting CRM API duplicates...")

    deleted = 0
    errors = 0

    for c in crm_api_companies:
        try:
            supabase.table('companies').delete().eq('id', c['id']).execute()
            deleted += 1
            if deleted % 50 == 0:
                print(f"   Deleted {deleted}/{len(crm_api_companies)}...")
        except Exception as e:
            print(f"   ❌ Error deleting {c['name']}: {e}")
            errors += 1

    # Summary
    print("\n" + "=" * 70)
    print("📊 CLEANUP COMPLETE")
    print("=" * 70)
    print(f"   ✅ Deleted: {deleted}")
    print(f"   ❌ Errors: {errors}")
    print("\nDone!")


if __name__ == "__main__":
    main()
