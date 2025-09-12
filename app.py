"""
DOUANO Frontend - Flask Web Application
Beautiful interface to interact with your DOUANO data
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import requests
import urllib.parse
import secrets
import os
from datetime import datetime, timedelta
import json
from dotenv import load_dotenv

try:
    # Prefer the modern OpenAI client; handle absence gracefully
    from openai import OpenAI
except Exception:
    OpenAI = None

try:
    from supabase import create_client, Client
except Exception:
    create_client = None
    Client = None

load_dotenv()

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# External API keys/config
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY', '')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
openai_client = None
if OPENAI_API_KEY and OpenAI is not None:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception:
        openai_client = None

# Supabase configuration
SUPABASE_URL = "https://gpjoypslbrpvnhqzvacc.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imdwam95cHNsYnJwdm5ocXp2YWNjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTM3MDQxNTAsImV4cCI6MjA2OTI4MDE1MH0.u0hGzIKziSPz2i576NhuyCetV6_iQwCoft7FIjDJCiI"
supabase_client = None
if create_client and Client:
    try:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    except Exception:
        supabase_client = None

# DOUANO API Configuration
DOUANO_CONFIG = {
    'client_id': '3',
    'client_secret': 'KBPJZ11EwPjAmEUKFWDoXGQaDdMRPFES2P6VCxEC',
    'base_url': 'https://yugen.douano.com',
    'auth_url': 'https://yugen.douano.com/authorize',
    'token_url': 'https://yugen.douano.com/oauth/token',
    'redirect_uri': 'http://localhost:5002/oauth/callback'
}


def is_token_valid():
    """Check if the stored token is valid"""
    if 'access_token' not in session:
        return False
    
    if 'token_expires_at' not in session:
        return False
    
    expires_at = datetime.fromisoformat(session['token_expires_at'])
    return datetime.now() < expires_at - timedelta(minutes=5)


def make_api_request(endpoint, method='GET', params=None):
    """Make authenticated API request to DOUANO"""
    if not is_token_valid():
        return None, "Token expired or invalid"
    
    headers = {
        'Authorization': f"Bearer {session['access_token']}",
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    url = f"{DOUANO_CONFIG['base_url']}{endpoint}"
    
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, params=params, timeout=15)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=params, timeout=15)
        else:
            return None, f"Unsupported method: {method}"
        
        if response.status_code == 200:
            return response.json(), None
        else:
            return None, f"API Error: {response.status_code} - {response.text[:200]}"
            
    except Exception as e:
        return None, f"Request failed: {str(e)}"


def _extract_belgian_vat_numbers(text: str):
    """Extract Belgian VAT numbers from arbitrary text using regex heuristics.

    Accepts formats like 'BE 0123.456.789', 'BTW BE0123456789', 'VAT: BE-0123456789', etc.
    Returns list of normalized VAT numbers in the form 'BE0123456789'.
    """
    import re
    if not text:
        return []
    candidates = set()
    # Common keywords around VAT in NL/FR/EN
    patterns = [
        r"(?:BE\s*[-.]?\s*0?\s*\d[\d .-]{7,14}\d)",
        r"(?:BTW\s*[:]?\s*BE\s*[-.]?\s*0?\s*\d[\d .-]{7,14}\d)",
        r"(?:TVA\s*[:]?\s*BE\s*[-.]?\s*0?\s*\d[\d .-]{7,14}\d)",
        r"(?:VAT\s*[:]?\s*BE\s*[-.]?\s*0?\s*\d[\d .-]{7,14}\d)",
    ]
    for pat in patterns:
        for m in re.findall(pat, text, flags=re.IGNORECASE):
            digits = ''.join(ch for ch in m if ch.isdigit())
            if digits.startswith('0') and len(digits) == 10:
                normalized = f"BE{digits}"
                candidates.add(normalized)
            elif len(digits) == 9:
                # Sometimes missing the leading 0
                normalized = f"BE0{digits}"
                candidates.add(normalized)
            elif len(digits) == 10:
                normalized = f"BE{digits}"
                candidates.add(normalized)
    return list(candidates)


def _fetch_text_from_url(url: str) -> str:
    """Fetch text content from a URL, returning best-effort decoded text."""
    if not url:
        return ''
    try:
        # Ensure scheme
        if not url.startswith('http'):
            url = 'https://' + url
        
        # Use better headers to avoid being blocked
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        resp = requests.get(url, timeout=15, headers=headers)
        if resp.status_code == 200:
            return resp.text or ''
        return ''
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return ''


def _extract_emails_and_phones(text: str):
    """Lightweight regex extraction for emails and phone numbers from free text."""
    import re
    emails = []
    phones = []
    if text:
        emails = sorted(set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)))
        # Very loose phone matching with + and spaces
        raw_phones = re.findall(r"(?:\+\d{1,3}[\s-]?)?(?:\d[\s-]?){7,12}", text)
        # Normalize: collapse spaces/dashes
        for p in raw_phones:
            digits = ''.join(ch for ch in p if ch.isdigit() or ch == '+')
            if len(digits) >= 8:
                phones.append(digits)
        phones = sorted(set(phones))
    return emails, phones


def make_paginated_api_request(endpoint, params=None):
    """Make API request and fetch all pages if paginated"""
    if params is None:
        params = {}
    
    # Set initial pagination
    params['per_page'] = 100
    params['page'] = 1
    
    all_data = []
    current_page = 1
    
    while True:
        params['page'] = current_page
        data, error = make_api_request(endpoint, params=params)
        
        if error:
            return None, error
        
        # Check if data has pagination structure
        if isinstance(data, dict) and 'result' in data:
            result = data['result']
            if isinstance(result, dict) and 'data' in result:
                # Paginated response
                page_data = result['data']
                all_data.extend(page_data)
                
                # Check if there are more pages
                current_page_num = result.get('current_page', 1)
                last_page = result.get('last_page', 1)
                
                if current_page_num >= last_page:
                    break
                    
                current_page += 1
            else:
                # Non-paginated response with result wrapper
                return data, None
        else:
            # Direct data response
            return data, None
    
    # Return all collected data in the same format
    final_result = {
        'result': {
            'data': all_data,
            'total': len(all_data),
            'current_page': 1,
            'last_page': 1,
            'per_page': len(all_data)
        }
    }
    
    return final_result, None


@app.route('/')
def index():
    """Home page"""
    if not is_token_valid():
        return render_template('login.html')
    # Serve a clean, simplified overview page
    return render_template('home.html')


@app.route('/login')
def login():
    """Initiate OAuth2 login"""
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state
    
    params = {
        'response_type': 'code',
        'client_id': DOUANO_CONFIG['client_id'],
        'redirect_uri': DOUANO_CONFIG['redirect_uri'],
        'scope': 'read write',
        'state': state
    }
    
    auth_url = f"{DOUANO_CONFIG['auth_url']}?" + urllib.parse.urlencode(params)
    return redirect(auth_url)


@app.route('/oauth/callback')
def oauth_callback():
    """Handle OAuth2 callback"""
    # Check for errors
    if 'error' in request.args:
        flash(f"Login failed: {request.args.get('error_description', 'Unknown error')}", 'error')
        return redirect(url_for('index'))
    
    # Verify state parameter
    if request.args.get('state') != session.get('oauth_state'):
        flash("Invalid state parameter", 'error')
        return redirect(url_for('index'))
    
    # Get authorization code
    auth_code = request.args.get('code')
    if not auth_code:
        flash("No authorization code received", 'error')
        return redirect(url_for('index'))
    
    # Exchange code for token
    token_data = {
        'grant_type': 'authorization_code',
        'client_id': DOUANO_CONFIG['client_id'],
        'client_secret': DOUANO_CONFIG['client_secret'],
        'code': auth_code,
        'redirect_uri': DOUANO_CONFIG['redirect_uri']
    }
    
    try:
        response = requests.post(DOUANO_CONFIG['token_url'], data=token_data, timeout=30)
        
        if response.status_code == 200:
            token_info = response.json()
            
            # Store token in session
            session['access_token'] = token_info['access_token']
            session['token_type'] = token_info.get('token_type', 'Bearer')
            session['duano_base_url'] = DOUANO_CONFIG['base_url']
            
            # Calculate expiration time
            expires_in = token_info.get('expires_in', 3600)
            expires_at = datetime.now() + timedelta(seconds=expires_in)
            session['token_expires_at'] = expires_at.isoformat()
            
            flash("Successfully logged in!", 'success')
            return redirect(url_for('dashboard'))
        else:
            flash(f"Token exchange failed: {response.status_code}", 'error')
            return redirect(url_for('index'))
            
    except Exception as e:
        flash(f"Login error: {str(e)}", 'error')
        return redirect(url_for('index'))


@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    flash("Successfully logged out", 'info')
    return redirect(url_for('index'))


@app.route('/dashboard')
def dashboard():
    """Deprecated: redirect to simplified home"""
    if not is_token_valid():
        return redirect(url_for('index'))
    return redirect(url_for('index'))


@app.route('/api/company-categories')
def api_company_categories():
    """Get company categories"""
    if not is_token_valid():
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Add pagination parameters to get all results
    params = {
        'per_page': 100,  # Request up to 100 items per page
        'page': 1
    }
    
    # Get query parameters for filtering and ordering
    if request.args.get('filter_by_created_since'):
        params['filter_by_created_since'] = request.args.get('filter_by_created_since')
    if request.args.get('filter_by_updated_since'):
        params['filter_by_updated_since'] = request.args.get('filter_by_updated_since')
    if request.args.get('filter_by_is_active'):
        params['filter_by_is_active'] = request.args.get('filter_by_is_active')
    if request.args.get('filter'):
        params['filter'] = request.args.get('filter')
    
    # Order parameters
    if request.args.get('order_by_name'):
        params['order_by_name'] = request.args.get('order_by_name')
    
    data, error = make_paginated_api_request('/api/public/v1/core/company-categories', params=params)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify(data)


@app.route('/api/crm-contacts')
def api_crm_contacts():
    """Get CRM contact persons"""
    if not is_token_valid():
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Add pagination parameters to get all results
    params = {
        'per_page': 100,  # Request up to 100 items per page
        'page': 1
    }
    
    # Get query parameters for filtering and ordering
    if request.args.get('order_by_name'):
        params['order_by_name'] = request.args.get('order_by_name')
    if request.args.get('order_by_company'):
        params['order_by_company'] = request.args.get('order_by_company')
    if request.args.get('filter_by_is_active'):
        params['filter_by_is_active'] = request.args.get('filter_by_is_active')
    
    data, error = make_paginated_api_request('/api/public/v1/crm/crm-contact-persons', params=params)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify(data)


@app.route('/api/crm-actions')
def api_crm_actions():
    """Get CRM actions"""
    if not is_token_valid():
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Add pagination parameters to get all results
    params = {
        'per_page': 100,  # Request up to 100 items per page
        'page': 1
    }
    
    data, error = make_api_request('/api/public/v1/crm/crm-actions', params=params)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify(data)


@app.route('/api/company-statuses')
def api_company_statuses():
    """Get company statuses"""
    if not is_token_valid():
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get query parameters for filtering and ordering
    params = {}
    
    # Filter parameters
    if request.args.get('filter_by_created_since'):
        params['filter_by_created_since'] = request.args.get('filter_by_created_since')
    if request.args.get('filter_by_updated_since'):
        params['filter_by_updated_since'] = request.args.get('filter_by_updated_since')
    if request.args.get('filter_by_is_active'):
        params['filter_by_is_active'] = request.args.get('filter_by_is_active')
    if request.args.get('filter'):
        params['filter'] = request.args.get('filter')
    
    # Order parameters
    if request.args.get('order_by_name'):
        params['order_by_name'] = request.args.get('order_by_name')
    if request.args.get('order_by_is_default'):
        params['order_by_is_default'] = request.args.get('order_by_is_default')
    if request.args.get('order_by_description'):
        params['order_by_description'] = request.args.get('order_by_description')
    
    # Add pagination parameters to get all results
    params['per_page'] = 100
    params['page'] = 1
    
    data, error = make_api_request('/api/public/v1/core/company-statuses', params=params)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify(data)


@app.route('/api/company-statuses/<int:status_id>')
def api_company_status(status_id):
    """Get specific company status"""
    if not is_token_valid():
        return jsonify({'error': 'Not authenticated'}), 401
    
    data, error = make_api_request(f'/api/public/v1/core/company-statuses/{status_id}')
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify(data)


@app.route('/api/accountancy/accounts')
def api_accountancy_accounts():
    """Get accountancy accounts"""
    if not is_token_valid():
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get query parameters for filtering and ordering
    params = {}
    
    # Order parameters
    order_fields = ['number', 'description', 'is_visible', 'type', 'sort', 'account_group', 'account_class']
    for field in order_fields:
        if request.args.get(f'order_by_{field}'):
            params[f'order_by_{field}'] = request.args.get(f'order_by_{field}')
    
    # Filter parameters
    filter_fields = ['is_visible', 'type', 'sort', 'allow_matching']
    for field in filter_fields:
        if request.args.get(f'filter_by_{field}'):
            params[f'filter_by_{field}'] = request.args.get(f'filter_by_{field}')
    
    # Add pagination parameters to get all results
    params['per_page'] = 100
    params['page'] = 1
    
    data, error = make_api_request('/api/public/v1/accountancy/accounts', params=params)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify(data)


@app.route('/api/accountancy/accounts/<int:account_id>')
def api_accountancy_account(account_id):
    """Get specific accountancy account"""
    if not is_token_valid():
        return jsonify({'error': 'Not authenticated'}), 401
    
    data, error = make_api_request(f'/api/public/v1/accountancy/accounts/{account_id}')
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify(data)


@app.route('/api/accountancy/bookings')
def api_accountancy_bookings():
    """Get accountancy bookings with extensive filtering"""
    if not is_token_valid():
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Add pagination parameters to get all results
    params = {
        'per_page': 100,  # Request up to 100 items per page
        'page': 1
    }
    
    # Get query parameters for ordering
    if request.args.get('order_by_date'):
        params['order_by_date'] = request.args.get('order_by_date')
    if request.args.get('order_by_journal'):
        params['order_by_journal'] = request.args.get('order_by_journal')
    if request.args.get('order_by_account'):
        params['order_by_account'] = request.args.get('order_by_account')
    if request.args.get('order_by_book_number'):
        params['order_by_book_number'] = request.args.get('order_by_book_number')
    if request.args.get('order_by_booking_type'):
        params['order_by_booking_type'] = request.args.get('order_by_booking_type')
    
    # Get query parameters for filtering
    if request.args.get('filter_by_start_date'):
        params['filter_by_start_date'] = request.args.get('filter_by_start_date')
    if request.args.get('filter_by_end_date'):
        params['filter_by_end_date'] = request.args.get('filter_by_end_date')
    if request.args.get('filter_by_journal'):
        params['filter_by_journal'] = request.args.get('filter_by_journal')
    if request.args.get('filter_by_account'):
        params['filter_by_account'] = request.args.get('filter_by_account')
    if request.args.get('filter_by_book_number'):
        params['filter_by_book_number'] = request.args.get('filter_by_book_number')
    if request.args.get('filter_by_cost_center'):
        params['filter_by_cost_center'] = request.args.get('filter_by_cost_center')
    if request.args.get('filter_by_cost_unit'):
        params['filter_by_cost_unit'] = request.args.get('filter_by_cost_unit')
    if request.args.get('filter_by_company'):
        params['filter_by_company'] = request.args.get('filter_by_company')
    if request.args.get('filter_by_product'):
        params['filter_by_product'] = request.args.get('filter_by_product')
    if request.args.get('filter_by_stock_location'):
        params['filter_by_stock_location'] = request.args.get('filter_by_stock_location')
    if request.args.get('filter_by_booking_type'):
        params['filter_by_booking_type'] = request.args.get('filter_by_booking_type')
    if request.args.get('filter_by_transaction'):
        params['filter_by_transaction'] = request.args.get('filter_by_transaction')
    if request.args.get('filter_by_updated_since'):
        params['filter_by_updated_since'] = request.args.get('filter_by_updated_since')
    if request.args.get('filter_by_created_since'):
        params['filter_by_created_since'] = request.args.get('filter_by_created_since')
    
    data, error = make_paginated_api_request('/api/public/v1/accountancy/bookings', params=params)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify(data)


@app.route('/api/accountancy/bookings/<int:booking_id>')
def api_accountancy_booking(booking_id):
    """Get specific accountancy booking"""
    if not is_token_valid():
        return jsonify({'error': 'Not authenticated'}), 401
    
    data, error = make_api_request(f'/api/public/v1/accountancy/bookings/{booking_id}')
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify(data)


@app.route('/api/companies')
def api_companies():
    """Get all companies (actual companies, not categories)"""
    if not is_token_valid():
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get query parameters for filtering and ordering
    params = {
        'per_page': request.args.get('per_page', 100),
        'page': request.args.get('page', 1)
    }
    
    # Filter parameters
    filter_params = [
        'filter_by_created_since', 'filter_by_updated_since', 'filter_by_is_customer',
        'filter_by_is_supplier', 'filter_by_is_active', 'filter_by_vat_number',
        'filter_by_iban', 'filter_by_company_categories[]', 'filter_by_sales_price_class',
        'filter_by_company_status', 'filter_by_country', 'filter_by_city', 'filter'
    ]
    
    for param in filter_params:
        if request.args.get(param):
            params[param] = request.args.get(param)
    
    # Lightweight search support for typeahead
    search_q = request.args.get('q')
    if search_q:
        params['filter'] = search_q
        params['per_page'] = request.args.get('per_page', 50)
        data, error = make_paginated_api_request('/api/public/v1/core/companies', params=params)
        if error:
            return jsonify({'error': error}), 500
        # Normalize to minimal payload for dropdown
        results = data.get('result', {}).get('data', [])
        minimal = [{'id': c.get('id'), 'name': c.get('public_name') or c.get('name') or ''} for c in results]
        return jsonify({'result': {'data': minimal}})

    data, error = make_paginated_api_request('/api/public/v1/core/companies', params=params)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify(data)


@app.route('/api/companies/<int:company_id>')
def api_company(company_id):
    """Get specific company"""
    if not is_token_valid():
        return jsonify({'error': 'Not authenticated'}), 401
    
    data, error = make_api_request(f'/api/public/v1/core/companies/{company_id}')
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify(data)


@app.route('/api/sales-invoices')
def api_sales_invoices():
    """Get sales invoices"""
    if not is_token_valid():
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Add pagination parameters to get all results
    params = {
        'per_page': 100,  # Request up to 100 items per page
        'page': 1
    }
    
    # Get query parameters for filtering and ordering
    if request.args.get('filter_by_created_since'):
        params['filter_by_created_since'] = request.args.get('filter_by_created_since')
    if request.args.get('filter_by_updated_since'):
        params['filter_by_updated_since'] = request.args.get('filter_by_updated_since')
    # Also support start/end date passthrough used by the UI
    if request.args.get('filter_by_start_date'):
        params['filter_by_start_date'] = request.args.get('filter_by_start_date')
    if request.args.get('filter_by_end_date'):
        params['filter_by_end_date'] = request.args.get('filter_by_end_date')
    if request.args.get('filter_by_company'):
        params['filter_by_company'] = request.args.get('filter_by_company')
    if request.args.get('filter_by_status'):
        params['filter_by_status'] = request.args.get('filter_by_status')
    if request.args.get('order_by_date'):
        params['order_by_date'] = request.args.get('order_by_date')
    if request.args.get('order_by_amount'):
        params['order_by_amount'] = request.args.get('order_by_amount')
    
    data, error = make_paginated_api_request('/api/public/v1/trade/sales-invoices', params=params)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify(data)


@app.route('/api/analytics/sales')
def api_analytics_sales():
    """Aggregate sales data for visualization.
    Query params:
      filter_by_company: company ID
      filter_by_product: product id or name (best-effort)
      filter_by_start_date, filter_by_end_date
      group_by: date|company|product (default: date)
      interval: day|week|month (default: day)
    """
    if not is_token_valid():
        return jsonify({'error': 'Not authenticated'}), 401

    group_by = request.args.get('group_by', 'date')
    interval = request.args.get('interval', 'day')
    product_filter = request.args.get('filter_by_product')

    params = { 'per_page': 100, 'page': 1 }
    if request.args.get('filter_by_company'):
        params['filter_by_company'] = request.args.get('filter_by_company')
    if request.args.get('filter_by_start_date'):
        params['filter_by_start_date'] = request.args.get('filter_by_start_date')
    if request.args.get('filter_by_end_date'):
        params['filter_by_end_date'] = request.args.get('filter_by_end_date')
    params['order_by_date'] = request.args.get('order_by_date', 'desc')

    raw, error = make_paginated_api_request('/api/public/v1/trade/sales-invoices', params=params)
    if error:
        return jsonify({'error': error}), 500
    invoices = raw.get('result', {}).get('data', [])

    def get_amount(inv):
        return (
            inv.get('payable_amount_without_financial_discount')
            or inv.get('payable_amount_with_financial_discount')
            or inv.get('balance')
            or 0
        ) or 0

    if product_filter:
        pf = product_filter.lower()
        filtered = []
        for inv in invoices:
            lines = inv.get('invoice_line_items') or []
            if any(((ln.get('product') or {}).get('name') or ln.get('description') or '').lower().find(pf) != -1 or str((ln.get('product') or {}).get('id') or '') == product_filter for ln in lines):
                filtered.append(inv)
        invoices = filtered

    from datetime import datetime
    def bucket_date(iso_str):
        try:
            dt = datetime.strptime((iso_str or '').split(' ')[0], '%Y-%m-%d')
        except Exception:
            return iso_str or ''
        if interval == 'week':
            return f"{dt.isocalendar().year}-W{dt.isocalendar().week:02d}"
        if interval == 'month':
            return dt.strftime('%Y-%m')
        return dt.strftime('%Y-%m-%d')

    buckets = {}
    total_amount = 0.0

    def get_line_amount(ln):
        return (
            ln.get('total_incl_tax')
            or ln.get('total_excl_tax')
            or ln.get('line_total')
            or ln.get('net_amount')
            or ln.get('gross_amount')
            or ln.get('subtotal')
            or (
                (ln.get('unit_price_incl_tax') or ln.get('unit_price') or 0)
                * (ln.get('quantity') or ln.get('qty') or 0)
            )
            or ln.get('amount')
            or ln.get('value')
            or 0
        )

    if group_by == 'product':
        # Aggregate per product across all invoices based on invoice line items
        for inv in invoices:
            for ln in inv.get('invoice_line_items') or []:
                prod = (ln.get('product') or {})
                name = prod.get('name') or ln.get('description') or 'Unspecified'
                amt = float(get_line_amount(ln) or 0)
                total_amount += amt
                buckets[name] = buckets.get(name, 0.0) + amt
    else:
        for inv in invoices:
            amt = float(get_amount(inv) or 0)
            total_amount += amt
            if group_by == 'company':
                key = (inv.get('company') or {}).get('public_name') or (inv.get('company') or {}).get('name') or inv.get('buyer_name') or 'Unknown'
            else:
                key = bucket_date(inv.get('date') or inv.get('created_at') or '')
            buckets[key] = buckets.get(key, 0.0) + amt

    labels = list(buckets.keys())
    try:
        labels.sort()
    except Exception:
        pass
    data_points = [round(buckets[k], 2) for k in labels]

    return jsonify({'result': {'labels': labels, 'datasets': [{ 'label': 'Amount (€)', 'data': data_points }], 'total_amount': round(total_amount, 2), 'count': len(invoices)}})


@app.route('/api/sales-invoices/<int:invoice_id>')
def api_sales_invoice(invoice_id):
    """Get specific sales invoice"""
    if not is_token_valid():
        return jsonify({'error': 'Not authenticated'}), 401
    
    data, error = make_api_request(f'/api/public/v1/trade/sales-invoices/{invoice_id}')
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify(data)


@app.route('/api/companies/<int:company_id>/sales')
def api_company_sales(company_id):
    """Get sales data for a specific company"""
    if not is_token_valid():
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Add pagination parameters and company filter
    params = {
        'per_page': 100,
        'page': 1,
        'filter_by_company': company_id
    }
    
    # Add additional filters from query parameters
    if request.args.get('filter_by_created_since'):
        params['filter_by_created_since'] = request.args.get('filter_by_created_since')
    if request.args.get('filter_by_updated_since'):
        params['filter_by_updated_since'] = request.args.get('filter_by_updated_since')
    if request.args.get('filter_by_status'):
        params['filter_by_status'] = request.args.get('filter_by_status')
    
    data, error = make_paginated_api_request('/api/public/v1/trade/sales-invoices', params=params)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify(data)


@app.route('/api/companies/<int:company_id>/bookings')
def api_company_bookings(company_id):
    """Get bookings for a specific company"""
    if not is_token_valid():
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Add pagination parameters and company filter
    params = {
        'per_page': 100,
        'page': 1,
        'filter_by_company': company_id
    }
    
    # Add additional filters from query parameters
    if request.args.get('filter_by_start_date'):
        params['filter_by_start_date'] = request.args.get('filter_by_start_date')
    if request.args.get('filter_by_end_date'):
        params['filter_by_end_date'] = request.args.get('filter_by_end_date')
    if request.args.get('filter_by_booking_type'):
        params['filter_by_booking_type'] = request.args.get('filter_by_booking_type')
    if request.args.get('order_by_date'):
        params['order_by_date'] = request.args.get('order_by_date')
    
    data, error = make_paginated_api_request('/api/public/v1/accountancy/bookings', params=params)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify(data)


@app.route('/api/composed-product-items')
def api_composed_product_items():
    """Get composed product items"""
    if not is_token_valid():
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Add pagination parameters to get all results
    params = {
        'per_page': 100,  # Request up to 100 items per page
        'page': 1
    }
    
    # Get query parameters for filtering and ordering
    if request.args.get('filter_by_created_since'):
        params['filter_by_created_since'] = request.args.get('filter_by_created_since')
    if request.args.get('filter_by_updated_since'):
        params['filter_by_updated_since'] = request.args.get('filter_by_updated_since')
    if request.args.get('filter_by_composed_product'):
        params['filter_by_composed_product'] = request.args.get('filter_by_composed_product')
    if request.args.get('filter_by_product'):
        params['filter_by_product'] = request.args.get('filter_by_product')
    if request.args.get('order_by_name'):
        params['order_by_name'] = request.args.get('order_by_name')
    if request.args.get('order_by_sku'):
        params['order_by_sku'] = request.args.get('order_by_sku')
    
    data, error = make_paginated_api_request('/api/public/v1/core/composed-product-items', params=params)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify(data)


@app.route('/api/composed-product-items/<int:item_id>')
def api_composed_product_item(item_id):
    """Get specific composed product item"""
    if not is_token_valid():
        return jsonify({'error': 'Not authenticated'}), 401
    
    data, error = make_api_request(f'/api/public/v1/core/composed-product-items/{item_id}')
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify(data)


@app.route('/api/products/hierarchy')
def api_products_hierarchy():
    """Get product hierarchy with composed products and their components"""
    if not is_token_valid():
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get all composed product items
    params = {
        'per_page': 1000,  # Get all items to build hierarchy
        'page': 1
    }
    
    data, error = make_paginated_api_request('/api/public/v1/core/composed-product-items', params=params)
    
    if error:
        return jsonify({'error': error}), 500
    
    # Process the data to create a hierarchical structure
    if 'result' in data and 'data' in data['result']:
        items = data['result']['data']
        
        # Group by composed product
        hierarchy = {}
        unique_products = {}  # Track all unique products (both composed and component)
        
        for item in items:
            composed_product = item.get('composed_product', {})
            component_product = item.get('product', {})
            quantity = item.get('quantity', 0)
            
            # Track unique products
            if composed_product.get('id'):
                unique_products[composed_product['id']] = {
                    **composed_product,
                    'type': 'composed'
                }
            if component_product.get('id'):
                unique_products[component_product['id']] = {
                    **component_product,
                    'type': 'component'
                }
            
            composed_id = composed_product.get('id')
            if composed_id not in hierarchy:
                hierarchy[composed_id] = {
                    'composed_product': composed_product,
                    'components': [],
                    'total_components': 0
                }
            
            hierarchy[composed_id]['components'].append({
                'product': component_product,
                'quantity': quantity,
                'item_id': item.get('id'),
                'created_at': item.get('created_at'),
                'updated_at': item.get('updated_at')
            })
            hierarchy[composed_id]['total_components'] += 1
        
        # Convert to list format and add statistics
        hierarchy_list = list(hierarchy.values())
        
        # Add summary statistics
        data['result']['hierarchy'] = hierarchy_list
        data['result']['statistics'] = {
            'total_composed_products': len(hierarchy_list),
            'total_unique_products': len(unique_products),
            'total_component_relationships': len(items)
        }
        data['result']['unique_products'] = list(unique_products.values())
    
    return jsonify(data)


@app.route('/api/composed-products/<int:composed_product_id>/components')
def api_composed_product_components(composed_product_id):
    """Get all component products for a specific composed product"""
    if not is_token_valid():
        return jsonify({'error': 'Not authenticated'}), 401
    
    params = {
        'per_page': 100,
        'page': 1,
        'filter_by_composed_product': composed_product_id
    }
    
    data, error = make_paginated_api_request('/api/public/v1/core/composed-product-items', params=params)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify(data)


@app.route('/api/products/<int:product_id>/composed-products')
def api_product_composed_products(product_id):
    """Get all composed products that use a specific component product"""
    if not is_token_valid():
        return jsonify({'error': 'Not authenticated'}), 401
    
    params = {
        'per_page': 100,
        'page': 1,
        'filter_by_product': product_id
    }
    
    data, error = make_paginated_api_request('/api/public/v1/core/composed-product-items', params=params)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify(data)


@app.route('/prospecting')
def prospecting():
    """Prospecting page with Google Maps and VAT lookup"""
    if not is_token_valid():
        return redirect(url_for('index'))
    return render_template('prospecting.html', google_maps_api_key=GOOGLE_MAPS_API_KEY)


def _companyweb_search_url(company_name: str) -> str:
    try:
        q = urllib.parse.quote(company_name or '')
        # Use the corrected search URL format
        return f"https://www.companyweb.be/search?q={q}"
    except Exception:
        return "https://www.companyweb.be/"


def _search_duano_by_vat(vat_number: str):
    candidates = []
    if not vat_number:
        return []
    normalized_digits = ''.join(ch for ch in vat_number if ch.isdigit())
    variants = [vat_number]
    if normalized_digits:
        variants.append(f"BE{normalized_digits}")
        if len(normalized_digits) == 9:
            variants.append(f"BE0{normalized_digits}")
        if len(normalized_digits) == 10:
            variants.append(normalized_digits)
    seen = set()
    for v in variants:
        if v in seen:
            continue
        seen.add(v)
        data, error = make_paginated_api_request('/api/public/v1/core/companies', params={'filter_by_vat_number': v, 'per_page': 50, 'page': 1})
        if not error and isinstance(data, dict):
            items = (data.get('result') or {}).get('data') or []
            if items:
                candidates.extend(items)
    return candidates


@app.route('/api/prospecting/vat-lookup', methods=['POST'])
def api_prospecting_vat_lookup():
    if not is_token_valid():
        return jsonify({'error': 'Not authenticated'}), 401
    payload = request.get_json(silent=True) or {}
    company_name = (payload.get('company_name') or '').strip()
    website_url = (payload.get('website_url') or '').strip()
    free_text = payload.get('text') or ''

    found_vats = []
    source = 'none'

    # 1) Try website scraping
    if website_url:
        html = _fetch_text_from_url(website_url)
        vats = _extract_belgian_vat_numbers(html)
        if vats:
            found_vats.extend(vats)
            source = 'website'

    # 2) Try free_text provided by caller
    if not found_vats and free_text:
        vats = _extract_belgian_vat_numbers(free_text)
        if vats:
            found_vats.extend(vats)
            source = 'text'

    # 3) Optionally ask LLM to extract VAT from collected text
    if not found_vats and OPENAI_API_KEY and openai_client and (website_url or free_text):
        try:
            combined = free_text
            if website_url and not combined:
                combined = _fetch_text_from_url(website_url)[:16000]
            if combined:
                prompt = (
                    "From the following text, extract any Belgian VAT numbers (BTW/TVA/VAT). "
                    "Return only a comma-separated list of normalized VAT numbers in the form BE0123456789.\n\n" + combined
                )
                resp = openai_client.chat.completions.create(
                    model='gpt-4o-mini',
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                content = resp.choices[0].message.content if resp and resp.choices else ''
                vats = _extract_belgian_vat_numbers(content)
                if vats:
                    found_vats.extend(vats)
                    source = 'ai'
        except Exception:
            pass

    # Deduplicate
    found_vats = sorted(set(found_vats))

    return jsonify({
        'vat_numbers': found_vats,
        'source': source,
        'companyweb_url': _companyweb_search_url(company_name) if company_name else 'https://www.companyweb.be/nl'
    })


@app.route('/api/prospecting/check-vat', methods=['GET'])
def api_prospecting_check_vat():
    if not is_token_valid():
        return jsonify({'error': 'Not authenticated'}), 401
    vat_number = request.args.get('vat_number', '').strip()
    matches = _search_duano_by_vat(vat_number)
    return jsonify({'result': {'data': matches, 'count': len(matches)}})


@app.route('/api/prospecting/enrich-company', methods=['POST'])
def api_prospecting_enrich_company():
    """Use AI web search to gather public info about a company.

    Body: { company_name, website_url?, city?, region?, country? }
    Returns: { summary, sources, websites, official_site, vat_numbers, emails, phone_numbers, addresses, social_links, companyweb_url }
    """
    if not is_token_valid():
        return jsonify({'error': 'Not authenticated'}), 401

    if not (OPENAI_API_KEY and openai_client):
        return jsonify({'error': 'AI enrichment unavailable: missing OpenAI key'}), 400

    payload = request.get_json(silent=True) or {}
    company_name = (payload.get('company_name') or '').strip()
    website_url = (payload.get('website_url') or '').strip()
    city = (payload.get('city') or '').strip()
    region = (payload.get('region') or '').strip()
    country = (payload.get('country') or 'BE').strip() or 'BE'
    if not company_name:
        return jsonify({'error': 'company_name is required'}), 400

    user_loc = {
        'type': 'approximate',
        'country': country,
        'city': city or None,
        'region': region or None,
    }

    instruction = (
        "Using web search, find authoritative, up-to-date public info about the given Belgian company. "
        "Return a compact JSON object with keys: summary (1-2 sentences), sources (top 3 URLs), websites (list), official_site, "
        "vat_numbers (list, normalized as BE0123456789), emails (list), phone_numbers (list), addresses (list of strings), "
        "social_links (object: linkedin, facebook, twitter, instagram). Be concise."
    )
    user_input = f"Company: {company_name}\nWebsite hint: {website_url or 'n/a'}"

    try:
        resp = openai_client.responses.create(
            model='gpt-5',
            tools=[{
                'type': 'web_search_preview',
                'user_location': user_loc
            }],
            input=user_input + "\n\n" + instruction
        )
        output_text = getattr(resp, 'output_text', None)
        if not output_text:
            # Fallback best-effort
            output_text = json.dumps({'summary': 'No output', 'sources': []})
    except Exception as e:
        return jsonify({'error': f'AI error: {str(e)}'}), 500

    # Try to parse JSON from the model output; fallback to heuristic extraction
    data = {}
    try:
        # Common case: model returns raw JSON text
        data = json.loads(output_text)
    except Exception:
        # Heuristic extraction
        data = {
            'summary': output_text[:600],
            'sources': [],
        }

    # Normalize fields
    data.setdefault('websites', [])
    data.setdefault('official_site', website_url or (data['websites'][0] if data['websites'] else ''))
    data.setdefault('vat_numbers', [])
    data.setdefault('emails', [])
    data.setdefault('phone_numbers', [])
    data.setdefault('addresses', [])
    data.setdefault('social_links', {})
    data.setdefault('sources', data.get('sources') or [])

    # Extract VATs from text as an extra safety net
    enriched_text_blob = output_text + "\n" + "\n".join(map(str, data.get('sources', [])))
    extra_vats = _extract_belgian_vat_numbers(enriched_text_blob)
    if extra_vats:
        data['vat_numbers'] = sorted(set((data.get('vat_numbers') or []) + extra_vats))

    data['companyweb_url'] = _companyweb_search_url(company_name)

    return jsonify({'result': data})


@app.route('/api/prospecting/companyweb-search', methods=['POST'])
def api_prospecting_companyweb_search():
    """AI-assisted web search constrained to Companyweb for a given business.

    Body: { company_name: str, address: str }
    Returns: { result: { ...structured fields... } }
    """
    if not is_token_valid():
        return jsonify({'error': 'Not authenticated'}), 401

    if not (OPENAI_API_KEY and openai_client):
        return jsonify({'error': 'AI enrichment unavailable: missing OpenAI key'}), 400

    payload = request.get_json(silent=True) or {}
    company_name = (payload.get('company_name') or '').strip()
    address = (payload.get('address') or '').strip()
    if not company_name:
        return jsonify({'error': 'company_name is required'}), 400

    companyweb_url = f"https://www.companyweb.be/en?q={urllib.parse.quote(company_name)}"
    user_prompt = (
        f"Find comprehensive business information for this Belgian company:\n\n"
        f"Company Name: {company_name}\n"
        f"Address: {address or 'Belgium'}\n\n"
        f"Search sources to check:\n"
        f"- companyweb.be (Belgian business database)\n"
        f"- Official company website\n"
        f"- Business directories\n"
        f"- Government registries\n"
        f"- Social media and review sites\n\n"
        f"Please extract and return this information in JSON format:\n\n"
        f"```json\n"
        f"{{\n"
        f'  "name": "{company_name}",\n'
        f'  "normalized_vat_numbers": [],\n'
        f'  "registered_address": "",\n'
        f'  "website": "",\n'
        f'  "emails": [],\n'
        f'  "phones": [],\n'
        f'  "activities": [],\n'
        f'  "directors": [],\n'
        f'  "credit_score": "",\n'
        f'  "barometer": "",\n'
        f'  "notes": "",\n'
        f'  "sources": []\n'
        f"}}\n"
        f"```\n\n"
        f"Important notes:\n"
        f"- VAT numbers should be in format BE0123456789\n"
        f"- Include all contact information found (emails, phones)\n"
        f"- List business activities/services\n"
        f"- Include management/director names if available\n"
        f"- Add any credit rating or financial health indicators\n"
        f"- Provide source URLs for verification"
    )

    result_payload = {
        'name': company_name,
        'vat': '',
        'registered': address,
        'site': '',
        'email': '',
        'phone': '',
        'directors': '',
        'companyweb_url': companyweb_url,
    }

    error_message = None
    try:
        # Fast approach: direct scraping + AI analysis instead of slow web search tool
        companyweb_search_url = f"https://www.companyweb.be/search?q={urllib.parse.quote(company_name)}"
        
        # Try to get some web content directly
        scraped_content = ""
        potential_websites = []
        
        # Quick scrape of a few likely sources
        for url_attempt in [companyweb_search_url]:
            try:
                content = _fetch_text_from_url(url_attempt)[:8000]  # Limit size
                if content and len(content) > 100:
                    scraped_content += f"\n--- From {url_attempt} ---\n{content}\n"
                    break
            except:
                continue
        
        # Fast AI analysis of scraped content
        if scraped_content:
            analysis_prompt = (
                f"Extract ONLY these 6 fields from this web content about '{company_name}':\n\n"
                f"{scraped_content[:2000]}\n\n"
                f"Return JSON: {{\n"
                f'  "vat": "BE0123456789 or empty",\n'
                f'  "registered": "full address or empty",\n'
                f'  "site": "website URL or empty",\n'
                f'  "email": "main email or empty",\n'
                f'  "phone": "main phone or empty",\n'
                f'  "directors": "director names or empty"\n'
                f"}}"
            )
            
            resp = openai_client.chat.completions.create(
                model='gpt-4o-mini',
                messages=[{"role": "user", "content": analysis_prompt}],
                temperature=0,
                max_tokens=200
            )
            output_text = resp.choices[0].message.content if resp.choices else ''
        else:
            # If scraping fails, do a minimal web search with fast model
            resp = openai_client.responses.create(
                model='gpt-5',
                tools=[{ 'type': 'web_search_preview', 'search_context_size': 'low' }],
                input=user_prompt
            )
            output_text = getattr(resp, 'output_text', '') or ''
        
        # Parse the result
        try:
            parsed = json.loads(output_text)
            if isinstance(parsed, dict):
                result_payload.update(parsed)
        except Exception:
            # Try to extract JSON from within the text (sometimes wrapped in markdown)
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', output_text, re.DOTALL)
            if json_match:
                try:
                    parsed = json.loads(json_match.group(1))
                    if isinstance(parsed, dict):
                        # Map old format to new simplified format
                        if 'normalized_vat_numbers' in parsed and parsed['normalized_vat_numbers']:
                            result_payload['vat'] = parsed['normalized_vat_numbers'][0]
                        if 'registered_address' in parsed:
                            result_payload['registered'] = parsed['registered_address']
                        if 'website' in parsed:
                            result_payload['site'] = parsed['website']
                        if 'emails' in parsed and parsed['emails']:
                            result_payload['email'] = parsed['emails'][0]
                        if 'phones' in parsed and parsed['phones']:
                            result_payload['phone'] = parsed['phones'][0]
                        if 'directors' in parsed and parsed['directors']:
                            result_payload['directors'] = ', '.join(parsed['directors']) if isinstance(parsed['directors'], list) else str(parsed['directors'])
                        # Update with any direct matches
                        for key in ['vat', 'registered', 'site', 'email', 'phone', 'directors']:
                            if key in parsed and parsed[key]:
                                result_payload[key] = parsed[key]
                except:
                    pass
            # Fallback heuristic extraction
            if not result_payload.get('vat'):
                vats = _extract_belgian_vat_numbers(output_text)
                if vats:
                    result_payload['vat'] = vats[0]
            if not result_payload.get('email') or not result_payload.get('phone'):
                emails, phones = _extract_emails_and_phones(output_text)
                if emails and not result_payload.get('email'):
                    result_payload['email'] = emails[0]
                if phones and not result_payload.get('phone'):
                    result_payload['phone'] = phones[0]
            
    except Exception as e:
        error_message = str(e)

    # Additional parsing pass: check if data is hidden in notes field
    notes_content = result_payload.get('notes', '')
    if notes_content and not any([result_payload.get('vat'), result_payload.get('site'), result_payload.get('email')]):
        import re
        # Try to extract JSON from notes
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', notes_content, re.DOTALL)
        if not json_match:
            json_match = re.search(r'(\{.*?\})', notes_content, re.DOTALL)
        
        if json_match:
            try:
                parsed_notes = json.loads(json_match.group(1))
                if isinstance(parsed_notes, dict):
                    # Map old format to new simplified format
                    if 'normalized_vat_numbers' in parsed_notes and parsed_notes['normalized_vat_numbers']:
                        result_payload['vat'] = parsed_notes['normalized_vat_numbers'][0]
                    if 'website' in parsed_notes and parsed_notes['website']:
                        result_payload['site'] = parsed_notes['website']
                    if 'emails' in parsed_notes and parsed_notes['emails']:
                        result_payload['email'] = parsed_notes['emails'][0]
                    if 'phones' in parsed_notes and parsed_notes['phones']:
                        result_payload['phone'] = parsed_notes['phones'][0]
                    if 'directors' in parsed_notes and parsed_notes['directors']:
                        if isinstance(parsed_notes['directors'], list):
                            result_payload['directors'] = ', '.join(parsed_notes['directors'])
                        else:
                            result_payload['directors'] = str(parsed_notes['directors'])
                    if 'registered_address' in parsed_notes and parsed_notes['registered_address']:
                        result_payload['registered'] = parsed_notes['registered_address']
            except Exception as parse_err:
                # Still try heuristic extraction from notes text
                vats = _extract_belgian_vat_numbers(notes_content)
                if vats:
                    result_payload['vat'] = vats[0]
                emails, phones = _extract_emails_and_phones(notes_content)
                if emails:
                    result_payload['email'] = emails[0]
                if phones:
                    result_payload['phone'] = phones[0]

    # Always include canonical Companyweb URL and return 200 even on partial data
    result_payload['companyweb_url'] = result_payload.get('companyweb_url') or companyweb_url
    response_obj = { 'result': result_payload }
    if error_message:
        response_obj['warning'] = f"AI search degraded: {error_message}"
    return jsonify(response_obj)


# Prospect Management API Routes
@app.route('/api/prospects', methods=['GET'])
def api_get_prospects():
    """Get all prospects from Supabase"""
    if not is_token_valid():
        return jsonify({'error': 'Not authenticated'}), 401
    
    if not supabase_client:
        return jsonify({'error': 'Supabase client not configured. Check your connection.'}), 500
    
    try:
        # Get query parameters for filtering
        status_filter = request.args.get('status')
        limit = int(request.args.get('limit', 100))
        
        # Build query
        query = supabase_client.table('prospects').select('*')
        
        if status_filter:
            query = query.eq('status', status_filter)
        
        # Execute query with limit
        result = query.limit(limit).order('created_at', desc=True).execute()
        
        return jsonify({
            'prospects': result.data,
            'count': len(result.data)
        })
        
    except Exception as e:
        error_msg = str(e)
        if 'relation "prospects" does not exist' in error_msg or 'table "prospects" does not exist' in error_msg:
            return jsonify({
                'error': 'Database table "prospects" does not exist. Please run the SQL setup script first.',
                'setup_required': True
            }), 500
        return jsonify({'error': f'Failed to fetch prospects: {error_msg}'}), 500


@app.route('/api/prospects', methods=['POST'])
def api_create_prospect():
    """Create a new prospect in Supabase with background enrichment"""
    if not is_token_valid():
        return jsonify({'error': 'Not authenticated'}), 401
    
    if not supabase_client:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        data = request.get_json()
        if not data or not data.get('name'):
            return jsonify({'error': 'Prospect name is required'}), 400
        
        # Extract city from address for tagging
        def extract_city_from_address(address):
            if not address:
                return []
            address_lower = address.lower()
            cities = []
            city_mappings = {
                'antwerpen': 'Antwerpen',
                'antwerp': 'Antwerpen', 
                'gent': 'Gent',
                'ghent': 'Gent',
                'brussels': 'Brussels',
                'brussel': 'Brussels',
                'brugge': 'Brugge',
                'bruges': 'Brugge',
                'leuven': 'Leuven',
                'mechelen': 'Mechelen',
                'hasselt': 'Hasselt',
                'charleroi': 'Charleroi',
                'liège': 'Liège',
                'namur': 'Namur'
            }
            for key, city in city_mappings.items():
                if key in address_lower:
                    cities.append(city)
                    break  # Take first match
            return cities
        
        # Prepare tags
        city_tags = extract_city_from_address(data.get('address', ''))
        keyword_tags = []
        if data.get('search_query'):
            # Extract keywords from search query, excluding common words
            keywords = data['search_query'].lower().replace(',', ' ').split()
            stop_words = {'in', 'at', 'the', 'and', 'or', 'of', 'for', 'with', 'by', 'from', 'to', 'a', 'an'}
            keyword_tags = [word.strip() for word in keywords if len(word) > 2 and word not in stop_words]
        
        tags = {
            'city': city_tags,
            'keywords': keyword_tags[:5],  # Limit to 5 keywords
            'custom': []
        }
        
        # Prepare prospect data
        prospect_data = {
            'name': data['name'],
            'address': data.get('address', ''),
            'website': data.get('website', ''),
            'status': data.get('status', 'new'),
            'enriched_data': data.get('enriched_data', {}),
            'google_place_id': data.get('google_place_id'),
            'tags': tags,
            'search_query': data.get('search_query', ''),
            'enrichment_status': 'pending',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        # Insert into Supabase
        result = supabase_client.table('prospects').insert(prospect_data).execute()
        
        if result.data:
            prospect_id = result.data[0]['id']
            
            # Start background enrichment if we have company name and no enriched data
            if data['name'] and not data.get('enriched_data'):
                try:
                    print(f"Starting backend enrichment for prospect {prospect_id}: {data['name']}")
                    _enrich_prospect_background(prospect_id, data['name'], data.get('address', ''), data.get('website', ''))
                except Exception as e:
                    # Log error but don't fail the request
                    print(f"Background enrichment failed for prospect {prospect_id}: {e}")
            else:
                print(f"Skipping backend enrichment for prospect {prospect_id}: name={data.get('name')}, has_enriched_data={bool(data.get('enriched_data'))}")
            
            return jsonify({
                'prospect': result.data[0],
                'message': 'Prospect created successfully'
            }), 201
        else:
            return jsonify({'error': 'Failed to create prospect'}), 500
            
    except Exception as e:
        error_msg = str(e)
        if 'row-level security policy' in error_msg or '42501' in error_msg:
            return jsonify({
                'error': 'Database permission error. Please run the RLS fix script.',
                'details': 'Row Level Security policy is blocking operations. Run fix_rls_policy.sql in Supabase.',
                'setup_required': True
            }), 500
        return jsonify({'error': f'Failed to create prospect: {error_msg}'}), 500


@app.route('/api/prospects/<prospect_id>', methods=['PATCH'])
def api_update_prospect(prospect_id):
    """Update a prospect's status or other fields"""
    if not is_token_valid():
        return jsonify({'error': 'Not authenticated'}), 401
    
    if not supabase_client:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Prepare update data
        update_data = {
            'updated_at': datetime.now().isoformat()
        }
        
        # Add allowed fields
        allowed_fields = ['status', 'name', 'address', 'website', 'enriched_data', 'notes']
        for field in allowed_fields:
            if field in data:
                update_data[field] = data[field]
        
        # Update in Supabase
        result = supabase_client.table('prospects').update(update_data).eq('id', prospect_id).execute()
        
        if result.data:
            return jsonify({
                'prospect': result.data[0],
                'message': 'Prospect updated successfully'
            })
        else:
            return jsonify({'error': 'Prospect not found'}), 404
            
    except Exception as e:
        return jsonify({'error': f'Failed to update prospect: {str(e)}'}), 500


