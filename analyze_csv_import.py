"""
CSV Import Analysis Script

Analyzes the location_export.csv to:
1. Find overlaps with existing companies in the database
2. Identify new columns needed
3. Generate import recommendations
"""

import csv
import re
from collections import defaultdict
from supabase import create_client

# Configuration
SUPABASE_URL = "https://gpjoypslbrpvnqzvacc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imdwam95cHNsYnJwdm5ocXp2YWNjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTM3MDQxNTAsImV4cCI6MjA2OTI4MDE1MH0.u0hGzIKziSPz2i576NhuyCetV6_iQwCoft7FIjDJCiI"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def normalize_name(name):
    """Normalize company name for matching."""
    if not name:
        return ""
    # Lowercase, remove extra spaces, remove common suffixes
    name = name.lower().strip()
    # Remove common business suffixes
    for suffix in [' bv', ' bvba', ' nv', ' sprl', ' sa', ' cvba', ' vzw', ' asbl']:
        name = name.replace(suffix, '')
    # Remove special characters, keep only alphanumeric and spaces
    name = re.sub(r'[^a-z0-9\s]', '', name)
    # Collapse multiple spaces
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def extract_city_from_address(address):
    """Extract city from an address string."""
    if not address:
        return ""
    # Belgian addresses usually end with: postal_code City, Country
    # Try to extract city
    parts = address.split(',')
    if len(parts) >= 2:
        # Get the part before country (usually "postal_code City")
        city_part = parts[-2].strip() if len(parts) > 2 else parts[-1].strip()
        # Extract city (usually after postal code)
        match = re.search(r'\d{4}\s+(.+)', city_part)
        if match:
            return match.group(1).strip().lower()
    return ""


def normalize_postal_code(address):
    """Extract postal code from address."""
    if not address:
        return ""
    match = re.search(r'\b(\d{4})\b', address)
    return match.group(1) if match else ""


def load_csv_data(filepath):
    """Load and parse the CSV file."""
    records = []
    with open(filepath, 'r', encoding='utf-8') as f:
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
        result = supabase.table('companies').select(
            'id, company_id, name, public_name, vat_number, address_line1, city, post_code, latitude, longitude'
        ).range(offset, offset + batch_size - 1).execute()

        if not result.data:
            break

        all_companies.extend(result.data)

        if len(result.data) < batch_size:
            break

        offset += batch_size

    return all_companies


def load_existing_prospects():
    """Load all prospects from the database."""
    all_prospects = []
    batch_size = 1000
    offset = 0

    while True:
        try:
            result = supabase.table('prospects').select(
                'id, name, address, city, postal_code, latitude, longitude'
            ).range(offset, offset + batch_size - 1).execute()

            if not result.data:
                break

            all_prospects.extend(result.data)

            if len(result.data) < batch_size:
                break

            offset += batch_size
        except Exception as e:
            print(f"Note: Could not load prospects table: {e}")
            break

    return all_prospects


