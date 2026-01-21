"""
Retry Failed CRM Imports

Retries the 22 records that failed due to language column being too short.
Run AFTER executing: ALTER TABLE companies ALTER COLUMN language TYPE VARCHAR(50);

Run with: python3 retry_failed_imports.py
"""

import csv
import re
import time
from datetime import datetime
from collections import defaultdict
from supabase import create_client

# Configuration
SUPABASE_URL = "https://gpjoypslbrpvnhqzvacc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imdwam95cHNsYnJwdm5ocXp2YWNjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTM3MDQxNTAsImV4cCI6MjA2OTI4MDE1MH0.u0hGzIKziSPz2i576NhuyCetV6_iQwCoft7FIjDJCiI"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

CSV_PATH = '/Users/hendrikdewinne/MOTHERSHIP_PROSPECTING/2026-01-20_location_export.csv'

# The 22 failed records
FAILED_NAMES = [
    "Barket l Comptoir gourmand take-away",
    "BelMundo",
    "Café Walvis",
    "Caleo Café",
    "Claw",
    "Colruyt",
    "DoubleTree by Hilton Brussels City",
    "GIMIC Radio",
    "Goyo",
    "Green House",
    "Iyagi Korean Takeaway",
    "JeanBon Louise",
    "Life Bar",
    "Liu Lin",
    "Lucifer Lives",
    "Muski Comics Café",
    "Nomade Coffee Brussels",
    "Renard Bakery",
    "Terter",
    "The WAYNE Café",
    "ToiToiToi Coffee x Culture / Antwerpen",
    "Van de Velde Stadscafe"
]


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
    result = {'address_line1': '', 'city': '', 'post_code': '', 'country_name': ''}
    parts = [p.strip() for p in address.split(',')]
    if len(parts) >= 1:
        result['address_line1'] = parts[0]
    if len(parts) >= 2:
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
        return float(parts[0].strip()), float(parts[1].strip())
    except (ValueError, IndexError):
        return None, None


def parse_products(product_string):
    """Parse product list into JSON array."""
    if not product_string or not product_string.strip():
        return []
    return [p.strip() for p in product_string.split(',') if p.strip()]


def parse_suppliers(supplier_string):
    """Parse suppliers into JSON array."""
    if not supplier_string or not supplier_string.strip():
        return []
    return [s.strip() for s in supplier_string.split(',') if s.strip()]


def build_company_record_from_csv(csv_record, is_new=True):
    """Build a company record from CSV data."""
    address_parts = parse_address(csv_record.get('Address', ''))
    lat, lng = parse_coordinates(csv_record.get('Coordinates', ''))

    record = {
        'name': csv_record.get('Name', ''),
        'public_name': csv_record.get('Name', ''),
        'address_line1': address_parts.get('address_line1', ''),
        'city': address_parts.get('city', ''),
        'post_code': address_parts.get('post_code', ''),
        'country_name': address_parts.get('country_name', 'Belgium'),
        'latitude': lat,
        'longitude': lng,
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
        'suppliers': parse_suppliers(csv_record.get('Suppliers', '')),
        'crm_notes': csv_record.get('Notes', '') or None,
        'activations': csv_record.get('Activations', '') or None,
        'products_proposed': parse_products(csv_record.get('Proposed', '')),
        'products_sampled': parse_products(csv_record.get('Sampled', '')),
        'products_listed': parse_products(csv_record.get('Listed', '')),
        'products_won': parse_products(csv_record.get('Win', '')),
        'contact_person_name': csv_record.get('Contact 1 Name', '') or None,
        'contact_person_role': csv_record.get('Contact 1 Role', '') or None,
        'contact_person_email': csv_record.get('Contact 1 Email', '') or None,
        'contact_person_phone': csv_record.get('Contact 1 Phone', '') or None,
        'contact_2_name': csv_record.get('Contact 2 Name', '') or None,
        'contact_2_role': csv_record.get('Contact 2 Role', '') or None,
        'contact_2_email': csv_record.get('Contact 2 Email', '') or None,
        'contact_2_phone': csv_record.get('Contact 2 Phone', '') or None,
        'contact_3_name': csv_record.get('Contact 3 Name', '') or None,
        'contact_3_role': csv_record.get('Contact 3 Role', '') or None,
        'contact_3_email': csv_record.get('Contact 3 Email', '') or None,
        'contact_3_phone': csv_record.get('Contact 3 Phone', '') or None,
        'imported_from_crm': True,
        'crm_import_date': datetime.now().isoformat(),
        'data_sources': ['crm_import'],
    }

    if is_new:
        lead_status = csv_record.get('Lead Status', '')
        record['is_customer'] = lead_status == 'Customer'
        record['is_supplier'] = False

    # Remove None values
    record = {k: v for k, v in record.items() if v is not None and v != ''}
    return record


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