@app.route('/api/prospects/<prospect_id>', methods=['DELETE'])
def api_delete_prospect(prospect_id):
    """Delete a prospect from Supabase"""
    if not is_token_valid():
        return jsonify({'error': 'Not authenticated'}), 401
    
    if not supabase_client:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        # Delete from Supabase
        result = supabase_client.table('prospects').delete().eq('id', prospect_id).execute()
        
        if result.data:
            return jsonify({'message': 'Prospect deleted successfully'})
        else:
            return jsonify({'error': 'Prospect not found'}), 404
            
    except Exception as e:
        return jsonify({'error': f'Failed to delete prospect: {str(e)}'}), 500


def _enrich_prospect_background(prospect_id, company_name, address, website):
    """Background task to enrich prospect data using AI"""
    import threading
    
    def enrich_task():
        try:
            if not (OPENAI_API_KEY and openai_client):
                print(f"No OpenAI client available for enrichment of {company_name}")
                return
            
            print(f"Starting background enrichment for prospect {prospect_id}: {company_name}")
            
            # Set status to in_progress
            try:
                supabase_client.table('prospects').update({
                    'enrichment_status': 'in_progress',
                    'updated_at': datetime.now().isoformat()
                }).eq('id', prospect_id).execute()
            except Exception as e:
                print(f"Failed to update enrichment status to in_progress: {e}")
                return
            
            # Use the existing companyweb search logic
            enrichment_data = {}
            
            # Try to get enriched data
            payload = {
                'company_name': company_name,
                'address': address
            }
            
            # Simulate the companyweb search API call internally
            companyweb_url = f"https://www.companyweb.be/en?q={urllib.parse.quote(company_name)}"
            
            try:
                print(f"Starting web scraping for {company_name}")
                
                # Try multiple sources for enrichment
                enrichment_data = {}
                
                # Use OpenAI Responses API with proper web search
                try:
                    print(f"Using OpenAI web search for {company_name}")
                    
                    search_input = (
                        f"Find current information about the Belgian company '{company_name}' "
                        f"located at {address}{f' with website {website}' if website else ''}. "
                        f"I need their VAT/BTW number (BE0123456789 format), official website, "
                        f"contact email, phone number, registered address, and company directors/owners. "
                        f"Please search the web for accurate, up-to-date information and provide "
                        f"the results in this exact JSON format: "
                        f'{{"vat": "", "registered": "", "site": "", "email": "", "phone": "", "directors": ""}}'
                    )
                    
                    # Use the proper Responses API with web search
                    try:
                        resp = openai_client.responses.create(
                            model='gpt-4o',
                            tools=[{
                                "type": "web_search_preview",
                                "user_location": {
                                    "type": "approximate",
                                    "country": "BE",
                                    "city": "Gent",
                                    "region": "East Flanders"
                                }
                            }],
                            input=search_input
                        )
                        output_text = resp.output_text if hasattr(resp, 'output_text') else ''
                        print(f"Web search result: {output_text}")
                        
                    except Exception as web_error:
                        print(f"Web search API failed: {web_error}")
                        # Fallback to regular chat completion
                        resp = openai_client.chat.completions.create(
                            model='gpt-4o',
                            messages=[{"role": "user", "content": search_input}],
                            temperature=0,
                            max_tokens=400
                        )
                        output_text = resp.choices[0].message.content if resp.choices else ''
                        print(f"Fallback AI result: {output_text}")
                    
                    # Parse the result - handle markdown code blocks
                    try:
                        # First try direct JSON parsing
                        enrichment_data = json.loads(output_text)
                    except json.JSONDecodeError:
                        # Try to extract JSON from markdown code blocks
                        import re
                        json_match = re.search(r'```json\s*(\{.*?\})\s*```', output_text, re.DOTALL)
                        if json_match:
                            try:
                                enrichment_data = json.loads(json_match.group(1))
                            except json.JSONDecodeError as je:
                                print(f"JSON parse error in markdown block: {je}")
                                enrichment_data = {}
                        else:
                            print(f"No JSON found in output: {output_text[:200]}...")
                            enrichment_data = {}
                            
                except Exception as e:
                    print(f"Overall search failed: {e}")
                    enrichment_data = {}
                
                # Fallback: Try basic AI enrichment if web search failed
                if not enrichment_data or not any(enrichment_data.values()):
                    print(f"Trying basic AI enrichment for {company_name}")
                    basic_prompt = (
                        f"Find basic information about this Belgian company: {company_name}\n"
                        f"Address: {address}\n"
                        f"Website: {website}\n\n"
                        f"Return ONLY a JSON object with these fields:\n"
                        f'{{\n'
                        f'  "vat": "BE0123456789 or empty",\n'
                        f'  "registered": "full address or empty",\n'
                        f'  "site": "website URL or empty",\n'
                        f'  "email": "main email or empty",\n'
                        f'  "phone": "main phone or empty",\n'
                        f'  "directors": "director names or empty"\n'
                        f'}}'
                    )
                    
                    try:
                        resp = openai_client.chat.completions.create(
                            model='gpt-4o-mini',
                            messages=[{"role": "user", "content": basic_prompt}],
                            temperature=0,
                            max_tokens=200
                        )
                        output_text = resp.choices[0].message.content if resp.choices else ''
                        print(f"Basic AI result: {output_text}")
                        
                        try:
                            enrichment_data = json.loads(output_text)
                        except json.JSONDecodeError:
                            # Fallback to basic data
                            enrichment_data = {
                                'vat': '',
                                'email': '',
                                'phone': '',
                                'site': website or '',
                                'registered': address or '',
                                'directors': ''
                            }
                    except Exception as e:
                        print(f"Basic AI enrichment failed: {e}")
                        enrichment_data = {
                            'vat': '',
                            'email': '',
                            'phone': '',
                            'site': website or '',
                            'registered': address or '',
                            'directors': ''
                        }
                
                print(f"Final enrichment data for {company_name}: {enrichment_data}")
                
            except Exception as e:
                print(f"Enrichment failed for {company_name}: {e}")
                enrichment_data = {
                    'vat': '',
                    'email': '',
                    'phone': '',
                    'site': website or '',
                    'registered': address or '',
                    'directors': ''
                }
            
            # Only update prospect with enrichment data if we found actual information
            try:
                # Check if we found any meaningful data
                has_meaningful_data = enrichment_data and any(
                    v for v in enrichment_data.values() 
                    if v and v.strip() and v != 'empty' and v != address and v != website
                )
                
                update_data = {
                    'updated_at': datetime.now().isoformat()
                }
                
                if has_meaningful_data:
                    update_data['enriched_data'] = enrichment_data
                    update_data['enrichment_status'] = 'completed'
                    supabase_client.table('prospects').update(update_data).eq('id', prospect_id).execute()
                    print(f"Successfully enriched prospect {prospect_id}: {company_name} with data: {enrichment_data}")
                else:
                    # Set status to indicate no meaningful data was found
                    update_data['enrichment_status'] = 'no_data'
                    supabase_client.table('prospects').update(update_data).eq('id', prospect_id).execute()
                    print(f"Enrichment attempted but no meaningful data found for prospect {prospect_id}: {company_name}")
                    print(f"Raw enrichment data was: {enrichment_data}")
                    
            except Exception as e:
                print(f"Failed to update prospect {prospect_id} with enriched data: {e}")
                # Set status to failed on database update error
                try:
                    supabase_client.table('prospects').update({
                        'enrichment_status': 'failed',
                        'updated_at': datetime.now().isoformat()
                    }).eq('id', prospect_id).execute()
                except:
                    pass
                    
        except Exception as e:
            print(f"Background enrichment error for prospect {prospect_id}: {e}")
            # Set status to failed on general error
            try:
                supabase_client.table('prospects').update({
                    'enrichment_status': 'failed',
                    'updated_at': datetime.now().isoformat()
                }).eq('id', prospect_id).execute()
            except:
                pass
    
    # Start enrichment in background thread
    thread = threading.Thread(target=enrich_task)
    thread.daemon = True
    thread.start()