def find_matches(csv_records, db_companies, db_prospects):
    """Find matches between CSV records and existing database records."""

    # Build lookup indexes for faster matching
    db_names_index = defaultdict(list)
    db_postal_index = defaultdict(list)

    for company in db_companies:
        norm_name = normalize_name(company.get('name') or company.get('public_name'))
        if norm_name:
            db_names_index[norm_name].append(('company', company))

        # Also index by public_name
        norm_public = normalize_name(company.get('public_name'))
        if norm_public and norm_public != norm_name:
            db_names_index[norm_public].append(('company', company))

        # Index by postal code
        postal = company.get('post_code')
        if postal:
            db_postal_index[str(postal)].append(('company', company))

    for prospect in db_prospects:
        norm_name = normalize_name(prospect.get('name'))
        if norm_name:
            db_names_index[norm_name].append(('prospect', prospect))

        postal = prospect.get('postal_code')
        if postal:
            db_postal_index[str(postal)].append(('prospect', prospect))

    # Match results
    exact_matches = []
    fuzzy_matches = []
    no_matches = []

    for csv_record in csv_records:
        csv_name = csv_record.get('Name', '')
        csv_address = csv_record.get('Address', '')
        csv_postal = normalize_postal_code(csv_address)
        csv_city = extract_city_from_address(csv_address)
        norm_csv_name = normalize_name(csv_name)

        match_found = False
        match_type = None
        matched_record = None

        # 1. Try exact name match
        if norm_csv_name in db_names_index:
            matches = db_names_index[norm_csv_name]
            # If multiple matches, try to narrow down by postal code
            if csv_postal:
                postal_filtered = [m for m in matches
                                   if (m[0] == 'company' and str(m[1].get('post_code', '')) == csv_postal) or
                                      (m[0] == 'prospect' and str(m[1].get('postal_code', '')) == csv_postal)]
                if postal_filtered:
                    matches = postal_filtered

            if matches:
                match_type, matched_record = matches[0]
                exact_matches.append({
                    'csv_record': csv_record,
                    'match_type': 'exact_name',
                    'db_type': match_type,
                    'db_record': matched_record
                })
                match_found = True

        # 2. Try fuzzy matching (partial name + same postal code)
        if not match_found and csv_postal and csv_postal in db_postal_index:
            for db_type, db_record in db_postal_index[csv_postal]:
                db_name = normalize_name(
                    db_record.get('name') or db_record.get('public_name', '')
                )
                # Check if one name contains the other (partial match)
                if db_name and norm_csv_name:
                    if db_name in norm_csv_name or norm_csv_name in db_name:
                        fuzzy_matches.append({
                            'csv_record': csv_record,
                            'match_type': 'fuzzy_name_postal',
                            'db_type': db_type,
                            'db_record': db_record,
                            'similarity': 'partial'
                        })
                        match_found = True
                        break

        if not match_found:
            no_matches.append(csv_record)

    return exact_matches, fuzzy_matches, no_matches


def analyze_csv_columns(csv_records):
    """Analyze CSV columns to understand data distribution."""
    column_stats = {}

    if not csv_records:
        return column_stats

    columns = list(csv_records[0].keys())

    for col in columns:
        non_empty = [r[col] for r in csv_records if r.get(col) and r[col].strip()]
        column_stats[col] = {
            'total': len(csv_records),
            'filled': len(non_empty),
            'fill_rate': round(len(non_empty) / len(csv_records) * 100, 1),
            'sample_values': non_empty[:3] if non_empty else []
        }

    return column_stats


