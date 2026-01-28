#!/usr/bin/env python3
"""
Cleanup CRM API Duplicates Script

This script identifies and removes ONLY duplicate companies that were synced from
the Duano CRM API (data_sources=['douano_crm_api']) where the company name matches
an existing company from invoice_data or douano_api.

Companies with unique names (prospects without invoices) are KEPT.

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


def normalize_name(name):
    """Normalize company name for comparison"""
    if not name:
        return ''
    return name.lower().strip().replace(' ', '').replace('-', '').replace('.', '').replace(',', '')


def main():
    print("=" * 70)
    print("CLEANUP CRM API DUPLICATES (Smart Deduplication)")
    print("=" * 70)

    # Step 1: Fetch all companies
    print("\nStep 1: Fetching all companies...")

    all_companies = []
    offset = 0
    batch_size = 1000

    while True:
        result = supabase.table('companies').select(
            'id, company_id, name, public_name, data_sources'
        ).range(offset, offset + batch_size - 1).execute()

        if not result.data:
            break

        all_companies.extend(result.data)

        if len(result.data) < batch_size:
            break
        offset += batch_size

    print(f"   Total companies: {len(all_companies)}")

    # Step 2: Separate by source and build name lookup
    print("\nStep 2: Analyzing companies by source...")

    crm_api_companies = []
    non_crm_api_names = set()

    for c in all_companies:
        data_sources = c.get('data_sources', [])
        if data_sources == ['douano_crm_api']:
            crm_api_companies.append(c)
        else:
            # Build lookup of names from non-CRM-API companies
            non_crm_api_names.add(normalize_name(c.get('name', '')))
            non_crm_api_names.add(normalize_name(c.get('public_name', '')))

    print(f"   CRM API companies: {len(crm_api_companies)}")
    print(f"   Non-CRM-API company names: {len(non_crm_api_names)}")

    # Step 3: Identify actual duplicates vs unique prospects
    print("\nStep 3: Identifying duplicates vs unique prospects...")

    duplicates = []
    unique_prospects = []

    for c in crm_api_companies:
        name_norm = normalize_name(c.get('name', ''))
        public_name_norm = normalize_name(c.get('public_name', ''))

        if name_norm in non_crm_api_names or public_name_norm in non_crm_api_names:
            duplicates.append(c)
        else:
            unique_prospects.append(c)

    print(f"   Actual duplicates (to delete): {len(duplicates)}")
    print(f"   Unique prospects (to keep): {len(unique_prospects)}")

    if not duplicates:
        print("\nNo duplicates to clean up!")
        return

    # Step 4: Show examples
    print("\nExamples of DUPLICATES to delete:")
    for c in duplicates[:10]:
        print(f"   - {c.get('public_name') or c['name']} (CRM ID: {c['company_id']})")

    if len(duplicates) > 10:
        print(f"   ... and {len(duplicates) - 10} more")

    print("\nExamples of UNIQUE PROSPECTS to keep:")
    for c in unique_prospects[:10]:
        print(f"   - {c.get('public_name') or c['name']} (CRM ID: {c['company_id']})")

    if len(unique_prospects) > 10:
        print(f"   ... and {len(unique_prospects) - 10} more")

    # Step 5: Confirm deletion
    print(f"\nReady to DELETE {len(duplicates)} duplicate CRM API companies")
    print(f"   Will KEEP {len(unique_prospects)} unique prospects")

    response = input("\nProceed with deletion? (yes/no): ").strip().lower()

    if response != 'yes':
        print("Aborted.")
        return

    # Step 6: Delete duplicates
    print("\nDeleting duplicates...")

    deleted = 0
    errors = 0

    for c in duplicates:
        try:
            supabase.table('companies').delete().eq('id', c['id']).execute()
            deleted += 1
            if deleted % 50 == 0:
                print(f"   Deleted {deleted}/{len(duplicates)}...")
        except Exception as e:
            print(f"   Error deleting {c['name']}: {e}")
            errors += 1

    # Summary
    print("\n" + "=" * 70)
    print("CLEANUP COMPLETE")
    print("=" * 70)
    print(f"   Deleted: {deleted}")
    print(f"   Errors: {errors}")
    print(f"   Unique prospects preserved: {len(unique_prospects)}")
    print("\nDone!")


if __name__ == "__main__":
    main()