@app.route('/companies')
def companies():
    """All companies page"""
    if not is_token_valid():
        return redirect(url_for('index'))
    
    return render_template('all_companies.html')


@app.route('/company-categories') 
def company_categories_page():
    """Company categories page"""
    if not is_token_valid():
        return redirect(url_for('index'))
    
    return render_template('companies.html')


@app.route('/crm')
def crm():
    """CRM data page"""
    if not is_token_valid():
        return redirect(url_for('index'))
    
    return render_template('crm.html')


@app.route('/company-statuses')
def company_statuses():
    """Company statuses page"""
    if not is_token_valid():
        return redirect(url_for('index'))
    
    return render_template('company_statuses.html')


@app.route('/accountancy')
def accountancy():
    """Accountancy data page"""
    if not is_token_valid():
        return redirect(url_for('index'))
    
    return render_template('accountancy.html')


@app.route('/sales')
def sales():
    """Sales data page"""
    if not is_token_valid():
        return redirect(url_for('index'))
    
    return render_template('sales.html')


@app.route('/products')
def products():
    """Products data page"""
    if not is_token_valid():
        return redirect(url_for('index'))
    
    return render_template('products.html')


@app.route('/visualize')
def visualize():
    """Data visualization playground"""
    if not is_token_valid():
        return redirect(url_for('index'))
    return render_template('visualize.html')