def generate_column_mapping():
    """Generate recommended column mapping from CSV to database."""

    # Current companies table columns (from our analysis)
    existing_columns = [
        'company_id', 'name', 'public_name', 'vat_number',
        'address_line1', 'address_line2', 'city', 'post_code', 'country_name',
        'latitude', 'longitude', 'geocoded_address',
        'email', 'phone_number', 'website',
        'contact_person_name', 'contact_person_email', 'contact_person_phone',
        'company_categories', 'addresses',
        'is_customer', 'is_supplier',
        'company_status_name', 'company_tag',
        'assigned_salesperson', 'lead_source',
        'total_revenue_2024', 'total_revenue_2025',
        'customer_since', 'last_activity_date',
        'notes', 'raw_company_data', 'data_sources'
    ]

    # CSV to DB mapping recommendations
    mapping = {
        'Name': 'public_name',  # CSV name -> public_name (display name)
        'Address': 'PARSE_TO: address_line1, city, post_code, country_name',
        'Account Number': 'external_account_number (NEW)',
        'Account Owner': 'SKIP (use assigned_salesperson)',
        'Activations': 'activations (NEW) - sales notes',
        'Channel': 'channel (NEW) - On-Trade/Off-Trade',
        'Company Owner': 'assigned_salesperson',
        'Language': 'language (NEW)',
        'Lead Status': 'lead_status (NEW) - Customer/To be contacted/Unqualified/etc',
        'Priority': 'priority (NEW) - High/Medium/Low',
        'Province / Region': 'province (NEW)',
        'Sub Type': 'sub_type (NEW) - Restaurant/Bar/Shop/etc',
        'Type (Yugen Website)': 'business_type (NEW)',
        'Parent Company': 'parent_company (NEW)',
        'Suppliers': 'suppliers (NEW) - JSONB array',
        'Coordinates': 'PARSE_TO: latitude, longitude',
        'Notes': 'notes (EXISTING or crm_notes NEW)',
        'Proposed': 'products_proposed (NEW) - JSONB',
        'Sampled': 'products_sampled (NEW) - JSONB',
        'Agreed': 'products_agreed (NEW) - JSONB',
        'Listed': 'products_listed (NEW) - JSONB',
        'Win': 'products_won (NEW) - JSONB',
        'De-Listed': 'products_delisted (NEW) - JSONB',
        'Lost': 'products_lost (NEW) - JSONB',
        'Unsuitable': 'products_unsuitable (NEW) - JSONB',
        'Menu Listing': 'menu_listing (NEW)',
        'FSDU': 'has_fsdu (NEW) - boolean',
        'Contact 1 Name': 'contact_person_name (EXISTING)',
        'Contact 1 Role': 'contact_person_role (NEW)',
        'Contact 1 Email': 'contact_person_email (EXISTING)',
        'Contact 1 Phone': 'contact_person_phone (EXISTING)',
        'Contact 2 Name': 'contact_2_name (NEW)',
        'Contact 2 Role': 'contact_2_role (NEW)',
        'Contact 2 Email': 'contact_2_email (NEW)',
        'Contact 2 Phone': 'contact_2_phone (NEW)',
        'Contact 3 Name': 'contact_3_name (NEW)',
        'Contact 3 Role': 'contact_3_role (NEW)',
        'Contact 3 Email': 'contact_3_email (NEW)',
        'Contact 3 Phone': 'contact_3_phone (NEW)',
    }

    return mapping, existing_columns


