"""Check the current database state after rollback"""
from supabase import create_client

SUPABASE_URL = "https://gpjoypslbrpvnhqzvacc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imdwam95cHNsYnJwdm5ocXp2YWNjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTM3MDQxNTAsImV4cCI6MjA2OTI4MDE1MH0.u0hGzIKziSPz2i576NhuyCetV6_iQwCoft7FIjDJCiI"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Count total companies
result = supabase.table('companies').select('id', count='exact').execute()
print(f"Total companies in DB: {result.count}")

# Count companies still marked as CRM imported
result2 = supabase.table('companies').select('id', count='exact').eq('imported_from_crm', True).execute()
print(f"Companies still marked as CRM imported: {result2.count}")

# Get company IDs from invoices (2024, 2025, 2026)
invoice_company_ids = set()
for year in ['2024', '2025', '2026']:
    try:
        result = supabase.table(f'sales_{year}').select('company_id').execute()
        for r in result.data:
            if r.get('company_id'):
                invoice_company_ids.add(r['company_id'])
    except Exception as e:
        print(f"Error fetching {year}: {e}")

print(f"Unique company IDs in invoices: {len(invoice_company_ids)}")

# Check how many companies have no invoices
all_companies = []
offset = 0
while True:
    result = supabase.table('companies').select('company_id, name').range(offset, offset + 999).execute()
    if not result.data:
        break
    all_companies.extend(result.data)
    if len(result.data) < 1000:
        break
    offset += 1000

companies_without_invoices = [c for c in all_companies if c['company_id'] not in invoice_company_ids]
print(f"Companies WITHOUT invoices: {len(companies_without_invoices)}")

if companies_without_invoices:
    print("\nSample companies without invoices (first 20):")
    for c in companies_without_invoices[:20]:
        print(f"  - {c['name']} (ID: {c['company_id']})")
