#!/usr/bin/env python3
"""
Sync Company Categories Script

This script syncs company_categories from Duano API to fix companies that are missing categories.
It will:
1. Find all companies in Supabase that have empty/null company_categories
2. Fetch their details from Duano API
3. Update the company_categories field in Supabase

Run with: python3 sync_company_categories.py
"""

import os
import sys
import time
import requests
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

# Configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_KEY')

DUANO_CLIENT_ID = os.getenv('DUANO_CLIENT_ID', '3')
DUANO_CLIENT_SECRET = os.getenv('DUANO_CLIENT_SECRET', 'KBPJZ11EwPjAmEUKFWDoXGQaDdMRPFES2P6VCxEC')
DUANO_BASE_URL = os.getenv('DOUANO_BASE_URL', 'https://yugen.douano.com')
LOCAL_REDIRECT_URI = "http://localhost:5051/oauth/callback"

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: Missing SUPABASE_URL or SUPABASE_KEY in environment")
    sys.exit(1)

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
    oauth_code = None  # Reset

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
    server = HTTPServer(('localhost', 5051), OAuthCallbackHandler)
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


def fetch_company_from_duano(company_id, headers):
    """Fetch a single company from Duano API with retry logic"""
    max_retries = 3

    for retry in range(max_retries):
        try:
            # Use the CRM companies endpoint which includes company_categories
            url = f"{DUANO_BASE_URL}/api/public/v1/crm/crm-companies/{company_id}"
            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 200:
                return response.json().get('result', {}), None
            elif response.status_code == 404:
                # Try the core endpoint as fallback
                url = f"{DUANO_BASE_URL}/api/public/v1/core/companies/{company_id}"
                response = requests.get(url, headers=headers, timeout=30)
                if response.status_code == 200:
                    return response.json().get('result', {}), None
                return None, f"Company not found (404)"
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


def get_companies_without_categories():
    """Get all companies from Supabase that have empty/null company_categories"""
    companies = []
    batch_size = 1000
    offset = 0

    print("\n📊 Finding companies without categories...")

    while True:
        try:
            # Fetch companies where company_categories is null or empty
            result = supabase.table('companies').select(
                'id, company_id, name, public_name, company_categories, raw_company_data'
            ).range(offset, offset + batch_size - 1).execute()

            if not result.data:
                break

            for company in result.data:
                categories = company.get('company_categories')
                raw_data = company.get('raw_company_data') or {}
                raw_categories = raw_data.get('company_categories') if raw_data else None

                # Check if categories are missing from both direct field and raw_company_data
                has_direct_categories = categories and isinstance(categories, list) and len(categories) > 0
                has_raw_categories = raw_categories and isinstance(raw_categories, list) and len(raw_categories) > 0

                if not has_direct_categories and not has_raw_categories:
                    companies.append(company)

            if len(result.data) < batch_size:
                break

            offset += batch_size

        except Exception as e:
            print(f"Error fetching companies: {e}")
            break

    return companies


def main():
    print("=" * 70)
    print("🏷️  SYNC COMPANY CATEGORIES FROM DUANO")
    print("=" * 70)

    # Step 1: Find companies without categories
    companies_without_cats = get_companies_without_categories()
    print(f"   Found {len(companies_without_cats)} companies without categories")

    if not companies_without_cats:
        print("\n✅ All companies already have categories!")
        return

    # Step 2: Get OAuth token
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

    # Step 3: Test API access
    print("\n🧪 Testing API access...")
    test_company = companies_without_cats[0]
    test_data, test_error = fetch_company_from_duano(test_company['company_id'], headers)
    if test_error:
        print(f"❌ API test failed: {test_error}")
        return
    print(f"✅ API access confirmed! Test company categories: {test_data.get('company_categories', [])}")

    # Step 4: Ask to proceed
    print(f"\n⚠️  Ready to sync categories for {len(companies_without_cats)} companies")
    response = input("Proceed? (y/n): ").strip().lower()

    if response != 'y':
        print("Aborted.")
        return

    # Step 5: Sync categories
    print("\n🚀 Syncing categories from Duano API...")

    synced_count = 0
    no_category_count = 0
    error_count = 0
    errors = []

    for i, company in enumerate(companies_without_cats):
        company_id = company['company_id']
        company_name = company.get('public_name') or company.get('name') or f"ID:{company_id}"

        # Rate limiting
        if i > 0 and i % 10 == 0:
            print(f"\n  Progress: {i}/{len(companies_without_cats)} ({synced_count} synced, {no_category_count} no categories, {error_count} errors)")
            time.sleep(1)
        elif i > 0:
            time.sleep(0.2)

        # Fetch from Duano
        company_data, error = fetch_company_from_duano(company_id, headers)

        if error:
            print(f"  ❌ {company_name}: {error}")
            error_count += 1
            errors.append({'id': company_id, 'name': company_name, 'error': error})
            continue

        if not company_data:
            print(f"  ❌ {company_name}: No data returned")
            error_count += 1
            errors.append({'id': company_id, 'name': company_name, 'error': 'No data'})
            continue

        # Get categories from Duano
        categories = company_data.get('company_categories', [])

        if not categories or len(categories) == 0:
            print(f"  ⚪ {company_name}: No categories in Duano either")
            no_category_count += 1
            continue

        # Extract category names for logging
        cat_names = [c.get('name', str(c)) if isinstance(c, dict) else str(c) for c in categories]

        # Update Supabase
        try:
            update_data = {
                'company_categories': categories,
                'raw_company_data': company_data,
                'last_sync_at': datetime.now().isoformat()
            }

            supabase.table('companies').update(update_data).eq('company_id', company_id).execute()
            print(f"  ✅ {company_name}: {cat_names}")
            synced_count += 1

        except Exception as e:
            print(f"  ❌ {company_name}: DB Error - {e}")
            error_count += 1
            errors.append({'id': company_id, 'name': company_name, 'error': str(e)})

    # Summary
    print("\n" + "=" * 70)
    print("📊 SYNC COMPLETE")
    print("=" * 70)
    print(f"  Total companies processed: {len(companies_without_cats)}")
    print(f"  ✅ Synced with categories: {synced_count}")
    print(f"  ⚪ No categories in Duano: {no_category_count}")
    print(f"  ❌ Errors: {error_count}")

    if errors:
        print(f"\n  First 20 failed companies:")
        for err in errors[:20]:
            print(f"    - {err['name']} (ID: {err['id']}): {err['error'][:50]}")

    print("\nDone!")


if __name__ == "__main__":
    main()