def main():
    print("=" * 70)
    print("CSV IMPORT ANALYSIS")
    print("=" * 70)

    # Load CSV data
    print("\n📊 Loading CSV data...")
    csv_path = '/Users/hendrikdewinne/MOTHERSHIP_PROSPECTING/2026-01-20_location_export.csv'
    csv_records = load_csv_data(csv_path)
    print(f"   Loaded {len(csv_records)} records from CSV")

    # Load existing database records
    print("\n📊 Loading existing database records...")
    db_companies = load_existing_companies()
    print(f"   Found {len(db_companies)} companies in database")

    db_prospects = load_existing_prospects()
    print(f"   Found {len(db_prospects)} prospects in database")

    # Find matches
    print("\n🔍 Analyzing overlaps...")
    exact_matches, fuzzy_matches, no_matches = find_matches(csv_records, db_companies, db_prospects)

    print(f"\n{'=' * 70}")
    print("MATCH RESULTS")
    print("=" * 70)
    print(f"   ✅ Exact matches:    {len(exact_matches)} ({round(len(exact_matches)/len(csv_records)*100, 1)}%)")
    print(f"   🔶 Fuzzy matches:    {len(fuzzy_matches)} ({round(len(fuzzy_matches)/len(csv_records)*100, 1)}%)")
    print(f"   ❌ No matches (NEW): {len(no_matches)} ({round(len(no_matches)/len(csv_records)*100, 1)}%)")

    # Show some exact match examples
    print(f"\n{'=' * 70}")
    print("SAMPLE EXACT MATCHES (first 10)")
    print("=" * 70)
    for match in exact_matches[:10]:
        csv_name = match['csv_record'].get('Name', '')
        csv_addr = match['csv_record'].get('Address', '')[:40]
        db_name = match['db_record'].get('name') or match['db_record'].get('public_name', '')
        db_type = match['db_type']
        print(f"   CSV: {csv_name[:30]:<30} | DB ({db_type}): {db_name[:30]}")

    # Show some fuzzy match examples
    if fuzzy_matches:
        print(f"\n{'=' * 70}")
        print("SAMPLE FUZZY MATCHES - REVIEW NEEDED (first 10)")
        print("=" * 70)
        for match in fuzzy_matches[:10]:
            csv_name = match['csv_record'].get('Name', '')
            db_name = match['db_record'].get('name') or match['db_record'].get('public_name', '')
            db_type = match['db_type']
            print(f"   CSV: {csv_name[:30]:<30} | DB ({db_type}): {db_name[:30]}")

    # Show some no-match examples
    print(f"\n{'=' * 70}")
    print("SAMPLE NEW RECORDS (first 20)")
    print("=" * 70)
    for record in no_matches[:20]:
        name = record.get('Name', '')
        addr = record.get('Address', '')[:50]
        status = record.get('Lead Status', '')
        print(f"   {name[:30]:<30} | {status:<15} | {addr}")

    # Analyze lead status distribution for new records
    print(f"\n{'=' * 70}")
    print("NEW RECORDS BY LEAD STATUS")
    print("=" * 70)
    status_counts = defaultdict(int)
    for record in no_matches:
        status = record.get('Lead Status', 'Unknown') or 'Unknown'
        status_counts[status] += 1

    for status, count in sorted(status_counts.items(), key=lambda x: -x[1]):
        print(f"   {status:<20}: {count:>4} records")

    # Column analysis
    print(f"\n{'=' * 70}")
    print("CSV COLUMN ANALYSIS")
    print("=" * 70)
    column_stats = analyze_csv_columns(csv_records)

    for col, stats in sorted(column_stats.items(), key=lambda x: -x[1]['fill_rate']):
        fill = stats['fill_rate']
        samples = ', '.join(str(s)[:20] for s in stats['sample_values'][:2])
        print(f"   {col:<25}: {fill:>5.1f}% filled | Examples: {samples}")

    # Column mapping recommendations
    print(f"\n{'=' * 70}")
    print("NEW COLUMNS NEEDED FOR COMPANIES TABLE")
    print("=" * 70)
    mapping, existing = generate_column_mapping()

    new_columns = []
    for csv_col, db_mapping in mapping.items():
        if '(NEW)' in db_mapping:
            # Extract column name and type
            col_info = db_mapping.replace('(NEW)', '').strip()
            new_columns.append((csv_col, col_info))

    for csv_col, col_info in new_columns:
        print(f"   {csv_col:<25} -> {col_info}")

    # Generate SQL for new columns
    print(f"\n{'=' * 70}")
    print("RECOMMENDED SQL FOR NEW COLUMNS")
    print("=" * 70)

    sql_statements = [
        "-- CRM import fields",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS external_account_number VARCHAR(50);",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS channel VARCHAR(20);  -- On-Trade, Off-Trade",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS language VARCHAR(10);",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS lead_status VARCHAR(30);  -- Customer, To be contacted, etc",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS priority VARCHAR(10);  -- High, Medium, Low",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS province VARCHAR(50);",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS sub_type VARCHAR(50);  -- Restaurant, Bar, Shop, etc",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS business_type VARCHAR(50);",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS parent_company VARCHAR(100);",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS suppliers JSONB DEFAULT '[]';",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS crm_notes TEXT;  -- Notes from old CRM",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS activations TEXT;  -- Sales activation notes",
        "",
        "-- Product tracking fields",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS products_proposed JSONB DEFAULT '[]';",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS products_sampled JSONB DEFAULT '[]';",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS products_agreed JSONB DEFAULT '[]';",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS products_listed JSONB DEFAULT '[]';",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS products_won JSONB DEFAULT '[]';",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS products_delisted JSONB DEFAULT '[]';",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS products_lost JSONB DEFAULT '[]';",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS products_unsuitable JSONB DEFAULT '[]';",
        "",
        "-- Display/marketing fields",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS menu_listing TEXT;",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS has_fsdu BOOLEAN DEFAULT FALSE;",
        "",
        "-- Additional contacts",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS contact_person_role VARCHAR(50);",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS contact_2_name VARCHAR(100);",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS contact_2_role VARCHAR(50);",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS contact_2_email VARCHAR(100);",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS contact_2_phone VARCHAR(30);",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS contact_3_name VARCHAR(100);",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS contact_3_role VARCHAR(50);",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS contact_3_email VARCHAR(100);",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS contact_3_phone VARCHAR(30);",
        "",
        "-- Data source tracking",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS imported_from_crm BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS crm_import_date TIMESTAMP;",
    ]

    for stmt in sql_statements:
        print(stmt)

    # Summary
    print(f"\n{'=' * 70}")
    print("SUMMARY & RECOMMENDATIONS")
    print("=" * 70)
    print(f"""
   TOTAL CSV RECORDS:     {len(csv_records)}

   OVERLAP ANALYSIS:
   - Exact matches:       {len(exact_matches)} (update existing records with new fields)
   - Fuzzy matches:       {len(fuzzy_matches)} (manual review needed)
   - New records:         {len(no_matches)} (will be inserted as new companies)

   RECOMMENDED APPROACH:
   1. Run the SQL above to add new columns to the companies table
   2. Create an import script that:
      a. For EXACT MATCHES: Update existing records with CSV data (preserve existing financial data)
      b. For FUZZY MATCHES: Export list for manual review before importing
      c. For NEW RECORDS: Insert as new companies (with is_customer=False initially)
   3. Use coordinates from CSV for geocoding where missing in DB
   4. Parse product lists (Proposed, Sampled, etc.) into JSONB arrays

   MATCHING STRATEGY USED:
   - Primary: Normalized name match (lowercase, remove suffixes, special chars)
   - Secondary: Name + postal code match for disambiguation
   - Fuzzy: Partial name match within same postal code
""")

    # Save detailed results to files
    print("\n📁 Saving detailed results to files...")

    # Save exact matches
    with open('/Users/hendrikdewinne/MOTHERSHIP_PROSPECTING/import_analysis_exact_matches.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(['CSV_Name', 'CSV_Address', 'CSV_Status', 'DB_Type', 'DB_Name', 'DB_ID'])
        for match in exact_matches:
            writer.writerow([
                match['csv_record'].get('Name', ''),
                match['csv_record'].get('Address', ''),
                match['csv_record'].get('Lead Status', ''),
                match['db_type'],
                match['db_record'].get('name') or match['db_record'].get('public_name', ''),
                match['db_record'].get('company_id') or match['db_record'].get('id', '')
            ])
    print(f"   ✅ Saved {len(exact_matches)} exact matches to import_analysis_exact_matches.csv")

    # Save fuzzy matches
    with open('/Users/hendrikdewinne/MOTHERSHIP_PROSPECTING/import_analysis_fuzzy_matches.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(['CSV_Name', 'CSV_Address', 'CSV_Status', 'DB_Type', 'DB_Name', 'DB_ID', 'REVIEW_ACTION'])
        for match in fuzzy_matches:
            writer.writerow([
                match['csv_record'].get('Name', ''),
                match['csv_record'].get('Address', ''),
                match['csv_record'].get('Lead Status', ''),
                match['db_type'],
                match['db_record'].get('name') or match['db_record'].get('public_name', ''),
                match['db_record'].get('company_id') or match['db_record'].get('id', ''),
                'REVIEW_NEEDED'
            ])
    print(f"   ✅ Saved {len(fuzzy_matches)} fuzzy matches to import_analysis_fuzzy_matches.csv")

    # Save new records
    with open('/Users/hendrikdewinne/MOTHERSHIP_PROSPECTING/import_analysis_new_records.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=';')
        # Write header (all CSV columns)
        if no_matches:
            writer.writerow(list(no_matches[0].keys()))
            for record in no_matches:
                writer.writerow(list(record.values()))
    print(f"   ✅ Saved {len(no_matches)} new records to import_analysis_new_records.csv")

    print("\n✅ Analysis complete!")


if __name__ == "__main__":
    main()
