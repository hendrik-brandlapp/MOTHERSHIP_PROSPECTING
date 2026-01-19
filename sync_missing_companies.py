"""
Sync Missing Companies Script

This script finds companies in invoices that are missing from the companies table
and syncs them from the Duano API using OAuth user authentication.

Run with: python3 sync_missing_companies.py
"""

import time
import requests
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from supabase import create_client

# Configuration
SUPABASE_URL = "https://gpjoypslbrpvnhqzvacc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imdwam95cHNsYnJwdm5ocXp2YWNjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTM3MDQxNTAsImV4cCI6MjA2OTI4MDE1MH0.u0hGzIKziSPz2i576NhuyCetV6_iQwCoft7FIjDJCiI"

DUANO_CLIENT_ID = "3"
DUANO_CLIENT_SECRET = "KBPJZ11EwPjAmEUKFWDoXGQaDdMRPFES2P6VCxEC"
DUANO_BASE_URL = "https://yugen.douano.com"
LOCAL_REDIRECT_URI = "http://localhost:5050/oauth/callback"

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Global to store the OAuth code
oauth_code = None


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handle OAuth callback"""

    def do_GET(self):
        global oauth_code
        parsed = urlparse(self.path)

        if parsed.path == '/oauth/callback':
            query = parse_qs(parsed.query)
            if 'code' in query:
                oauth_code = query['code'][0]
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'''
                    <html><body style="font-family: sans-serif; text-align: center; padding: 50px;">
                    <h1>Authentication Successful!</h1>
                    <p>You can close this window and return to the terminal.</p>
                    </body></html>
                ''')
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'No code received')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress logging


def get_oauth_token():
    """Get OAuth token via authorization code flow"""
    global oauth_code

    print("\n🔐 Starting OAuth authentication...")
    print("   A browser window will open for you to log in to Duano.")

    # Build authorization URL
    auth_url = (
        f"{DUANO_BASE_URL}/oauth/authorize?"
        f"client_id={DUANO_CLIENT_ID}&"
        f"redirect_uri={LOCAL_REDIRECT_URI}&"
        f"response_type=code&"
        f"scope=*"
    )

    # Start local server to receive callback
    server = HTTPServer(('localhost', 5050), OAuthCallbackHandler)
    server.timeout = 120  # 2 minute timeout

    # Open browser
    print(f"\n   Opening: {auth_url}\n")
    webbrowser.open(auth_url)

    print("   Waiting for authentication...")

    # Wait for callback
    while oauth_code is None:
        server.handle_request()

    server.server_close()

    print("   ✅ Received authorization code")

    # Exchange code for token
    token_url = f"{DUANO_BASE_URL}/oauth/token"
    token_data = {
        'grant_type': 'authorization_code',
        'client_id': DUANO_CLIENT_ID,
        'client_secret': DUANO_CLIENT_SECRET,
        'redirect_uri': LOCAL_REDIRECT_URI,
        'code': oauth_code
    }

    response = requests.post(token_url, data=token_data, timeout=30)

    if response.status_code == 200:
        token_info = response.json()
        print("   ✅ Got access token")
        return token_info.get('access_token')
    else:
        raise Exception(f"Failed to get token: {response.status_code} - {response.text}")


def get_company_ids_from_year(year):
    """Get all unique company IDs from invoices for a given year"""
    company_ids = set()
    batch_size = 1000
    offset = 0

    while True:
        try:
            result = supabase.table(f'sales_{year}').select('company_id').range(offset, offset + batch_size - 1).execute()

            if not result.data:
                break

            for record in result.data:
                if record.get('company_id'):
                    company_ids.add(record['company_id'])

            if len(result.data) < batch_size:
                break

            offset += batch_size

            if offset > 50000:
                break
        except Exception as e:
            print(f"Error fetching {year} company IDs at offset {offset}: {e}")
            break

    return company_ids


def fetch_company_from_duano(company_id, headers):
    """Fetch a single company from Duano API with retry logic"""
    max_retries = 3

    for retry in range(max_retries):
        try:
            # Try CORE endpoint
            url = f"{DUANO_BASE_URL}/api/public/v1/core/companies/{company_id}"
            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 200:
                return response.json().get('result', {}), None
            elif response.status_code == 429:
                wait_time = min(5 * (retry + 1), 30)
                print(f"  Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                return None, f"API Error: {response.status_code}"

        except requests.exceptions.Timeout:
            if retry < max_retries - 1:
                time.sleep(2)
                continue
            return None, "Request timeout"
        except Exception as e:
            return None, str(e)

    return None, "Max retries exceeded"


def main():
    print("=" * 60)
    print("🔍 SYNC MISSING COMPANIES (OAuth)")
    print("=" * 60)

    # Step 1: Find missing companies
    print("\n📊 Step 1: Finding companies in invoices...")

    invoice_company_ids = set()
    for year in ['2024', '2025', '2026']:
        year_ids = get_company_ids_from_year(year)
        print(f"  {year}: {len(year_ids)} unique companies")
        invoice_company_ids.update(year_ids)

    print(f"  Total unique companies in invoices: {len(invoice_company_ids)}")

    # Step 2: Get existing companies
    print("\n📊 Step 2: Checking companies table...")
    existing_result = supabase.table('companies').select('company_id').execute()
    existing_company_ids = set(c['company_id'] for c in existing_result.data)
    print(f"  Companies already in database: {len(existing_company_ids)}")

    # Step 3: Find missing
    missing_company_ids = invoice_company_ids - existing_company_ids
    print(f"\n🎯 Missing companies to sync: {len(missing_company_ids)}")

    if not missing_company_ids:
        print("\n✅ All companies are already synced!")
        return

    # Step 4: Get OAuth token (user login)
    try:
        access_token = get_oauth_token()
    except Exception as e:
        print(f"\n❌ OAuth failed: {e}")
        return

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    # Step 5: Test API access
    print("\n🧪 Testing API access...")
    test_url = f"{DUANO_BASE_URL}/api/public/v1/core/companies/{list(existing_company_ids)[0]}"
    test_resp = requests.get(test_url, headers=headers, timeout=15)
    if test_resp.status_code != 200:
        print(f"❌ API test failed: {test_resp.status_code}")
        print(f"   Response: {test_resp.text[:200]}")
        return
    print("✅ API access confirmed!")

    # Step 6: Ask to proceed
    print(f"\n⚠️  Ready to sync {len(missing_company_ids)} companies")
    response = input("Proceed? (y/n): ").strip().lower()

    if response != 'y':
        print("Aborted.")
        return

    # Step 7: Sync from Duano API
    print("\n🚀 Syncing companies from Duano API...")

    synced_count = 0
    error_count = 0
    errors = []

    for i, company_id in enumerate(missing_company_ids):
        print(f"\n[{i+1}/{len(missing_company_ids)}] Fetching company {company_id}...")

        # Rate limiting
        if i > 0 and i % 10 == 0:
            print(f"  Rate limiting: waiting 2 seconds...")
            time.sleep(2)
        elif i > 0:
            time.sleep(0.3)

        company_data, error = fetch_company_from_duano(company_id, headers)

        if error:
            print(f"  ❌ Error: {error}")
            error_count += 1
            errors.append({'id': company_id, 'error': error})
            continue

        if not company_data:
            print(f"  ❌ No data returned")
            error_count += 1
            errors.append({'id': company_id, 'error': 'No data'})
            continue

        # Build record
        record = {
            'company_id': company_id,
            'name': company_data.get('name'),
            'public_name': company_data.get('public_name'),
            'company_tag': company_data.get('tag'),
            'vat_number': company_data.get('vat_number'),
            'is_customer': company_data.get('is_customer', False),
            'is_supplier': company_data.get('is_supplier', False),
            'company_status_id': company_data.get('company_status', {}).get('id') if company_data.get('company_status') else None,
            'company_status_name': company_data.get('company_status', {}).get('name') if company_data.get('company_status') else None,
            'sales_price_class_id': company_data.get('sales_price_class', {}).get('id') if company_data.get('sales_price_class') else None,
            'sales_price_class_name': company_data.get('sales_price_class', {}).get('name') if company_data.get('sales_price_class') else None,
            'document_delivery_type': company_data.get('document_delivery_type'),
            'email_addresses': company_data.get('email_addresses'),
            'default_document_notes': company_data.get('default_document_notes', []),
            'company_categories': company_data.get('company_categories', []),
            'addresses': company_data.get('addresses', []),
            'bank_accounts': company_data.get('bank_accounts', []),
            'extension_values': company_data.get('extension_values', []),
            'raw_company_data': company_data,
            'data_sources': ['douano_api', 'invoices'],
            'last_sync_at': datetime.now().isoformat()
        }

        # Insert into Supabase
        try:
            supabase.table('companies').insert(record).execute()
            categories = company_data.get('company_categories', [])
            cat_names = [c.get('name', c) for c in categories] if categories else []
            print(f"  ✅ Synced: {company_data.get('name')} | Categories: {cat_names}")
            synced_count += 1
        except Exception as e:
            print(f"  ❌ DB Error: {e}")
            error_count += 1
            errors.append({'id': company_id, 'error': str(e)})

    # Summary
    print("\n" + "=" * 60)
    print("📊 SYNC COMPLETE")
    print("=" * 60)
    print(f"  ✅ Synced: {synced_count}")
    print(f"  ❌ Errors: {error_count}")

    if errors:
        print(f"\n  Failed companies:")
        for err in errors[:20]:
            print(f"    - {err['id']}: {err['error'][:50]}")


if __name__ == "__main__":
    main()