# Delivery Orders API endpoints
@app.route('/api/delivery-orders')
def api_delivery_orders():
    """Get delivery orders"""
    if not is_token_valid():
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Add pagination parameters to get all results
    params = {
        'per_page': 100,  # Request up to 100 items per page
        'page': 1
    }
    
    # Get query parameters for filtering and ordering
    if request.args.get('filter_by_created_since'):
        params['filter_by_created_since'] = request.args.get('filter_by_created_since')
    if request.args.get('filter_by_updated_since'):
        params['filter_by_updated_since'] = request.args.get('filter_by_updated_since')
    if request.args.get('filter_by_customer'):
        params['filter_by_customer'] = request.args.get('filter_by_customer')
    if request.args.get('filter_by_supplier'):
        params['filter_by_supplier'] = request.args.get('filter_by_supplier')
    if request.args.get('filter_by_date'):
        params['filter_by_date'] = request.args.get('filter_by_date')
    if request.args.get('filter_by_status'):
        params['filter_by_status'] = request.args.get('filter_by_status')
    if request.args.get('order_by_date'):
        params['order_by_date'] = request.args.get('order_by_date')
    if request.args.get('order_by_customer'):
        params['order_by_customer'] = request.args.get('order_by_customer')
    
    data, error = make_paginated_api_request('/api/public/v1/crm/delivery-orders', params=params)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify(data)


