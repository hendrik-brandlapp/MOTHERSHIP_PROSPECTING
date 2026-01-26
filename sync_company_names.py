#!/usr/bin/env python3
"""
Sync company names from Duano API to ensure both name (legal) and public_name (display) are properly set.
"""

import os
import sys
import time
import requests
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

# Supabase setup
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: Missing SUPABASE_URL or SUPABASE_KEY in environment")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Duano API setup
DOUANO_BASE_URL = os.getenv('DOUANO_BASE_URL')
DOUANO_ACCESS_TOKEN = os.getenv('DOUANO_ACCESS_TOKEN')

if not DOUANO_BASE_URL or not DOUANO_ACCESS_TOKEN:
    print("ERROR: Missing DOUANO_BASE_URL or DOUANO_ACCESS_TOKEN in environment")
    print("You need to be logged in to get a valid access token.")
    sys.exit(1)


def fetch_all_duano_companies():
    """Fetch all companies from Duano API with pagination."""
    headers = {
        'Authorization': f'Bearer {DOUANO_ACCESS_TOKEN}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    all_companies = []
    page = 1
    per_page = 100

    while True:
        print(f"  Fetching page {page}...")

        try:
            # Use the CRM companies endpoint which returns full data
            url = f"{DOUANO_BASE_URL}/api/public/v1/crm/crm-companies"
            response = requests.get(
                url,
                headers=headers,
                params={'page': page, 'per_page': per_page},
                timeout=60
            )

            if response.status_code == 401:
                print("ERROR: Access token expired. Please log in again to refresh the token.")
                sys.exit(1)

            if response.status_code != 200:
                print(f"ERROR: API returned {response.status_code}: {response.text[:200]}")
                break

            data = response.json()
            result = data.get('result', {})
            companies = result.get('data', [])

            if not companies:
                break

            all_companies.extend(companies)
            print(f"  Got {len(companies)} companies (total: {len(all_companies)})")

            # Check pagination
            current_page = result.get('current_page', page)
            last_page = result.get('last_page', 1)

            if current_page >= last_page:
                break

            page += 1
            time.sleep(0.2)  # Rate limiting

        except Exception as e:
            print(f"ERROR fetching page {page}: {e}")
            break

    return all_companies


def update_company_names():
    """Update company names in Supabase from Duano API data."""

    print("=" * 60)
    print("SYNC COMPANY NAMES FROM DUANO")
    print("=" * 60)

    # Step 1: Fetch all companies from Duano
    print("\n1. Fetching companies from Duano API...")
    duano_companies = fetch_all_duano_companies()
    print(f"   Fetched {len(duano_companies)} companies from Duano")

    if not duano_companies:
        print("No companies fetched. Exiting.")
        return

    # Step 2: Get existing companies from Supabase
    print("\n2. Fetching existing companies from Supabase...")
    existing = {}
    offset = 0
    batch_size = 1000

    while True:
        result = supabase.table('companies').select('id, company_id, name, public_name').range(offset, offset + batch_size - 1).execute()
        if not result.data:
            break
        for c in result.data:
            if c.get('company_id'):
                existing[c['company_id']] = c
        if len(result.data) < batch_size:
            break
        offset += batch_size

    print(f"   Found {len(existing)} existing companies in database")

    # Step 3: Update companies with correct name/public_name
    print("\n3. Updating company names...")

    updated = 0
    skipped = 0
    not_found = 0
    different_names = []

    for company in duano_companies:
        company_id = company.get('id')
        legal_name = company.get('name')  # This is the legal/registered name
        public_name = company.get('public_name')  # This is the display/trading name

        if not company_id:
            continue

        if company_id not in existing:
            not_found += 1
            continue

        db_record = existing[company_id]

        # Check if update is needed
        needs_update = False
        update_data = {}

        if legal_name and db_record.get('name') != legal_name:
            update_data['name'] = legal_name
            needs_update = True

        if public_name and db_record.get('public_name') != public_name:
            update_data['public_name'] = public_name
            needs_update = True

        if needs_update:
            try:
                supabase.table('companies').update(update_data).eq('company_id', company_id).execute()
                updated += 1

                # Track companies where legal != public name
                if legal_name and public_name and legal_name != public_name:
                    different_names.append({
                        'company_id': company_id,
                        'legal': legal_name,
                        'public': public_name
                    })

                if updated % 100 == 0:
                    print(f"   Updated {updated} companies...")

            except Exception as e:
                print(f"   Error updating company {company_id}: {e}")
        else:
            skipped += 1

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total Duano companies: {len(duano_companies)}")
    print(f"Companies updated: {updated}")
    print(f"Companies skipped (no changes): {skipped}")
    print(f"Companies not in database: {not_found}")

    if different_names:
        print(f"\nCompanies with different legal vs public names: {len(different_names)}")
        print("\nExamples (first 20):")
        for c in different_names[:20]:
            print(f"  - Legal: '{c['legal']}' -> Public: '{c['public']}'")

    print("\nDone!")


if __name__ == '__main__':
    update_company_names()
