"""
CRM Data Import Script

Imports data from the 2026-01-20_location_export.csv into the companies table.
- Updates 169 existing companies with CRM data
- Inserts 993 new records (including Unqualified and Ex-customer to avoid repeat mistakes)

Run with: python3 import_crm_data.py
"""

import csv
import re
import json
from datetime import datetime
from collections import defaultdict
from supabase import create_client

# Configuration
SUPABASE_URL = "https://gpjoypslbrpvnhqzvacc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imdwam95cHNsYnJwdm5ocXp2YWNjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTM3MDQxNTAsImV4cCI6MjA2OTI4MDE1MH0.u0hGzIKziSPz2i576NhuyCetV6_iQwCoft7FIjDJCiI"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

CSV_PATH = '/Users/hendrikdewinne/MOTHERSHIP_PROSPECTING/2026-01-20_location_export.csv'


def normalize_name(name):
    """Normalize company name for matching."""
    if not name:
        return ""
    name = name.lower().strip()
    for suffix in [' bv', ' bvba', ' nv', ' sprl', ' sa', ' cvba', ' vzw', ' asbl']:
        name = name.replace(suffix, '')
    name = re.sub(r'[^a-z0-9\s]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def parse_address(address):
    """Parse address string into components."""
    if not address:
        return {}

    result = {
        'address_line1': '',
        'city': '',
        'post_code': '',
        'country_name': ''
    }

    # Belgian address format: "Street 123, 1234 City, Country"
    parts = [p.strip() for p in address.split(',')]

    if len(parts) >= 1:
        result['address_line1'] = parts[0]

    if len(parts) >= 2:
        # Try to extract postal code and city
        city_part = parts[1].strip()
        match = re.match(r'(\d{4,5})\s+(.+)', city_part)
        if match:
            result['post_code'] = match.group(1)
            result['city'] = match.group(2)
        else:
            result['city'] = city_part

    if len(parts) >= 3:
        result['country_name'] = parts[2].strip()

    return result


def parse_coordinates(coord_string):
    """Parse coordinates from '51.057265,3.724585' format."""
    if not coord_string or ',' not in coord_string:
        return None, None

    try:
        parts = coord_string.split(',')
        lat = float(parts[0].strip())
        lng = float(parts[1].strip())
        return lat, lng
    except (ValueError, IndexError):
        return None, None


def parse_products(product_string):
    """Parse product list into JSON array."""
    if not product_string or not product_string.strip():
        return []

    # Products are comma-separated
    products = [p.strip() for p in product_string.split(',') if p.strip()]
    return products


def parse_suppliers(supplier_string):
    """Parse suppliers into JSON array."""
    if not supplier_string or not supplier_string.strip():
        return []

    suppliers = [s.strip() for s in supplier_string.split(',') if s.strip()]
    return suppliers


def load_csv_data():
    """Load and parse the CSV file."""
    records = []
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            records.append(row)
    return records


def load_existing_companies():
    """Load all companies from the database."""
    all_companies = []
    batch_size = 1000
    offset = 0

    while True:
        result = supabase.table('companies').select('*').range(offset, offset + batch_size - 1).execute()
        if not result.data:
            break
        all_companies.extend(result.data)
        if len(result.data) < batch_size:
            break
        offset += batch_size

    return all_companies


def normalize_postal_code(address):
    """Extract postal code from address."""
    if not address:
        return ""
    match = re.search(r'\b(\d{4})\b', address)
    return match.group(1) if match else ""


def build_company_record_from_csv(csv_record, is_new=True):
    """Build a company record from CSV data."""

    # Parse address
    address_parts = parse_address(csv_record.get('Address', ''))

    # Parse coordinates
    lat, lng = parse_coordinates(csv_record.get('Coordinates', ''))

    # Build record
    record = {
        # Basic info
        'name': csv_record.get('Name', ''),
        'public_name': csv_record.get('Name', ''),

        # Address fields
        'address_line1': address_parts.get('address_line1', ''),
        'city': address_parts.get('city', ''),
        'post_code': address_parts.get('post_code', ''),
        'country_name': address_parts.get('country_name', 'Belgium'),

        # Coordinates
        'latitude': lat,
        'longitude': lng,

        # CRM fields
        'external_account_number': csv_record.get('Account Number', '') or None,
        'channel': csv_record.get('Channel', '') or None,
        'language': csv_record.get('Language', '') or None,
        'lead_status': csv_record.get('Lead Status', '') or None,
        'priority': csv_record.get('Priority', '') or None,
        'province': csv_record.get('Province / Region', '') or None,
        'sub_type': csv_record.get('Sub Type', '') or None,
        'business_type': csv_record.get('Type (Yugen Website)', '') or None,
        'parent_company': csv_record.get('Parent Company', '') or None,
        'assigned_salesperson': csv_record.get('Company Owner', '') or None,

        # Suppliers as JSON
        'suppliers': parse_suppliers(csv_record.get('Suppliers', '')),

        # Notes
        'crm_notes': csv_record.get('Notes', '') or None,
        'activations': csv_record.get('Activations', '') or None,

        # Products as JSON arrays
        'products_proposed': parse_products(csv_record.get('Proposed', '')),
        'products_sampled': parse_products(csv_record.get('Sampled', '')),
        'products_listed': parse_products(csv_record.get('Listed', '')),
        'products_won': parse_products(csv_record.get('Win', '')),

        # Contact 1
        'contact_person_name': csv_record.get('Contact 1 Name', '') or None,
        'contact_person_role': csv_record.get('Contact 1 Role', '') or None,
        'contact_person_email': csv_record.get('Contact 1 Email', '') or None,
        'contact_person_phone': csv_record.get('Contact 1 Phone', '') or None,

        # Contact 2
        'contact_2_name': csv_record.get('Contact 2 Name', '') or None,
        'contact_2_role': csv_record.get('Contact 2 Role', '') or None,
        'contact_2_email': csv_record.get('Contact 2 Email', '') or None,
        'contact_2_phone': csv_record.get('Contact 2 Phone', '') or None,

        # Contact 3
        'contact_3_name': csv_record.get('Contact 3 Name', '') or None,
        'contact_3_role': csv_record.get('Contact 3 Role', '') or None,
        'contact_3_email': csv_record.get('Contact 3 Email', '') or None,
        'contact_3_phone': csv_record.get('Contact 3 Phone', '') or None,

        # Import tracking
        'imported_from_crm': True,
        'crm_import_date': datetime.now().isoformat(),
        'data_sources': ['crm_import'],
    }

    # For new records, set customer status based on lead_status
    if is_new:
        lead_status = csv_record.get('Lead Status', '')
        record['is_customer'] = lead_status == 'Customer'
        record['is_supplier'] = False

    # Remove None values for cleaner inserts
    record = {k: v for k, v in record.items() if v is not None and v != ''}

    return record


def find_matches(csv_records, db_companies):
    """Find matches between CSV records and existing database records."""

    # Build lookup indexes
    db_names_index = defaultdict(list)
    db_postal_index = defaultdict(list)

    for company in db_companies:
        norm_name = normalize_name(company.get('name') or company.get('public_name'))
        if norm_name:
            db_names_index[norm_name].append(company)

        norm_public = normalize_name(company.get('public_name'))
        if norm_public and norm_public != norm_name:
            db_names_index[norm_public].append(company)

        postal = company.get('post_code')
        if postal:
            db_postal_index[str(postal)].append(company)

    # Match results
    exact_matches = []
    no_matches = []

    for csv_record in csv_records:
        csv_name = csv_record.get('Name', '')
        csv_address = csv_record.get('Address', '')
        csv_postal = normalize_postal_code(csv_address)
        norm_csv_name = normalize_name(csv_name)

        match_found = False
        matched_record = None

        # Try exact name match
        if norm_csv_name in db_names_index:
            matches = db_names_index[norm_csv_name]
            # If multiple matches, narrow by postal code
            if csv_postal:
                postal_filtered = [m for m in matches if str(m.get('post_code', '')) == csv_postal]
                if postal_filtered:
                    matches = postal_filtered

            if matches:
                matched_record = matches[0]
                exact_matches.append({
                    'csv_record': csv_record,
                    'db_record': matched_record
                })
                match_found = True

        if not match_found:
            no_matches.append(csv_record)

    return exact_matches, no_matches


def update_existing_company(db_record, csv_record):
    """Update an existing company with CRM data."""

    company_id = db_record.get('company_id') or db_record.get('id')

    # Build update data (only CRM fields, preserve existing data)
    update_data = {}

    # Only update if CSV has data and DB doesn't
    def set_if_missing(db_field, csv_value):
        if csv_value and not db_record.get(db_field):
            update_data[db_field] = csv_value

    # Always update these CRM fields
    csv_data = build_company_record_from_csv(csv_record, is_new=False)

    # CRM-specific fields (always update if CSV has data)
    crm_fields = [
        'external_account_number', 'channel', 'language', 'lead_status',
        'priority', 'province', 'sub_type', 'business_type', 'parent_company',
        'crm_notes', 'activations',
        'products_proposed', 'products_sampled', 'products_listed', 'products_won',
        'contact_person_role', 'contact_2_name', 'contact_2_role', 'contact_2_email',
        'contact_2_phone', 'contact_3_name', 'contact_3_role', 'contact_3_email', 'contact_3_phone'
    ]

    for field in crm_fields:
        if field in csv_data and csv_data[field]:
            update_data[field] = csv_data[field]

    # Update contact info only if missing
    set_if_missing('contact_person_name', csv_data.get('contact_person_name'))
    set_if_missing('contact_person_email', csv_data.get('contact_person_email'))
    set_if_missing('contact_person_phone', csv_data.get('contact_person_phone'))
    set_if_missing('assigned_salesperson', csv_data.get('assigned_salesperson'))

    # Update coordinates only if missing
    if not db_record.get('latitude') and csv_data.get('latitude'):
        update_data['latitude'] = csv_data['latitude']
        update_data['longitude'] = csv_data.get('longitude')

    # Update address only if missing
    set_if_missing('address_line1', csv_data.get('address_line1'))
    set_if_missing('city', csv_data.get('city'))
    set_if_missing('post_code', csv_data.get('post_code'))

    # Update suppliers as array
    if csv_data.get('suppliers'):
        existing_suppliers = db_record.get('suppliers', []) or []
        new_suppliers = csv_data['suppliers']
        combined = list(set(existing_suppliers + new_suppliers))
        if combined:
            update_data['suppliers'] = combined

    # Mark as imported
    update_data['imported_from_crm'] = True
    update_data['crm_import_date'] = datetime.now().isoformat()

    # Update data_sources
    existing_sources = db_record.get('data_sources', []) or []
    if 'crm_import' not in existing_sources:
        update_data['data_sources'] = existing_sources + ['crm_import']

    if update_data:
        try:
            supabase.table('companies').update(update_data).eq('company_id', company_id).execute()
            return True, None
        except Exception as e:
            return False, str(e)

    return True, "No updates needed"


def insert_new_company(csv_record):
    """Insert a new company from CSV data."""

    record = build_company_record_from_csv(csv_record, is_new=True)

    # Generate a unique company_id (negative to distinguish from Duano IDs)
    # We'll use timestamp-based IDs
    import time
    record['company_id'] = -int(time.time() * 1000) % 1000000000

    try:
        supabase.table('companies').insert(record).execute()
        return True, None
    except Exception as e:
        return False, str(e)


def main():
    print("=" * 70)
    print("CRM DATA IMPORT")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Load data
    print("\n📊 Loading data...")
    csv_records = load_csv_data()
    print(f"   CSV records: {len(csv_records)}")

    db_companies = load_existing_companies()
    print(f"   Existing companies: {len(db_companies)}")

    # Find matches
    print("\n🔍 Finding matches...")
    exact_matches, no_matches = find_matches(csv_records, db_companies)
    print(f"   Exact matches (to update): {len(exact_matches)}")
    print(f"   New records (to insert): {len(no_matches)}")

    # Ask to proceed
    print(f"\n⚠️  Ready to:")
    print(f"   - UPDATE {len(exact_matches)} existing companies")
    print(f"   - INSERT {len(no_matches)} new companies")
    response = input("\nProceed? (y/n): ").strip().lower()

    if response != 'y':
        print("Aborted.")
        return

    # Update existing companies
    print("\n📝 Updating existing companies...")
    update_success = 0
    update_errors = []

    for i, match in enumerate(exact_matches):
        csv_record = match['csv_record']
        db_record = match['db_record']

        success, error = update_existing_company(db_record, csv_record)

        if success:
            update_success += 1
            print(f"   [{i+1}/{len(exact_matches)}] ✅ Updated: {csv_record.get('Name', '')[:40]}")
        else:
            update_errors.append({'name': csv_record.get('Name', ''), 'error': error})
            print(f"   [{i+1}/{len(exact_matches)}] ❌ Error: {csv_record.get('Name', '')[:40]} - {error}")

    # Insert new companies
    print("\n📥 Inserting new companies...")
    insert_success = 0
    insert_errors = []

    for i, csv_record in enumerate(no_matches):
        success, error = insert_new_company(csv_record)

        if success:
            insert_success += 1
            status = csv_record.get('Lead Status', 'Unknown')
            print(f"   [{i+1}/{len(no_matches)}] ✅ Inserted: {csv_record.get('Name', '')[:35]} ({status})")
        else:
            insert_errors.append({'name': csv_record.get('Name', ''), 'error': error})
            print(f"   [{i+1}/{len(no_matches)}] ❌ Error: {csv_record.get('Name', '')[:40]} - {error}")

        # Small delay to avoid rate limiting
        if (i + 1) % 50 == 0:
            import time
            print(f"   ... {i+1} processed, pausing briefly...")
            time.sleep(0.5)

    # Summary
    print("\n" + "=" * 70)
    print("IMPORT COMPLETE")
    print("=" * 70)
    print(f"\n📊 Results:")
    print(f"   Updates: {update_success}/{len(exact_matches)} successful")
    print(f"   Inserts: {insert_success}/{len(no_matches)} successful")

    if update_errors:
        print(f"\n❌ Update errors ({len(update_errors)}):")
        for err in update_errors[:10]:
            print(f"   - {err['name']}: {err['error']}")

    if insert_errors:
        print(f"\n❌ Insert errors ({len(insert_errors)}):")
        for err in insert_errors[:10]:
            print(f"   - {err['name']}: {err['error']}")

    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