@app.route('/api/delivery-orders/<int:order_id>')
def api_delivery_order(order_id):
    """Get specific delivery order"""
    if not is_token_valid():
        return jsonify({'error': 'Not authenticated'}), 401
    
    data, error = make_api_request(f'/api/public/v1/crm/delivery-orders/{order_id}')
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify(data)


@app.route('/api/companies/<int:company_id>/orders')
def api_company_orders(company_id):
    """Get delivery orders for a specific company (as customer)"""
    if not is_token_valid():
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Add pagination parameters and customer filter
    params = {
        'per_page': 100,
        'page': 1,
        'filter_by_customer': company_id
    }
    
    # Add additional filters from query parameters
    if request.args.get('filter_by_created_since'):
        params['filter_by_created_since'] = request.args.get('filter_by_created_since')
    if request.args.get('filter_by_updated_since'):
        params['filter_by_updated_since'] = request.args.get('filter_by_updated_since')
    if request.args.get('filter_by_date'):
        params['filter_by_date'] = request.args.get('filter_by_date')
    if request.args.get('filter_by_status'):
        params['filter_by_status'] = request.args.get('filter_by_status')
    
    data, error = make_paginated_api_request('/api/public/v1/crm/delivery-orders', params=params)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify(data)


@app.route('/api/companies/<int:company_id>/supplier-orders')
def api_company_supplier_orders(company_id):
    """Get delivery orders where company is the supplier"""
    if not is_token_valid():
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Add pagination parameters and supplier filter
    params = {
        'per_page': 100,
        'page': 1,
        'filter_by_supplier': company_id
    }
    
    # Add additional filters from query parameters
    if request.args.get('filter_by_created_since'):
        params['filter_by_created_since'] = request.args.get('filter_by_created_since')
    if request.args.get('filter_by_updated_since'):
        params['filter_by_updated_since'] = request.args.get('filter_by_updated_since')
    if request.args.get('filter_by_date'):
        params['filter_by_date'] = request.args.get('filter_by_date')
    if request.args.get('filter_by_status'):
        params['filter_by_status'] = request.args.get('filter_by_status')
    
    data, error = make_paginated_api_request('/api/public/v1/crm/delivery-orders', params=params)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify(data)