def main():
    print("=" * 70)
    print("RETRY FAILED CRM IMPORTS")
    print("=" * 70)
    print(f"Retrying {len(FAILED_NAMES)} failed records...")
    print("\nMake sure you have run this SQL first:")
    print("  ALTER TABLE companies ALTER COLUMN language TYPE VARCHAR(50);")
    print()

    # Load CSV data
    print("Loading CSV data...")
    csv_records = load_csv_data()

    # Filter to only failed records
    failed_records = [r for r in csv_records if r.get('Name', '') in FAILED_NAMES]
    print(f"Found {len(failed_records)} failed records in CSV")

    # Load existing companies to check for matches
    print("Loading existing companies...")
    db_companies = load_existing_companies()

    # Build name index
    db_names_index = defaultdict(list)
    for company in db_companies:
        norm_name = normalize_name(company.get('name') or company.get('public_name'))
        if norm_name:
            db_names_index[norm_name].append(company)

    # Process each failed record
    success_count = 0
    error_count = 0
    errors = []

    for csv_record in failed_records:
        name = csv_record.get('Name', '')
        norm_name = normalize_name(name)

        print(f"\nProcessing: {name}")

        # Check if it exists in DB (was it an update or insert that failed?)
        existing = db_names_index.get(norm_name, [])

        if existing:
            # Update existing record
            db_record = existing[0]
            company_id = db_record.get('company_id') or db_record.get('id')

            csv_data = build_company_record_from_csv(csv_record, is_new=False)
            update_data = {}

            # CRM-specific fields
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

            # Update missing fields
            for field in ['contact_person_name', 'contact_person_email', 'contact_person_phone', 'assigned_salesperson']:
                if csv_data.get(field) and not db_record.get(field):
                    update_data[field] = csv_data[field]

            if not db_record.get('latitude') and csv_data.get('latitude'):
                update_data['latitude'] = csv_data['latitude']
                update_data['longitude'] = csv_data.get('longitude')

            for field in ['address_line1', 'city', 'post_code']:
                if csv_data.get(field) and not db_record.get(field):
                    update_data[field] = csv_data[field]

            update_data['imported_from_crm'] = True
            update_data['crm_import_date'] = datetime.now().isoformat()

            try:
                supabase.table('companies').update(update_data).eq('company_id', company_id).execute()
                print(f"  ✅ Updated existing record")
                success_count += 1
            except Exception as e:
                print(f"  ❌ Update failed: {e}")
                error_count += 1
                errors.append({'name': name, 'error': str(e)})

        else:
            # Insert new record
            record = build_company_record_from_csv(csv_record, is_new=True)
            record['company_id'] = -int(time.time() * 1000) % 1000000000

            try:
                supabase.table('companies').insert(record).execute()
                print(f"  ✅ Inserted new record")
                success_count += 1
            except Exception as e:
                print(f"  ❌ Insert failed: {e}")
                error_count += 1
                errors.append({'name': name, 'error': str(e)})

        time.sleep(0.2)  # Small delay

    # Summary
    print("\n" + "=" * 70)
    print("RETRY COMPLETE")
    print("=" * 70)
    print(f"  ✅ Successful: {success_count}")
    print(f"  ❌ Failed: {error_count}")

    if errors:
        print("\nRemaining errors:")
        for err in errors:
            print(f"  - {err['name']}: {err['error'][:80]}")


if __name__ == "__main__":
    main()