@app.route('/orders')
def orders():
    """Delivery orders page"""
    if not is_token_valid():
        return redirect(url_for('index'))
    
    return render_template('orders.html')


# Pricing API endpoints
@app.route('/api/pricing/purchase-adjustments')
def api_purchase_price_adjustments():
    """Get purchase price adjustments"""
    if not is_token_valid():
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Add pagination parameters
    params = {
        'per_page': 100,
        'page': 1
    }
    
    # Get query parameters for filtering
    if request.args.get('filter_by_companies'):
        params['filter_by_companies'] = request.args.getlist('filter_by_companies')
    if request.args.get('filter_by_price_classes'):
        params['filter_by_price_classes'] = request.args.getlist('filter_by_price_classes')
    if request.args.get('filter_by_product'):
        params['filter_by_product'] = request.args.get('filter_by_product')
    if request.args.get('filter_by_is_active'):
        params['filter_by_is_active'] = request.args.get('filter_by_is_active').lower() == 'true'
    
    data, error = make_paginated_api_request('/api/public/v1/trade/price-adjustments-items/purchase', params=params)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify(data)


@app.route('/api/pricing/sales-adjustments')
def api_sales_price_adjustments():
    """Get sales price adjustments"""
    if not is_token_valid():
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Add pagination parameters
    params = {
        'per_page': 100,
        'page': 1
    }
    
    # Get query parameters for filtering
    if request.args.get('filter_by_companies'):
        params['filter_by_companies'] = request.args.getlist('filter_by_companies')
    if request.args.get('filter_by_price_classes'):
        params['filter_by_price_classes'] = request.args.getlist('filter_by_price_classes')
    if request.args.get('filter_by_product'):
        params['filter_by_product'] = request.args.get('filter_by_product')
    if request.args.get('filter_by_is_active'):
        params['filter_by_is_active'] = request.args.get('filter_by_is_active').lower() == 'true'
    
    data, error = make_paginated_api_request('/api/public/v1/trade/price-adjustments-items/sales', params=params)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify(data)


@app.route('/api/companies/<int:company_id>/pricing')
def api_company_pricing(company_id):
    """Get pricing adjustments for a specific company"""
    if not is_token_valid():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        # Get purchase price adjustments for this company
        purchase_params = {
            'per_page': 100,
            'page': 1,
            'filter_by_companies[]': company_id
        }
        purchase_data, purchase_error = make_paginated_api_request('/api/public/v1/trade/price-adjustments-items/purchase', params=purchase_params)
        
        # Get sales price adjustments for this company
        sales_params = {
            'per_page': 100,
            'page': 1,
            'filter_by_companies[]': company_id
        }
        sales_data, sales_error = make_paginated_api_request('/api/public/v1/trade/price-adjustments-items/sales', params=sales_params)
        
        result = {
            'purchase_adjustments': purchase_data if not purchase_error else {'result': {'data': []}},
            'sales_adjustments': sales_data if not sales_error else {'result': {'data': []}}
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# CRM API endpoints
@app.route('/api/crm/companies', methods=['GET'])
def api_get_crm_companies():
    """Get companies from Duano CRM"""
    if not is_token_valid():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        companies = _get_crm_companies_data()
        return jsonify({'companies': companies})
            
    except Exception as e:
        print(f"Error fetching CRM companies: {e}")
        return jsonify({'error': str(e)}), 500

def _get_crm_companies_data():
    """Helper function to get CRM companies data"""
    # Get query parameters
    search = request.args.get('search', '')
    status_filter = request.args.get('status', '')
    
    # Build Duano API URL
    duano_base_url = session.get('duano_base_url', DOUANO_CONFIG['base_url'])
    url = f"{duano_base_url}/api/public/v1/crm/crm-companies"
    
    # Build query parameters
    params = {
        'filter_by_created_since': '2023-01-01',
        'filter_by_updated_since': '2023-01-01'
    }
    
    if status_filter:
        params['filter_by_crm_company_statuses'] = status_filter
    
    # Get access token
    access_token = session.get('access_token')
    if not access_token:
        raise Exception('Not authenticated with Duano')
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json'
    }
    
    response = requests.get(url, params=params, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        companies = data.get('result', {}).get('data', [])
        
        # Apply search filter on frontend data if needed
        if search:
            search_lower = search.lower()
            companies = [
                company for company in companies
                if (search_lower in company.get('name', '').lower() or
                    search_lower in company.get('address_line1', '').lower() or
                    search_lower in company.get('city', '').lower() or
                    any(search_lower in str(v).lower() for v in company.values() if v))
            ]
        
        return companies
    else:
        raise Exception(f'Failed to fetch CRM data: {response.status_code}')

@app.route('/api/crm/search-vat/<vat_number>', methods=['GET'])
def api_search_company_by_vat(vat_number):
    """Search company in CRM by VAT number"""
    if not is_token_valid():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        # Get all companies
        companies = _get_crm_companies_data()
        
        # Search for VAT number in company data
        vat_clean = vat_number.replace('BE', '').replace('.', '').replace(' ', '')
        matching_companies = []
        
        for company in companies:
            # Check various fields that might contain VAT
            company_str = str(company).lower()
            if vat_clean.lower() in company_str or vat_number.lower() in company_str:
                matching_companies.append(company)
        
        return jsonify({'companies': matching_companies, 'vat_searched': vat_number})
        
    except Exception as e:
        print(f"Error searching company by VAT: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/crm/search-director/<director_name>', methods=['GET'])
def api_search_director_in_crm(director_name):
    """Search for a director in CRM companies"""
    if not is_token_valid():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        # Get all companies
        companies = _get_crm_companies_data()
        
        # Search for director name in company data
        director_lower = director_name.lower()
        matching_companies = []
        
        for company in companies:
            # Search in all company fields for the director name
            company_str = str(company).lower()
            if director_lower in company_str:
                matching_companies.append(company)
        
        return jsonify({'companies': matching_companies, 'director_searched': director_name})
        
    except Exception as e:
        print(f"Error searching director in CRM: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)
