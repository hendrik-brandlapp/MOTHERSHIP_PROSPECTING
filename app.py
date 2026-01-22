"""
DOUANO Frontend - Flask Web Application
Beautiful interface to interact with your DOUANO data
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import requests
import urllib.parse
import secrets
import os
import time
import threading
import atexit
from datetime import datetime, timedelta
import json
import math
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

try:
    from duano_client import DuanoClient
except Exception:
    DuanoClient = None

try:
    from google import genai
    from google.genai import types
except Exception:
    genai = None
    types = None

try:
    from whatsapp_service import WhatsAppService
except Exception:
    WhatsAppService = None

try:
    from automation_engine import AutomationEngine, AUTOMATION_TEMPLATES
except Exception:
    AutomationEngine = None
    AUTOMATION_TEMPLATES = []

try:
    from route_optimizer import optimize_trip_route
except Exception:
    try:
        # Fallback to simple optimizer if ortools is not available
        from simple_route_optimizer import optimize_trip_route
    except Exception:
        optimize_trip_route = None

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

# Gemini API configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
gemini_client = None
if GEMINI_API_KEY and genai is not None:
    try:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception:
        gemini_client = None

# Supabase configuration
SUPABASE_URL = "https://gpjoypslbrpvnhqzvacc.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imdwam95cHNsYnJwdm5ocXp2YWNjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTM3MDQxNTAsImV4cCI6MjA2OTI4MDE1MH0.u0hGzIKziSPz2i576NhuyCetV6_iQwCoft7FIjDJCiI"
supabase_client = None
if create_client and Client:
    try:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    except Exception:
        supabase_client = None

# Initialize Automation Engine
automation_engine = None
if supabase_client and AutomationEngine:
    try:
        automation_engine = AutomationEngine(supabase_client)
    except Exception:
        automation_engine = None

# Background scheduler for time-based automations
automation_scheduler_running = False
automation_scheduler_thread = None

def run_automation_scheduler():
    """Background thread that processes time-based automations every 15 minutes"""
    global automation_scheduler_running
    while automation_scheduler_running:
        try:
            if automation_engine:
                result = automation_engine.process_time_based_queue()
                if result.get('processed', 0) > 0:
                    print(f"[Automation Scheduler] Processed {result['processed']} time-based automations")
        except Exception as e:
            print(f"[Automation Scheduler] Error: {e}")

        # Sleep for 15 minutes (check every 30 seconds to allow graceful shutdown)
        for _ in range(30):
            if not automation_scheduler_running:
                break
            time.sleep(30)

def start_automation_scheduler():
    """Start the background automation scheduler"""
    global automation_scheduler_running, automation_scheduler_thread
    if automation_engine and not automation_scheduler_running:
        automation_scheduler_running = True
        automation_scheduler_thread = threading.Thread(target=run_automation_scheduler, daemon=True)
        automation_scheduler_thread.start()
        print("[Automation Scheduler] Started background processing for time-based automations")

def stop_automation_scheduler():
    """Stop the background automation scheduler"""
    global automation_scheduler_running
    automation_scheduler_running = False
    print("[Automation Scheduler] Stopped")

# Register cleanup on app shutdown
atexit.register(stop_automation_scheduler)

# Start scheduler if automation engine is available
if automation_engine:
    start_automation_scheduler()

# DOUANO API Configuration
DOUANO_CONFIG = {
    'client_id': os.getenv('DUANO_CLIENT_ID', '3'),
    'client_secret': os.getenv('DUANO_CLIENT_SECRET', 'KBPJZ11EwPjAmEUKFWDoXGQaDdMRPFES2P6VCxEC'),
    'base_url': os.getenv('DUANO_API_BASE_URL', 'https://yugen.douano.com'),
    'auth_url': 'https://yugen.douano.com/authorize',
    'token_url': 'https://yugen.douano.com/oauth/token',
    'redirect_uri': os.getenv('DUANO_REDIRECT_URI', 'https://mothership-prospecting.onrender.com/oauth/callback')
}


def is_token_valid():
    """Check if the stored DUANO token is valid (for admin)"""
    if 'access_token' not in session:
        return False
    
    if 'token_expires_at' not in session:
        return False
    
    expires_at = datetime.fromisoformat(session['token_expires_at'])
    return datetime.now() < expires_at - timedelta(minutes=5)


def is_logged_in():
    """Check if user is logged in (either as admin or sales rep)"""
    # Sales rep login
    if session.get('user_role') == 'sales_rep':
        return True
    # Admin login via DUANO
    if is_token_valid():
        return True
    return False


def is_admin():
    """Check if current user is admin"""
    return session.get('user_role') == 'admin' and is_token_valid()


def get_current_user():
    """Get current user info"""
    return {
        'name': session.get('user_name', 'Unknown'),
        'role': session.get('user_role', 'unknown'),
        'is_admin': is_admin()
    }


def get_douano_client():
    """Get initialized Douano client with current session token"""
    if not DuanoClient:
        return None
    
    if not is_logged_in():
        return None
    
    try:
        client = DuanoClient(
            client_id=DOUANO_CONFIG['client_id'],
            client_secret=DOUANO_CONFIG['client_secret'],
            base_url=DOUANO_CONFIG['base_url'],
            redirect_uri=DOUANO_CONFIG['redirect_uri']
        )
        
        # Set the access token from session
        client.set_access_token(
            access_token=session['access_token'],
            token_type=session.get('token_type', 'Bearer'),
            expires_in=3600
        )
        
        return client
    except Exception as e:
        print(f"Error initializing Douano client: {e}")
        return None


def make_api_request(endpoint, method='GET', params=None):
    """Make authenticated API request to DOUANO"""
    if not is_logged_in():
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
    """Home page - check if user is logged in (either as admin or sales rep)"""
    # Check if logged in as sales rep
    if session.get('user_role') == 'sales_rep':
        return render_template('home.html', now=datetime.now())

    # Check if logged in as admin (via DUANO)
    if is_token_valid():
        session['user_role'] = 'admin'
        session['user_name'] = 'Admin'
        return render_template('home.html', now=datetime.now())

    # Not logged in - show login page
    return render_template('login.html')


@app.route('/login-sales-rep', methods=['POST'])
def login_sales_rep():
    """Login as a sales rep (no DUANO auth required)"""
    name = request.form.get('name')
    
    if name not in ['Caitlin', 'Kesha', 'Django']:
        return redirect(url_for('index'))
    
    session['user_role'] = 'sales_rep'
    session['user_name'] = name
    session.permanent = True
    
    return redirect(url_for('index'))


@app.route('/admin-login')
def admin_login():
    """Redirect to DUANO OAuth for admin login"""
    return redirect(url_for('login'))


@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    return redirect(url_for('index'))


@app.route('/login')
def login():
    """Initiate OAuth2 login for admin"""
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


@app.route('/dashboard')
def dashboard():
    """Deprecated: redirect to simplified home"""
    if not is_logged_in():
        return redirect(url_for('index'))
    return redirect(url_for('index'))


@app.route('/api/company-categories')
def api_company_categories():
    """Get company categories"""
    if not is_logged_in():
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
    if not is_logged_in():
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
    if not is_logged_in():
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
    if not is_logged_in():
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
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    data, error = make_api_request(f'/api/public/v1/core/company-statuses/{status_id}')
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify(data)


@app.route('/api/accountancy/accounts')
def api_accountancy_accounts():
    """Get accountancy accounts"""
    if not is_logged_in():
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
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    data, error = make_api_request(f'/api/public/v1/accountancy/accounts/{account_id}')
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify(data)


@app.route('/api/accountancy/bookings')
def api_accountancy_bookings():
    """Get accountancy bookings with extensive filtering"""
    if not is_logged_in():
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
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    data, error = make_api_request(f'/api/public/v1/accountancy/bookings/{booking_id}')
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify(data)


@app.route('/api/companies')
def api_companies():
    """Get all companies (actual companies, not categories)"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get query parameters for filtering and ordering
    params = {
        'per_page': request.args.get('per_page', 100),
        'page': request.args.get('page', 1),
        'include': 'country,company_status,sales_price_class,company_categories'  # Try to include related data
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

    # Check for sales_since_year filter
    sales_since_year = request.args.get('sales_since_year')
    
    if sales_since_year:
        # Get all companies first
        data, error = make_paginated_api_request('/api/public/v1/core/companies', params=params)
        
        if error:
            return jsonify({'error': error}), 500
        
        companies = data.get('result', {}).get('data', [])
        
        # Get invoices since the specified year
        invoice_params = {
            'per_page': 1000,
            'page': 1,
            'filter_by_start_date': f'{sales_since_year}-01-01'
        }
        
        invoices_data, invoice_error = make_paginated_api_request('/api/public/v1/trade/sales-invoices', params=invoice_params)
        
        if invoice_error:
            return jsonify({'error': f'Error fetching invoices: {invoice_error}'}), 500
        
        invoices = invoices_data.get('result', {}).get('data', [])
        
        # Create a set of company IDs that have invoices
        company_ids_with_sales = set()
        for invoice in invoices:
            company = invoice.get('company')
            if company and isinstance(company, dict):
                company_id = company.get('id')
                if company_id:
                    company_ids_with_sales.add(company_id)
        
        # Filter companies to only those with sales
        filtered_companies = [c for c in companies if c.get('id') in company_ids_with_sales]
        
        # Return filtered results
        data['result']['data'] = filtered_companies
        return jsonify(data)
    
    data, error = make_paginated_api_request('/api/public/v1/core/companies', params=params)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify(data)


@app.route('/api/companies/<int:company_id>')
def api_company(company_id):
    """Get specific company"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    data, error = make_api_request(f'/api/public/v1/core/companies/{company_id}')
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify(data)


@app.route('/api/sales-invoices')
def api_sales_invoices():
    """Get sales invoices with enhanced transport method data"""
    if not is_logged_in():
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
    
    # Get sales invoices
    data, error = make_paginated_api_request('/api/public/v1/trade/sales-invoices', params=params)
    
    if error:
        return jsonify({'error': error}), 500
    
    # If transport method enhancement is requested, enhance with purchase order data
    if request.args.get('transport_method') or request.args.get('enhance_transport') or 'transport' in request.path.lower():
        try:
            # Get purchase orders to link transport methods
            purchase_params = {
                'per_page': 100,
                'page': 1
            }
            
            # Apply same date filters to purchase orders
            if request.args.get('filter_by_start_date'):
                purchase_params['filter_by_start_date'] = request.args.get('filter_by_start_date')
            if request.args.get('filter_by_end_date'):
                purchase_params['filter_by_end_date'] = request.args.get('filter_by_end_date')
            
            purchase_data, purchase_error = make_paginated_api_request('/api/public/v1/trade/purchase-orders', params=purchase_params)
            
            if not purchase_error and purchase_data:
                purchase_orders = purchase_data.get('result', {}).get('data', [])
                
                # Create a mapping of company to transport method (with date preference)
                transport_lookup = {}
                company_transport_methods = {}  # Fallback: just by company
                
                # Debug: Log first few purchase orders
                print(f"DEBUG: Found {len(purchase_orders)} purchase orders")
                for i, order in enumerate(purchase_orders[:3]):
                    print(f"DEBUG: Purchase order {i+1}: ID={order.get('id')}, Company={order.get('company', {}).get('name')}, Date={order.get('date')}, Transport={order.get('transport_method', {}).get('name') if order.get('transport_method') else 'None'}")
                
                for order in purchase_orders:
                    if order.get('transport_method') and order.get('company'):
                        company_id = order['company'].get('id')
                        order_date = order.get('date', '')[:10]  # Get just the date part
                        transport_method = order['transport_method']
                        
                        # Create lookup key: company_id + date (preferred)
                        lookup_key = f"{company_id}_{order_date}"
                        transport_lookup[lookup_key] = transport_method
                        
                        # Also store by company only (fallback)
                        if company_id not in company_transport_methods:
                            company_transport_methods[company_id] = transport_method
                
                print(f"DEBUG: Created {len(transport_lookup)} date-specific lookups and {len(company_transport_methods)} company fallbacks")
                
                # Enhance sales invoices with transport method data
                invoices = data.get('result', {}).get('data', [])
                enhanced_count = 0
                
                # Debug: Log first few invoices
                print(f"DEBUG: Found {len(invoices)} sales invoices")
                for i, invoice in enumerate(invoices[:3]):
                    print(f"DEBUG: Sales invoice {i+1}: ID={invoice.get('id')}, Company={invoice.get('company', {}).get('name')}, Date={invoice.get('date')}")
                
                for invoice in invoices:
                    if invoice.get('company'):
                        company_id = invoice['company'].get('id')
                        invoice_date = invoice.get('date', invoice.get('created_at', ''))
                        if invoice_date:
                            invoice_date = invoice_date[:10]  # Get just the date part
                        
                        # Try exact date match first
                        lookup_key = f"{company_id}_{invoice_date}"
                        if lookup_key in transport_lookup:
                            invoice['transport_method'] = transport_lookup[lookup_key]
                            enhanced_count += 1
                            print(f"DEBUG: Enhanced invoice {invoice.get('id')} with exact date match: {transport_lookup[lookup_key].get('name')}")
                        # Fallback to any transport method for this company
                        elif company_id in company_transport_methods:
                            invoice['transport_method'] = company_transport_methods[company_id]
                            enhanced_count += 1
                            print(f"DEBUG: Enhanced invoice {invoice.get('id')} with company fallback: {company_transport_methods[company_id].get('name')}")
                        else:
                            print(f"DEBUG: No transport method found for invoice {invoice.get('id')}, company {company_id}, date {invoice_date}")
                
                print(f"DEBUG: Enhanced {enhanced_count} out of {len(invoices)} invoices")
                
                # Add debug info
                data['debug'] = {
                    'purchase_orders_loaded': len(purchase_orders),
                    'transport_methods_found': len(transport_lookup),
                    'company_fallbacks': len(company_transport_methods),
                    'invoices_enhanced': enhanced_count,
                    'total_invoices': len(invoices)
                }
        
        except Exception as e:
            # Don't fail the whole request if transport method enhancement fails
            data['debug'] = {'transport_enhancement_error': str(e)}
    
    return jsonify(data)

@app.route('/api/sales-orders')
def api_sales_orders():
    """Get sales orders - these already have transport methods built-in!"""
    print("DEBUG: /api/sales-orders endpoint called")
    print(f"DEBUG: Session keys: {list(session.keys())}")
    print(f"DEBUG: is_token_valid(): {is_token_valid()}")
    
    if not is_logged_in():
        print("DEBUG: Not authenticated, returning 401")
        return jsonify({'error': 'Not authenticated'}), 401
    
    print("DEBUG: Authentication passed, setting up parameters")
    
    # Add pagination parameters to get all results
    params = {
        'per_page': 100,  # Request up to 100 items per page
        'page': 1
    }
    
    print(f"DEBUG: Initial params: {params}")
    
    # Get query parameters for filtering and ordering
    # Handle date filtering - if API doesn't support proper ranges, we'll filter on frontend
    start_date = request.args.get('filter_by_start_date')
    end_date = request.args.get('filter_by_end_date')
    
    # Store for frontend filtering as backup
    frontend_start_date = start_date
    frontend_end_date = end_date
    
    # Try to use the transport method filter at API level if possible
    transport_method_filter = request.args.get('transport_method')
    
    # Remove per_page limit to get ALL orders, then filter properly
    params['per_page'] = 1000  # Get more orders to match CSV export
    
    # Try the most basic approach - get all recent orders and filter frontend
    if start_date:
        params['filter_by_created_since'] = start_date
        print(f"DEBUG: Using filter_by_created_since={start_date}")
    
    print(f"DEBUG: Requesting up to {params['per_page']} orders to match CSV export completeness")
    print(f"DEBUG: Will filter on frontend for transport method: {transport_method_filter}")
    print(f"DEBUG: Will filter on frontend for date range: {frontend_start_date} to {frontend_end_date}")
    
    # Direct parameter passthrough
    if request.args.get('filter_by_created_since'):
        params['filter_by_created_since'] = request.args.get('filter_by_created_since')
    if request.args.get('filter_by_updated_since'):
        params['filter_by_updated_since'] = request.args.get('filter_by_updated_since')
    if request.args.get('filter_by_company'):
        params['filter_by_company'] = request.args.get('filter_by_company')
    if request.args.get('filter_by_status'):
        params['filter_by_status'] = request.args.get('filter_by_status')
    if request.args.get('order_by_date'):
        params['order_by_date'] = request.args.get('order_by_date')
    
    # DO NOT pass transport_method to API - we'll filter on frontend
    # The Duano sales-orders API doesn't support transport method filtering
    transport_method_filter = request.args.get('transport_method')
    if transport_method_filter:
        print(f"DEBUG: Transport method filter '{transport_method_filter}' will be applied on frontend, not API")
    
    print(f"DEBUG: Final params before API call: {params}")
    print("DEBUG: Calling make_paginated_api_request for sales-orders...")
    
    # Get sales orders directly - they already have transport methods!
    data, error = make_paginated_api_request('/api/public/v1/trade/sales-orders', params=params)
    
    print(f"DEBUG: API call completed. Error: {error}")
    print(f"DEBUG: Data type: {type(data)}")
    if data and isinstance(data, dict):
        result = data.get('result', {})
        orders_count = len(result.get('data', [])) if result.get('data') else 0
        print(f"DEBUG: Found {orders_count} orders")
    
    if error:
        print(f"DEBUG: Returning error: {error}")
        return jsonify({'error': error}), 500
    
    # Sales orders already have transport_method, company, date, address - enhance with full address details!
    orders = data.get('result', {}).get('data', [])
    
    # Apply frontend date filtering FIRST to reduce the number of orders we need to process
    original_count = len(orders)
    if frontend_start_date or frontend_end_date:
        filtered_orders = []
        for order in orders:
            order_date = order.get('date') or order.get('created_at', '')[:10]  # Get date part only
            
            # Check if order is within date range
            include_order = True
            if frontend_start_date and order_date < frontend_start_date:
                include_order = False
            if frontend_end_date and order_date > frontend_end_date:
                include_order = False
                
            if include_order:
                filtered_orders.append(order)
        
        print(f"DEBUG: Frontend date filtering FIRST: {original_count} -> {len(filtered_orders)} orders")
        orders = filtered_orders
        data['result']['data'] = orders

    # Now enhance addresses only for the filtered orders
    enhanced_addresses = 0
    should_enhance = True  # Enhanced sales invoices with transport method data
    print(f"DEBUG: Enhancing addresses for {len(orders)} filtered orders (enhance_addresses={request.args.get('enhance_addresses')})")
    
    if should_enhance:
        print("DEBUG: Enhancing orders with real street address details...")
        
        # Collect unique address IDs to get actual street addresses
        address_ids = set()
        for order in orders:
            if order.get('address') and order['address'].get('id'):
                address_ids.add(order['address']['id'])
        
        print(f"DEBUG: Found {len(address_ids)} unique addresses to fetch")
        
        # Fetch real address details for each unique address ID
        address_lookup = {}
        for address_id in address_ids:
            try:
                # Try different endpoints for addresses
                endpoints_to_try = [
                    f'/api/public/v1/core/addresses/{address_id}',
                    f'/api/public/v1/crm/addresses/{address_id}',
                    f'/api/public/v1/logistics/addresses/{address_id}',
                    f'/api/public/v1/addresses/{address_id}'
                ]
                
                address_found = False
                for endpoint in endpoints_to_try:
                    print(f"DEBUG: Trying {endpoint} for address {address_id}")
                    address_data, address_error = make_api_request(endpoint)
                    if not address_error and address_data and address_data.get('result'):
                        address_lookup[address_id] = address_data['result']
                        street = address_data['result'].get('street', address_data['result'].get('address_line1', 'No street'))
                        city = address_data['result'].get('city', 'No city')
                        print(f"DEBUG: SUCCESS! Fetched address {address_id} from {endpoint}: {street}, {city}")
                        address_found = True
                        break
                    else:
                        print(f"DEBUG: Failed {endpoint}: {address_error}")
                
                if not address_found:
                    print(f"DEBUG: Could not fetch address {address_id} from any endpoint")
                    
            except Exception as e:
                print(f"DEBUG: Error fetching address {address_id}: {str(e)}")
        
        print(f"DEBUG: Successfully fetched {len(address_lookup)} real address details")
        
        # Enhance orders with real street address details
        for order in orders:
            if order.get('address') and order['address'].get('id'):
                address_id = order['address']['id']
                if address_id in address_lookup:
                    # Add the real address details
                    real_address = address_lookup[address_id]
                    order['address']['street_details'] = real_address
                    enhanced_addresses += 1
                    street = real_address.get('street', real_address.get('address_line1', ''))
                    city = real_address.get('city', '')
                    print(f"DEBUG: Enhanced order {order.get('id')} with real address: {street}, {city}")
                else:
                    # If we can't get real address details, at least add a note
                    print(f"DEBUG: No address details found for address {address_id} (order {order.get('id')})")
                    order['address']['street_details'] = {
                        'note': f'Address details not available for ID {address_id}',
                        'original_name': order['address'].get('name', 'Unknown')
                    }
    
    # Add debug info about what we found
    transport_methods_found = 0
    addresses_found = 0
    
    for order in orders:
        if order.get('transport_method'):
            transport_methods_found += 1
        if order.get('address'):
            addresses_found += 1
    
    data['debug'] = {
        'total_orders': len(orders),
        'original_orders_before_date_filter': original_count,
        'date_range_requested': f"{frontend_start_date} to {frontend_end_date}",
        'transport_methods_found': transport_methods_found,
        'addresses_found': addresses_found,
        'addresses_enhanced': enhanced_addresses,
        'source': 'Direct from Sales Orders API with efficient filtering + address enhancement',
        'transport_filter_note': 'Transport method filtering happens on frontend, not API level'
    }
    
    print(f"DEBUG: Returning response with {len(orders)} orders")
    return jsonify(data)

@app.route('/api/debug/auth-status')
def debug_auth_status():
    """Debug endpoint to check authentication status"""
    return jsonify({
        'is_authenticated': is_token_valid(),
        'session_keys': list(session.keys()),
        'has_access_token': 'access_token' in session,
        'token_expires_at': session.get('token_expires_at'),
        'current_time': time.time()
    })

@app.route('/api/debug/address/<int:address_id>')
def debug_address(address_id):
    """Debug endpoint to test address API directly"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    print(f"DEBUG: Testing address API for address ID {address_id}")
    
    # Try different possible endpoints for addresses
    endpoints_to_try = [
        f'/api/public/v1/core/addresses/{address_id}',
        f'/api/public/v1/crm/addresses/{address_id}',
        f'/api/public/v1/logistics/addresses/{address_id}',
        f'/api/public/v1/addresses/{address_id}'
    ]
    
    results = {}
    for endpoint in endpoints_to_try:
        print(f"DEBUG: Trying endpoint: {endpoint}")
        data, error = make_api_request(endpoint)
        results[endpoint] = {
            'success': error is None,
            'error': error,
            'data': data.get('result') if data and not error else None
        }
        if not error and data:
            print(f"DEBUG: SUCCESS with {endpoint}")
            break
        else:
            print(f"DEBUG: FAILED with {endpoint}: {error}")
    
    return jsonify({
        'address_id': address_id,
        'results': results
    })

@app.route('/api/debug/raw-sales-orders')
def debug_raw_sales_orders():
    """Debug endpoint to see raw sales orders data like CSV export"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get raw sales orders with minimal filtering to compare with CSV
    params = {
        'per_page': 1000,
        'filter_by_created_since': '2025-08-01',  # Get recent orders
        'order_by_date': 'desc'
    }
    
    print(f"DEBUG: Fetching raw sales orders with params: {params}")
    
    data, error = make_paginated_api_request('/api/public/v1/trade/sales-orders', params=params)
    
    if error:
        return jsonify({'error': error}), 500
    
    orders = data.get('result', {}).get('data', [])
    
    # Count transport methods like in CSV
    transport_stats = {}
    shippr_orders = []
    
    for order in orders:
        transport_method = 'Unknown'
        if order.get('transport_method') and order['transport_method'].get('name'):
            transport_method = order['transport_method']['name']
        
        transport_stats[transport_method] = transport_stats.get(transport_method, 0) + 1
        
        # Collect SHIPPR orders specifically
        if 'SHIPPR' in transport_method:
            shippr_orders.append({
                'id': order.get('id'),
                'date': order.get('date'),
                'company': order.get('company', {}).get('name'),
                'transport_method': transport_method,
                'address_id': order.get('address', {}).get('id'),
                'address_name': order.get('address', {}).get('name')
            })
    
    return jsonify({
        'total_orders': len(orders),
        'transport_method_stats': transport_stats,
        'shippr_orders_count': len(shippr_orders),
        'shippr_orders_sample': shippr_orders[:10],  # First 10 SHIPPR orders
        'sample_order_structure': orders[0] if orders else None,
        'comparison_with_csv': {
            'csv_shows': '200+ SHIPPR orders',
            'api_shows': f'{len(shippr_orders)} SHIPPR orders',
            'possible_issue': 'Date filtering or API pagination limits'
        }
    })

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
    if not is_logged_in():
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
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    data, error = make_api_request(f'/api/public/v1/trade/sales-invoices/{invoice_id}')
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify(data)


@app.route('/api/companies/<int:company_id>/sales')
def api_company_sales(company_id):
    """Get sales data for a specific company"""
    if not is_logged_in():
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
    if not is_logged_in():
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
    if not is_logged_in():
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
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    data, error = make_api_request(f'/api/public/v1/core/composed-product-items/{item_id}')
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify(data)


@app.route('/api/products/hierarchy')
def api_products_hierarchy():
    """Get product hierarchy with composed products and their components"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        # Get all composed product items
        params = {
            'per_page': 1000,  # Get all items to build hierarchy
            'page': 1
        }
        
        data, error = make_paginated_api_request('/api/public/v1/core/composed-product-items', params=params)
        
        if error:
            print(f"❌ Error fetching composed products: {error}")
            # Return empty structure if API fails
            return jsonify({
                'hierarchy': [],
                'all_products': [],
                'stats': {
                    'total_composed_products': 0,
                    'total_unique_products': 0,
                    'total_components': 0
                }
            })
    except Exception as e:
        print(f"❌ Exception in products hierarchy: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'hierarchy': [],
            'all_products': [],
            'stats': {
                'total_composed_products': 0,
                'total_unique_products': 0,
                'total_components': 0
            }
        })
    
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
    if not is_logged_in():
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
    if not is_logged_in():
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
    if not is_logged_in():
        return redirect(url_for('index'))
    return render_template('prospecting.html', google_maps_api_key=GOOGLE_MAPS_API_KEY)


@app.route('/prospecting-map')
def prospecting_map():
    """Unified Prospecting Map with Google Maps and Places search"""
    if not is_logged_in():
        return redirect(url_for('index'))
    return render_template('prospecting_map.html', google_maps_api_key=GOOGLE_MAPS_API_KEY)


@app.route('/api/places/search', methods=['POST'])
def api_places_search():
    """Search Google Places API within map bounds"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        data = request.get_json()
        query = data.get('query', '')
        bounds = data.get('bounds', {})

        if not query:
            return jsonify({'error': 'Search query is required'}), 400

        # Calculate center and radius from bounds
        if bounds:
            north = bounds.get('north', 50.85)
            south = bounds.get('south', 50.85)
            east = bounds.get('east', 4.35)
            west = bounds.get('west', 4.35)

            lat = (north + south) / 2
            lng = (east + west) / 2
            location = f"{lat},{lng}"

            # Calculate radius based on bounds (distance from center to edge)
            # Using Haversine approximation: 1 degree lat ≈ 111km, 1 degree lng ≈ 111km * cos(lat)
            lat_diff = (north - south) / 2
            lng_diff = (east - west) / 2
            lat_dist = lat_diff * 111000  # meters
            lng_dist = lng_diff * 111000 * math.cos(math.radians(lat))  # meters

            # Use the larger dimension to cover visible area (max 50km)
            radius = min(max(lat_dist, lng_dist), 50000)
            radius = max(radius, 500)  # Minimum 500m radius
        else:
            location = "50.8503,4.3517"  # Belgium default
            radius = 15000

        # Use Google Places Text Search API
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {
            'query': query,
            'location': location,
            'radius': int(radius),
            'key': GOOGLE_MAPS_API_KEY
        }

        response = requests.get(url, params=params)
        places_data = response.json()

        return jsonify(places_data)

    except Exception as e:
        print(f"Places search error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/planning')
def planning():
    """Planning page with Mapbox map visualization"""
    if not is_logged_in():
        return redirect(url_for('index'))
    
    # Mapbox API key
    mapbox_api_key = "pk.eyJ1IjoiaGVuZHJpa3l1Z2VuIiwiYSI6ImNtY24zZnB4YTAwNTYybnMzNGVpemZxdGEifQ.HIpLMTGycSiEsf7ytxaSJg"
    
    return render_template('planning.html', 
                         mapbox_api_key=mapbox_api_key,
                         google_maps_api_key=GOOGLE_MAPS_API_KEY)

@app.route('/tasks')
def tasks():
    """Task Management Dashboard"""
    if not is_logged_in():
        return redirect(url_for('index'))
    return render_template('tasks.html')


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
    if not is_logged_in():
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
    if not is_logged_in():
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
    if not is_logged_in():
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
    if not is_logged_in():
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
    if not is_logged_in():
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
    if not is_logged_in():
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
        
        # Prepare prospect data with new pipeline fields
        # Only include core fields that definitely exist in the prospects table
        prospect_data = {
            'name': data['name'],
            'address': data.get('address', ''),
            'website': data.get('website', ''),
            'status': data.get('status', 'new_leads'),
            'enriched_data': data.get('enriched_data', {}),
            'tags': tags,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }

        # Add Google Place ID if provided (from Places search)
        if data.get('google_place_id'):
            prospect_data['google_place_id'] = data['google_place_id']

        # Add search query if provided
        if data.get('search_query'):
            prospect_data['search_query'] = data['search_query']
        
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
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401

    if not supabase_client:
        return jsonify({'error': 'Supabase not configured'}), 500

    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Get current prospect state before update (for automation triggers)
        old_prospect = None
        if 'status' in data:
            try:
                old_result = supabase_client.table('prospects').select('*').eq('id', prospect_id).execute()
                if old_result.data:
                    old_prospect = old_result.data[0]
            except Exception as e:
                print(f"Error fetching old prospect state: {e}")

        # Prepare update data
        update_data = {
            'updated_at': datetime.now().isoformat()
        }
        
        # Add allowed fields - only include fields that definitely exist in prospects table
        allowed_fields = [
            'status', 'name', 'address', 'website', 'enriched_data', 'notes'
        ]
        
        # Add optional fields that might exist (these won't cause errors if they don't exist)
        optional_fields = [
            'region', 'contact_later_date', 'contact_later_reason',
            'unqualified_reason', 'unqualified_details', 'next_action'
        ]
        for field in allowed_fields:
            if field in data:
                update_data[field] = data[field]
        
        # Special handling for contact_later status
        if data.get('status') == 'contact_later' and 'contact_later_date' in data:
            # Create a task for follow-up
            task_data = {
                'prospect_id': prospect_id,
                'task_type': 'contact_later',
                'title': f"Follow up with {data.get('name', 'prospect')}",
                'description': data.get('contact_later_reason', 'Scheduled follow-up contact'),
                'scheduled_date': data['contact_later_date'],
                'created_at': datetime.now().isoformat()
            }
            
            try:
                supabase_client.table('prospect_tasks').insert(task_data).execute()
            except Exception as task_error:
                print(f"Failed to create task for contact_later: {task_error}")
                # Don't fail the main update if task creation fails
        
        # Update in Supabase
        result = supabase_client.table('prospects').update(update_data).eq('id', prospect_id).execute()
        
        if result.data:
            updated_prospect = result.data[0]
            
            # Create automated tasks based on status change
            if 'status' in data:
                create_automated_tasks(prospect_id, data['status'], updated_prospect)

                # Trigger no-code automations for status change
                if automation_engine and old_prospect:
                    old_status = old_prospect.get('status')
                    new_status = data['status']
                    if old_status != new_status:
                        try:
                            current_user = session.get('user_name', 'system')
                            automation_engine.evaluate_status_change(
                                prospect_id=prospect_id,
                                old_status=old_status,
                                new_status=new_status,
                                prospect_data=updated_prospect,
                                triggered_by=current_user
                            )
                        except Exception as auto_error:
                            print(f"Automation engine error: {auto_error}")
                            # Don't fail the main update if automation fails

            return jsonify({
                'prospect': updated_prospect,
                'message': 'Prospect updated successfully'
            })
        else:
            return jsonify({'error': 'Prospect not found'}), 404
            
    except Exception as e:
        return jsonify({'error': f'Failed to update prospect: {str(e)}'}), 500


@app.route('/api/prospects/<prospect_id>', methods=['DELETE'])
def api_delete_prospect(prospect_id):
    """Delete a prospect from Supabase"""
    if not is_logged_in():
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


# Pipeline Enhancement API Routes

@app.route('/api/prospects/pipeline-stats', methods=['GET'])
def api_get_pipeline_stats():
    """Get prospect pipeline statistics"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401

    if not supabase_client:
        return jsonify({'error': 'Supabase not configured'}), 500

    try:
        # Calculate stats manually - more reliable than database function
        prospects_result = supabase_client.table('prospects').select('status').execute()
        prospects = prospects_result.data or []

        stats = {}
        total = len(prospects)

        for prospect in prospects:
            status = prospect.get('status', 'new_leads')
            if status:  # Only count non-null statuses
                stats[status] = stats.get(status, 0) + 1

        # Convert to percentage and sort by pipeline order
        pipeline_order = {
            'new_leads': 1,
            'visited': 2,
            'first_contact': 3,
            'meeting_planned': 4,
            'follow_up': 5,
            'customer': 6,
            'ex_customer': 7,
            'contact_later': 8,
            'unqualified': 9
        }

        formatted_stats = {}
        for status, count in stats.items():
            formatted_stats[status] = {
                'count': count,
                'percentage': round((count / total * 100), 2) if total > 0 else 0
            }

        return jsonify({
            'stats': formatted_stats,
            'total': total
        })

    except Exception as e:
        print(f"Error getting pipeline stats: {e}")
        return jsonify({'error': f'Failed to get pipeline stats: {str(e)}'}), 500


@app.route('/api/dashboard', methods=['GET'])
def api_get_dashboard():
    """Get aggregated dashboard data for the home page"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401

    if not supabase_client:
        return jsonify({'error': 'Supabase not configured'}), 500

    try:
        today = datetime.now().date()
        today_str = today.isoformat()
        current_user = session.get('user_name', '')

        dashboard_data = {
            'tasks': {
                'today': [],
                'overdue': [],
                'upcoming': [],
                'total_today': 0,
                'total_overdue': 0,
                'completed_today': 0
            },
            'trips': {
                'today': [],
                'upcoming': [],
                'total_stops_today': 0
            },
            'pipeline': {
                'total': 0,
                'by_status': {}
            },
            'alerts': [],
            'recent_activity': []
        }

        # Get tasks for current user
        try:
            tasks_result = supabase_client.table('sales_tasks').select('''
                *,
                prospects:prospect_id (id, name, status, address)
            ''').or_(f'assigned_to.eq.{current_user},assigned_to.is.null').execute()

            if tasks_result.data:
                for task in tasks_result.data:
                    due_date = task.get('due_date', '')
                    if due_date:
                        due = datetime.fromisoformat(due_date.replace('Z', '+00:00')).date() if 'T' in due_date else datetime.strptime(due_date, '%Y-%m-%d').date()

                        task_info = {
                            'id': task.get('id'),
                            'title': task.get('title'),
                            'task_type': task.get('task_type'),
                            'priority': task.get('priority', 2),
                            'status': task.get('status'),
                            'due_date': due_date,
                            'prospect': task.get('prospects')
                        }

                        if task.get('status') == 'completed':
                            if due == today:
                                dashboard_data['tasks']['completed_today'] += 1
                        elif due < today:
                            dashboard_data['tasks']['overdue'].append(task_info)
                            dashboard_data['tasks']['total_overdue'] += 1
                        elif due == today:
                            dashboard_data['tasks']['today'].append(task_info)
                            dashboard_data['tasks']['total_today'] += 1
                        elif due <= today + timedelta(days=7):
                            dashboard_data['tasks']['upcoming'].append(task_info)

                # Sort by priority (high first) then due date
                for key in ['today', 'overdue', 'upcoming']:
                    dashboard_data['tasks'][key].sort(key=lambda x: (-x.get('priority', 2), x.get('due_date', '')))
                    dashboard_data['tasks'][key] = dashboard_data['tasks'][key][:5]  # Limit to 5
        except Exception as e:
            print(f"Error fetching tasks for dashboard: {e}")

        # Get trips for current user
        try:
            trips_result = supabase_client.table('trips').select('''
                *,
                trip_stops (id, prospect_id, stop_order)
            ''').eq('created_by', current_user).gte('trip_date', today_str).order('trip_date').limit(10).execute()

            if trips_result.data:
                for trip in trips_result.data:
                    trip_date = trip.get('trip_date', '')
                    if trip_date:
                        trip_d = datetime.strptime(trip_date, '%Y-%m-%d').date() if isinstance(trip_date, str) else trip_date

                        trip_info = {
                            'id': trip.get('id'),
                            'name': trip.get('name'),
                            'trip_date': trip_date,
                            'status': trip.get('status'),
                            'stop_count': len(trip.get('trip_stops', []))
                        }

                        if trip_d == today:
                            dashboard_data['trips']['today'].append(trip_info)
                            dashboard_data['trips']['total_stops_today'] += trip_info['stop_count']
                        else:
                            dashboard_data['trips']['upcoming'].append(trip_info)

                dashboard_data['trips']['upcoming'] = dashboard_data['trips']['upcoming'][:3]
        except Exception as e:
            print(f"Error fetching trips for dashboard: {e}")

        # Get pipeline stats
        try:
            prospects_result = supabase_client.table('prospects').select('status').execute()
            if prospects_result.data:
                dashboard_data['pipeline']['total'] = len(prospects_result.data)
                for prospect in prospects_result.data:
                    status = prospect.get('status', 'new_leads')
                    if status:
                        dashboard_data['pipeline']['by_status'][status] = dashboard_data['pipeline']['by_status'].get(status, 0) + 1
        except Exception as e:
            print(f"Error fetching pipeline for dashboard: {e}")

        # Generate alerts
        if dashboard_data['tasks']['total_overdue'] > 0:
            dashboard_data['alerts'].append({
                'type': 'warning',
                'icon': 'exclamation-triangle',
                'message': f"You have {dashboard_data['tasks']['total_overdue']} overdue task(s)",
                'link': '/tasks?filter=overdue'
            })

        if dashboard_data['trips']['today']:
            stops = dashboard_data['trips']['total_stops_today']
            dashboard_data['alerts'].append({
                'type': 'info',
                'icon': 'route',
                'message': f"Route planned for today with {stops} stop(s)",
                'link': '/trips'
            })

        # Get recent automation executions
        try:
            if automation_engine:
                exec_result = supabase_client.table('automation_executions').select('''
                    *,
                    automation_rules:automation_rule_id (name)
                ''').order('executed_at', desc=True).limit(5).execute()

                if exec_result.data:
                    for ex in exec_result.data:
                        dashboard_data['recent_activity'].append({
                            'type': 'automation',
                            'message': f"Automation '{ex.get('automation_rules', {}).get('name', 'Unknown')}' executed",
                            'status': ex.get('status'),
                            'time': ex.get('executed_at')
                        })
        except Exception as e:
            print(f"Error fetching automation executions: {e}")

        return jsonify({
            'success': True,
            'data': dashboard_data
        })

    except Exception as e:
        print(f"Error getting dashboard data: {e}")
        return jsonify({'error': f'Failed to get dashboard data: {str(e)}'}), 500


@app.route('/api/prospect-tasks', methods=['GET'])
def api_get_prospect_tasks():
    """Get prospect tasks/reminders"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    if not supabase_client:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        # Get query parameters
        prospect_id = request.args.get('prospect_id')
        completed = request.args.get('completed')
        overdue_only = request.args.get('overdue_only') == 'true'
        
        # Build query
        query = supabase_client.table('prospect_tasks').select('''
            *,
            prospects:prospect_id (
                id,
                name,
                status
            )
        ''')
        
        if prospect_id:
            query = query.eq('prospect_id', prospect_id)
        
        if completed is not None:
            query = query.eq('completed', completed.lower() == 'true')
        
        if overdue_only:
            from datetime import date
            query = query.lt('scheduled_date', date.today().isoformat())
            query = query.eq('completed', False)
        
        result = query.order('scheduled_date').execute()
        
        return jsonify({
            'tasks': result.data,
            'count': len(result.data)
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch tasks: {str(e)}'}), 500


@app.route('/api/prospect-tasks', methods=['POST'])
def api_create_prospect_task():
    """Create a new prospect task"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    if not supabase_client:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        required_fields = ['prospect_id', 'title', 'scheduled_date']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        task_data = {
            'prospect_id': data['prospect_id'],
            'task_type': data.get('task_type', 'contact_later'),
            'title': data['title'],
            'description': data.get('description', ''),
            'scheduled_date': data['scheduled_date'],
            'created_at': datetime.now().isoformat()
        }
        
        result = supabase_client.table('prospect_tasks').insert(task_data).execute()
        
        if result.data:
            return jsonify({
                'task': result.data[0],
                'message': 'Task created successfully'
            }), 201
        else:
            return jsonify({'error': 'Failed to create task'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to create task: {str(e)}'}), 500


@app.route('/api/prospect-tasks/<task_id>', methods=['PATCH'])
def api_update_prospect_task(task_id):
    """Update a prospect task"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    if not supabase_client:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        update_data = {
            'updated_at': datetime.now().isoformat()
        }
        
        allowed_fields = ['title', 'description', 'scheduled_date', 'completed', 'completed_at']
        for field in allowed_fields:
            if field in data:
                update_data[field] = data[field]
        
        # Set completed_at when marking as completed
        if data.get('completed') and 'completed_at' not in data:
            update_data['completed_at'] = datetime.now().isoformat()
        
        result = supabase_client.table('prospect_tasks').update(update_data).eq('id', task_id).execute()
        
        if result.data:
            return jsonify({
                'task': result.data[0],
                'message': 'Task updated successfully'
            })
        else:
            return jsonify({'error': 'Task not found'}), 404
            
    except Exception as e:
        return jsonify({'error': f'Failed to update task: {str(e)}'}), 500


@app.route('/api/unqualified-reasons', methods=['GET'])
def api_get_unqualified_reasons():
    """Get predefined unqualified reasons"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    if not supabase_client:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        result = supabase_client.table('unqualified_reasons').select('*').order('sort_order').execute()
        
        return jsonify({
            'reasons': result.data,
            'count': len(result.data)
        })
        
    except Exception as e:
        # Return default reasons if table doesn't exist yet
        default_reasons = [
            {'reason_code': 'no_fridge_space', 'reason_text': 'No Fridge space & no place for extra fridge'},
            {'reason_code': 'no_fit', 'reason_text': 'No fit'},
            {'reason_code': 'not_convinced', 'reason_text': 'Not convinced by product'},
            {'reason_code': 'too_expensive', 'reason_text': 'Too expensive'},
            {'reason_code': 'prefers_competition', 'reason_text': 'Likes competition more'},
            {'reason_code': 'unclear', 'reason_text': 'Unclear'}
        ]
        
        return jsonify({
            'reasons': default_reasons,
            'count': len(default_reasons),
            'note': 'Using default reasons. Run migration to create unqualified_reasons table.'
        })


# COMPREHENSIVE TASK MANAGEMENT API ENDPOINTS

@app.route('/api/tasks', methods=['GET'])
def api_get_tasks():
    """Get tasks with filtering and sorting options"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    if not supabase_client:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        # Get query parameters
        status = request.args.get('status')
        priority = request.args.get('priority')
        task_type = request.args.get('task_type')
        category = request.args.get('category')
        assigned_to = request.args.get('assigned_to')
        due_date = request.args.get('due_date')
        prospect_id = request.args.get('prospect_id')
        overdue_only = request.args.get('overdue_only') == 'true'
        upcoming_days = request.args.get('upcoming_days')
        
        # Build query with prospect information
        query = supabase_client.table('sales_tasks').select('''
            *,
            prospects:prospect_id (
                id,
                name,
                status,
                address
            )
        ''')
        
        # Apply filters
        if status:
            query = query.eq('status', status)
        if priority:
            query = query.eq('priority', int(priority))
        if task_type:
            query = query.eq('task_type', task_type)
        if category:
            query = query.eq('category', category)
        if assigned_to:
            query = query.eq('assigned_to', assigned_to)
        if prospect_id:
            query = query.eq('prospect_id', prospect_id)
        if due_date:
            query = query.eq('due_date', due_date)
        if overdue_only:
            from datetime import date
            query = query.lt('due_date', date.today().isoformat())
            query = query.neq('status', 'completed')
        if upcoming_days:
            from datetime import date, timedelta
            end_date = date.today() + timedelta(days=int(upcoming_days))
            query = query.gte('due_date', date.today().isoformat())
            query = query.lte('due_date', end_date.isoformat())
        
        # IMPORTANT: Exclude long-term customer maintenance tasks from main task list
        # These should only appear in the calendar view
        query = query.neq('category', 'customer_maintenance')
        
        # Execute query with sorting
        result = query.order('due_date', desc=False).order('priority', desc=False).execute()
        
        return jsonify({
            'tasks': result.data,
            'count': len(result.data)
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch tasks: {str(e)}'}), 500


@app.route('/api/tasks', methods=['POST'])
def api_create_task():
    """Create a new task"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    if not supabase_client:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        required_fields = ['title']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Prepare task data
        task_data = {
            'title': data['title'],
            'description': data.get('description', ''),
            'task_type': data.get('task_type', 'general'),
            'category': data.get('category', 'sales'),
            'priority': data.get('priority', 3),
            'status': data.get('status', 'pending'),
            'due_date': data.get('due_date'),
            'due_time': data.get('due_time'),
            'scheduled_date': data.get('scheduled_date'),
            'scheduled_time': data.get('scheduled_time'),
            'estimated_duration': data.get('estimated_duration'),
            'prospect_id': data.get('prospect_id'),
            'assigned_to': data.get('assigned_to'),
            'created_by': data.get('created_by'),
            'progress_percentage': data.get('progress_percentage', 0),
            'notes': data.get('notes', ''),
            'tags': data.get('tags', []),
            'attachments': data.get('attachments', []),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        # Insert into Supabase
        result = supabase_client.table('sales_tasks').insert(task_data).execute()
        
        if result.data:
            return jsonify({
                'task': result.data[0],
                'message': 'Task created successfully'
            }), 201
        else:
            return jsonify({'error': 'Failed to create task'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to create task: {str(e)}'}), 500


@app.route('/api/tasks/<task_id>', methods=['GET'])
def api_get_task(task_id):
    """Get a specific task with full details"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    if not supabase_client:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        # Get task with prospect and comments
        task_result = supabase_client.table('sales_tasks').select('''
            *,
            prospects:prospect_id (
                id,
                name,
                status,
                address,
                enriched_data
            )
        ''').eq('id', task_id).execute()
        
        if not task_result.data:
            return jsonify({'error': 'Task not found'}), 404
        
        # Get task comments
        comments_result = supabase_client.table('task_comments').select('*').eq('task_id', task_id).order('created_at').execute()
        
        task = task_result.data[0]
        task['comments'] = comments_result.data
        
        return jsonify({
            'task': task
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch task: {str(e)}'}), 500


@app.route('/api/tasks/<task_id>', methods=['PATCH'])
def api_update_task(task_id):
    """Update a task"""
    if not is_logged_in():
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
        allowed_fields = [
            'title', 'description', 'task_type', 'category', 'priority', 'status',
            'due_date', 'due_time', 'scheduled_date', 'scheduled_time', 'estimated_duration',
            'prospect_id', 'assigned_to', 'progress_percentage', 'notes', 'tags', 'attachments',
            'completed_at'
        ]
        
        for field in allowed_fields:
            if field in data:
                update_data[field] = data[field]
        
        # Handle completion
        if data.get('status') == 'completed' and 'completed_at' not in data:
            update_data['completed_at'] = datetime.now().isoformat()
            update_data['progress_percentage'] = 100
        
        # Update in Supabase
        result = supabase_client.table('sales_tasks').update(update_data).eq('id', task_id).execute()
        
        if result.data:
            # Add comment for status changes
            if 'status' in data:
                comment_data = {
                    'task_id': task_id,
                    'comment': f"Status changed to {data['status']}",
                    'comment_type': 'status_change',
                    'created_by': data.get('updated_by', 'System'),
                    'created_at': datetime.now().isoformat()
                }
                supabase_client.table('task_comments').insert(comment_data).execute()
            
            return jsonify({
                'task': result.data[0],
                'message': 'Task updated successfully'
            })
        else:
            return jsonify({'error': 'Task not found'}), 404
            
    except Exception as e:
        return jsonify({'error': f'Failed to update task: {str(e)}'}), 500


@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def api_delete_task(task_id):
    """Delete a task"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    if not supabase_client:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        result = supabase_client.table('sales_tasks').delete().eq('id', task_id).execute()
        
        if result.data:
            return jsonify({'message': 'Task deleted successfully'})
        else:
            return jsonify({'error': 'Task not found'}), 404
            
    except Exception as e:
        return jsonify({'error': f'Failed to delete task: {str(e)}'}), 500


@app.route('/api/tasks/<task_id>/comments', methods=['POST'])
def api_add_task_comment(task_id):
    """Add a comment to a task"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    if not supabase_client:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        data = request.get_json()
        if not data or 'comment' not in data:
            return jsonify({'error': 'Comment text required'}), 400
        
        comment_data = {
            'task_id': task_id,
            'comment': data['comment'],
            'comment_type': data.get('comment_type', 'comment'),
            'created_by': data.get('created_by', 'User'),
            'created_at': datetime.now().isoformat()
        }
        
        result = supabase_client.table('task_comments').insert(comment_data).execute()
        
        if result.data:
            return jsonify({
                'comment': result.data[0],
                'message': 'Comment added successfully'
            }), 201
        else:
            return jsonify({'error': 'Failed to add comment'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to add comment: {str(e)}'}), 500


@app.route('/api/tasks/analytics', methods=['GET'])
def api_get_task_analytics():
    """Get task analytics and statistics"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    if not supabase_client:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        # Get basic task counts by status (excluding long-term customer maintenance tasks)
        tasks_result = supabase_client.table('sales_tasks').select('status, priority, task_type, category, due_date').neq('category', 'customer_maintenance').execute()
        tasks = tasks_result.data or []
        
        # Calculate analytics
        from datetime import date, timedelta
        today = date.today()
        
        analytics = {
            'total_tasks': len(tasks),
            'by_status': {},
            'by_priority': {},
            'by_type': {},
            'by_category': {},
            'overdue_count': 0,
            'due_today': 0,
            'due_this_week': 0,
            'completion_rate': 0
        }
        
        for task in tasks:
            # By status
            status = task.get('status', 'pending')
            analytics['by_status'][status] = analytics['by_status'].get(status, 0) + 1
            
            # By priority
            priority = task.get('priority', 3)
            analytics['by_priority'][f'priority_{priority}'] = analytics['by_priority'].get(f'priority_{priority}', 0) + 1
            
            # By type
            task_type = task.get('task_type', 'general')
            analytics['by_type'][task_type] = analytics['by_type'].get(task_type, 0) + 1
            
            # By category
            category = task.get('category', 'sales')
            analytics['by_category'][category] = analytics['by_category'].get(category, 0) + 1
            
            # Due date analytics
            if task.get('due_date'):
                due_date = datetime.strptime(task['due_date'], '%Y-%m-%d').date()
                if due_date < today and status != 'completed':
                    analytics['overdue_count'] += 1
                elif due_date == today:
                    analytics['due_today'] += 1
                elif due_date <= today + timedelta(days=7):
                    analytics['due_this_week'] += 1
        
        # Calculate completion rate
        completed = analytics['by_status'].get('completed', 0)
        if analytics['total_tasks'] > 0:
            analytics['completion_rate'] = round((completed / analytics['total_tasks']) * 100, 2)
        
        return jsonify(analytics)
        
    except Exception as e:
        return jsonify({'error': f'Failed to get analytics: {str(e)}'}), 500


@app.route('/api/task-templates', methods=['GET'])
def api_get_task_templates():
    """Get available task templates"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    if not supabase_client:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        result = supabase_client.table('task_templates').select('*').eq('is_active', True).order('name').execute()
        
        return jsonify({
            'templates': result.data,
            'count': len(result.data)
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch templates: {str(e)}'}), 500


@app.route('/api/tasks/upcoming', methods=['GET'])
def api_get_upcoming_tasks():
    """Get upcoming tasks for dashboard"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    if not supabase_client:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        days_ahead = int(request.args.get('days', 7))
        
        from datetime import date, timedelta
        end_date = date.today() + timedelta(days=days_ahead)
        
        result = supabase_client.table('sales_tasks').select('''
            *,
            prospects:prospect_id (
                id,
                name,
                status
            )
        ''').gte('due_date', date.today().isoformat()).lte('due_date', end_date.isoformat()).in_('status', ['pending', 'in_progress']).order('due_date').order('priority').execute()
        
        return jsonify({
            'tasks': result.data,
            'count': len(result.data),
            'days_ahead': days_ahead
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch upcoming tasks: {str(e)}'}), 500


@app.route('/api/tasks/calendar', methods=['GET'])
def api_get_tasks_calendar():
    """Get all tasks for calendar view, including far future ones"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    if not supabase_client:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        from datetime import date, timedelta
        
        # Get date range from query parameters
        start_date = request.args.get('start_date', date.today().isoformat())
        end_date = request.args.get('end_date', (date.today() + timedelta(days=365)).isoformat())
        
        # Get all tasks within date range, including prospect info
        result = supabase_client.table('sales_tasks').select('''
            *, 
            prospects:prospect_id (
                id,
                name,
                status
            )
        ''').gte('due_date', start_date).lte('due_date', end_date).order('due_date').execute()
        
        tasks = result.data or []
        
        # Group tasks by month for easier calendar display
        from collections import defaultdict
        tasks_by_month = defaultdict(list)
        
        for task in tasks:
            if task.get('due_date'):
                month_key = task['due_date'][:7]  # YYYY-MM format
                tasks_by_month[month_key].append(task)
        
        return jsonify({
            'tasks': tasks,
            'tasks_by_month': dict(tasks_by_month),
            'date_range': {
                'start': start_date,
                'end': end_date
            },
            'total_tasks': len(tasks)
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch calendar tasks: {str(e)}'}), 500


@app.route('/api/tasks/debug/<prospect_id>')
def api_debug_prospect_tasks(prospect_id):
    """Debug endpoint to see all tasks for a specific prospect"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    if not supabase_client:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        # Get all tasks for this prospect
        result = supabase_client.table('sales_tasks').select('*').eq('prospect_id', prospect_id).order('due_date').execute()
        
        # Get prospect info
        prospect_result = supabase_client.table('prospects').select('*').eq('id', prospect_id).execute()
        
        return jsonify({
            'prospect': prospect_result.data[0] if prospect_result.data else None,
            'tasks': result.data or [],
            'task_count': len(result.data or [])
        })
        
    except Exception as e:
        return jsonify({'error': f'Debug failed: {str(e)}'}), 500


def create_automated_tasks(prospect_id, new_status, prospect_data):
    """Create automated tasks based on prospect status changes"""
    try:
        from datetime import datetime, timedelta
        
        prospect_name = prospect_data.get('name', 'Unknown Prospect')
        tasks_to_create = []
        
        # Tasks after visit (when status changes to 'visited', 'first_contact', etc.)
        if new_status in ['visited', 'first_contact']:
            # 📧 Send Mail (immediate)
            tasks_to_create.append({
                'prospect_id': prospect_id,
                'title': f'📧 Send follow-up email to {prospect_name}',
                'description': 'Send personalized follow-up email with product information and next steps',
                'task_type': 'email',
                'category': 'follow_up',
                'priority': 2,  # Orange - within 7 days
                'due_date': (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
                'status': 'pending',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            })
            
            # 📥 Check for Reply (after 3 days)
            tasks_to_create.append({
                'prospect_id': prospect_id,
                'title': f'📥 Check for reply from {prospect_name}',
                'description': 'Follow up if no response received to initial email',
                'task_type': 'follow_up',
                'category': 'follow_up',
                'priority': 3,  # Green - not urgent
                'due_date': (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d'),
                'status': 'pending',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            })
            
            # 📞 Call task (after 5 days)
            tasks_to_create.append({
                'prospect_id': prospect_id,
                'title': f'📞 Call {prospect_name}',
                'description': 'Phone call to discuss their needs and schedule next meeting',
                'task_type': 'call',
                'category': 'follow_up',
                'priority': 2,  # Orange - within 7 days
                'due_date': (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d'),
                'status': 'pending',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            })
        
        # Customer follow-up flow
        elif new_status == 'customer':
            # After 1 month: "Hoe gaat het? Wat kan beter?"
            tasks_to_create.append({
                'prospect_id': prospect_id,
                'title': f'🔄 1-Month Check-in: {prospect_name}',
                'description': 'Contact customer: "Hoe gaat het? Wat kan beter?" - Gather feedback and identify improvement opportunities',
                'task_type': 'call',
                'category': 'customer_maintenance',  # Special category for long-term tasks
                'priority': 3,  # Green - not urgent
                'due_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
                'status': 'pending',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'is_automated': True
            })
            
            # After 3 months: Follow up
            tasks_to_create.append({
                'prospect_id': prospect_id,
                'title': f'🔄 3-Month Follow-up: {prospect_name}',
                'description': 'Quarterly check-in to ensure satisfaction and identify new opportunities',
                'task_type': 'call',
                'category': 'customer_maintenance',  # Special category for long-term tasks
                'priority': 3,  # Green - not urgent
                'due_date': (datetime.now() + timedelta(days=90)).strftime('%Y-%m-%d'),
                'status': 'pending',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'is_automated': True
            })
            
            # After 6 months: Regular check-in (will repeat every 6 months)
            tasks_to_create.append({
                'prospect_id': prospect_id,
                'title': f'🔄 6-Month Regular Check-in: {prospect_name}',
                'description': 'Semi-annual customer review and relationship maintenance (repeats every 6 months)',
                'task_type': 'meeting',
                'category': 'customer_maintenance',  # Special category for long-term tasks
                'priority': 3,  # Green - not urgent
                'due_date': (datetime.now() + timedelta(days=180)).strftime('%Y-%m-%d'),
                'status': 'pending',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'is_recurring': True,
                'recurring_interval_days': 180,  # Every 6 months
                'is_automated': True
            })
        
        # Create all tasks in database
        if tasks_to_create and supabase_client:
            for task in tasks_to_create:
                try:
                    result = supabase_client.table('sales_tasks').insert(task).execute()
                    if result.data:
                        print(f"✅ Created automated task: {task['title']}")
                    else:
                        print(f"❌ Failed to create task: {task['title']}")
                except Exception as task_error:
                    print(f"❌ Error creating task {task['title']}: {str(task_error)}")
                    
        print(f"🤖 Created {len(tasks_to_create)} automated tasks for {prospect_name} (status: {new_status})")
        
        # Return task creation summary for debugging
        return {
            'tasks_created': len(tasks_to_create),
            'task_titles': [task['title'] for task in tasks_to_create]
        }
        
    except Exception as e:
        print(f"❌ Error in create_automated_tasks: {str(e)}")
        # Don't fail the main operation if task creation fails


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


@app.route('/company-categories') 
def company_categories_page():
    """Company categories page"""
    if not is_logged_in():
        return redirect(url_for('index'))
    
    return render_template('companies.html')


@app.route('/crm')
def crm():
    """CRM data page"""
    if not is_logged_in():
        return redirect(url_for('index'))
    
    return render_template('crm.html')


@app.route('/company-statuses')
def company_statuses():
    """Company statuses page"""
    if not is_logged_in():
        return redirect(url_for('index'))
    
    return render_template('company_statuses.html')


@app.route('/accountancy')
def accountancy():
    """Accountancy data page"""
    if not is_logged_in():
        return redirect(url_for('index'))
    
    return render_template('accountancy.html')


@app.route('/sales')
def sales():
    """Sales data page"""
    if not is_logged_in():
        return redirect(url_for('index'))
    
    return render_template('sales.html')


@app.route('/sales-2025')
def sales_2025():
    """2025 Sales data extraction and management page"""
    if not is_logged_in():
        return redirect(url_for('index'))
    
    return render_template('sales_2025.html')


@app.route('/products')
def products():
    """Products data page"""
    if not is_logged_in():
        return redirect(url_for('index'))
    
    return render_template('products.html')


@app.route('/visualize')
def visualize():
    """Data visualization playground"""
    if not is_logged_in():
        return redirect(url_for('index'))
    return render_template('visualize.html')


@app.route('/maps-ai')
def maps_ai():
    """Maps AI with Gemini grounding"""
    if not is_logged_in():
        return redirect(url_for('index'))
    return render_template('maps_ai.html', google_maps_api_key=GOOGLE_MAPS_API_KEY)


@app.route('/api/maps-ai/chat', methods=['POST'])
def api_maps_ai_chat():
    """Chat with Maps AI using Gemini grounding"""
    if not is_logged_in():
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    if gemini_client is None:
        return jsonify({
            'success': False, 
            'error': 'Gemini API is not configured. Please set GEMINI_API_KEY in your environment variables.'
        }), 500
    
    try:
        data = request.get_json()
        message = data.get('message', '')
        location = data.get('location')
        history = data.get('history', [])
        
        if not message:
            return jsonify({'success': False, 'error': 'Message is required'}), 400
        
        # Build config with Google Maps grounding
        config_dict = {
            'tools': [types.Tool(google_maps=types.GoogleMaps())],
        }
        
        # Add location context if available
        if location and 'latitude' in location and 'longitude' in location:
            config_dict['tool_config'] = types.ToolConfig(
                retrieval_config=types.RetrievalConfig(
                    lat_lng=types.LatLng(
                        latitude=location['latitude'],
                        longitude=location['longitude']
                    )
                )
            )
        
        # Make API call to Gemini with Maps grounding
        response = gemini_client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=message,
            config=types.GenerateContentConfig(**config_dict)
        )
        
        # Extract response text
        response_text = response.text
        
        # Extract grounding sources if available
        sources = []
        if response.candidates and len(response.candidates) > 0:
            grounding = response.candidates[0].grounding_metadata
            if grounding and grounding.grounding_chunks:
                for chunk in grounding.grounding_chunks:
                    if hasattr(chunk, 'maps') and chunk.maps:
                        sources.append({
                            'title': chunk.maps.title,
                            'uri': chunk.maps.uri,
                            'place_id': getattr(chunk.maps, 'place_id', None)
                        })
        
        return jsonify({
            'success': True,
            'response': response_text,
            'sources': sources
        })
        
    except Exception as e:
        print(f"Error in Maps AI chat: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Error processing request: {str(e)}'
        }), 500


@app.route('/maps-ai-enhanced')
def maps_ai_enhanced():
    """Enhanced Maps AI with interactive map visualization"""
    if not is_logged_in():
        return redirect(url_for('index'))
    return render_template('maps_ai_enhanced.html', google_maps_api_key=GOOGLE_MAPS_API_KEY)


@app.route('/api/maps-ai/chat-enhanced', methods=['POST'])
def api_maps_ai_chat_enhanced():
    """Enhanced chat with agentic map features and place details"""
    if not is_logged_in():
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    if gemini_client is None:
        return jsonify({
            'success': False, 
            'error': 'Gemini API is not configured. Please set GEMINI_API_KEY in your environment variables.'
        }), 500
    
    try:
        data = request.get_json()
        message = data.get('message', '')
        location = data.get('location')
        history = data.get('history', [])
        
        if not message:
            return jsonify({'success': False, 'error': 'Message is required'}), 400
        
        # Build config with Google Maps grounding
        config_dict = {
            'tools': [types.Tool(google_maps=types.GoogleMaps())],
        }
        
        # Add location context if available
        if location and 'latitude' in location and 'longitude' in location:
            config_dict['tool_config'] = types.ToolConfig(
                retrieval_config=types.RetrievalConfig(
                    lat_lng=types.LatLng(
                        latitude=location['latitude'],
                        longitude=location['longitude']
                    )
                )
            )
        
        # Make API call to Gemini with Maps grounding
        response = gemini_client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=message,
            config=types.GenerateContentConfig(**config_dict)
        )
        
        # Extract response text
        response_text = response.text
        
        # Extract place details from grounding metadata
        places = []
        place_ids = []
        
        if response.candidates and len(response.candidates) > 0:
            grounding = response.candidates[0].grounding_metadata
            if grounding and grounding.grounding_chunks:
                for chunk in grounding.grounding_chunks:
                    if hasattr(chunk, 'maps') and chunk.maps:
                        place_id = getattr(chunk.maps, 'place_id', None)
                        if place_id and place_id not in place_ids:
                            place_ids.append(place_id)
        
        # Fetch detailed place information using Google Places API
        # This would require implementing a Google Places API call
        # For now, we'll extract basic info from the grounding metadata
        if place_ids and GOOGLE_MAPS_API_KEY:
            try:
                # Fetch place details for visualization
                for place_id in place_ids[:5]:  # Limit to 5 places
                    place_details_url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&key={GOOGLE_MAPS_API_KEY}&fields=name,formatted_address,geometry,rating,user_ratings_total,photos,opening_hours,vicinity"
                    place_response = requests.get(place_details_url, timeout=5)
                    
                    if place_response.status_code == 200:
                        place_data = place_response.json()
                        if place_data.get('status') == 'OK':
                            result = place_data['result']
                            place_info = {
                                'place_id': place_id,
                                'name': result.get('name', ''),
                                'formatted_address': result.get('formatted_address', ''),
                                'vicinity': result.get('vicinity', ''),
                                'rating': result.get('rating'),
                                'user_ratings_total': result.get('user_ratings_total'),
                                'geometry': result.get('geometry'),
                                'opening_hours': result.get('opening_hours'),
                                'photo_url': None
                            }
                            
                            # Get photo URL if available
                            if result.get('photos') and len(result['photos']) > 0:
                                photo_reference = result['photos'][0].get('photo_reference')
                                if photo_reference:
                                    place_info['photo_url'] = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photo_reference={photo_reference}&key={GOOGLE_MAPS_API_KEY}"
                            
                            places.append(place_info)
            except Exception as e:
                print(f"Error fetching place details: {str(e)}")
        
        return jsonify({
            'success': True,
            'response': response_text,
            'places': places
        })
        
    except Exception as e:
        print(f"Error in enhanced Maps AI chat: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Error processing request: {str(e)}'
        }), 500


@app.route('/maps-ai-3d')
def maps_ai_3d():
    """3D Photorealistic Maps AI with agentic functionality"""
    if not is_logged_in():
        return redirect(url_for('index'))
    return render_template('maps_ai_3d.html', google_maps_api_key=GOOGLE_MAPS_API_KEY)


@app.route('/api/maps-ai/chat-3d', methods=['POST'])
def api_maps_ai_chat_3d():
    """Agentic chat with 3D map visualization and tool functions"""
    if not is_logged_in():
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    if gemini_client is None:
        return jsonify({
            'success': False, 
            'error': 'Gemini API is not configured. Please set GEMINI_API_KEY in your environment variables.'
        }), 500
    
    try:
        data = request.get_json()
        message = data.get('message', '')
        location = data.get('location')
        
        if not message:
            return jsonify({'success': False, 'error': 'Message is required'}), 400
        
        # Enhanced system instruction for agentic behavior
        system_instruction = """You are an intelligent location-aware AI assistant with access to photorealistic 3D maps.

Your capabilities:
1. **frameEstablishingShot**: Fly the camera to a specific location with custom range, tilt, and heading
2. **mapsGrounding**: Search for and display places using Google Maps data
3. **frameLocations**: Frame multiple locations on the map simultaneously

When users ask about places:
- Use mapsGrounding to find accurate, real-time information
- Automatically fly the camera to show the location
- Provide rich details about places (ratings, hours, address)

When users ask to "show", "take me to", or "explore" a location:
- Use frameEstablishingShot to fly there with an appropriate view
- Describe what they're seeing

Be conversational, helpful, and proactive in using visual tools to enhance the experience.
Always cite your sources from Google Maps."""
        
        # Build config with Google Maps grounding and system instruction
        config_dict = {
            'tools': [types.Tool(google_maps=types.GoogleMaps())],
            'system_instruction': system_instruction
        }
        
        # Add location context if available
        if location and 'lat' in location and 'lng' in location:
            config_dict['tool_config'] = types.ToolConfig(
                retrieval_config=types.RetrievalConfig(
                    lat_lng=types.LatLng(
                        latitude=location['lat'],
                        longitude=location['lng']
                    )
                )
            )
        
        # Make API call to Gemini with Maps grounding
        response = gemini_client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=message,
            config=types.GenerateContentConfig(**config_dict)
        )
        
        # Extract response text
        response_text = response.text
        
        # Process tool calls and extract locations
        tool_results = []
        places = []
        place_ids = []
        
        # Check if we need to execute tool functions based on the query
        # Parse common patterns for camera control
        lower_message = message.lower()
        
        # frameEstablishingShot patterns
        if any(word in lower_message for word in ['show me', 'take me to', 'fly to', 'go to', 'visit']):
            # Try to extract location from message or use grounding
            if response.candidates and len(response.candidates) > 0:
                grounding = response.candidates[0].grounding_metadata
                if grounding and grounding.grounding_chunks:
                    for chunk in grounding.grounding_chunks:
                        if hasattr(chunk, 'maps') and chunk.maps:
                            place_id = getattr(chunk.maps, 'place_id', None)
                            if place_id and place_id not in place_ids:
                                place_ids.append(place_id)
        
        # Extract place details from grounding metadata
        if response.candidates and len(response.candidates) > 0:
            grounding = response.candidates[0].grounding_metadata
            if grounding and grounding.grounding_chunks:
                for chunk in grounding.grounding_chunks:
                    if hasattr(chunk, 'maps') and chunk.maps:
                        place_id = getattr(chunk.maps, 'place_id', None)
                        if place_id and place_id not in place_ids:
                            place_ids.append(place_id)
        
        # Fetch detailed place information
        if place_ids and GOOGLE_MAPS_API_KEY:
            try:
                for place_id in place_ids[:5]:  # Limit to 5 places
                    place_details_url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&key={GOOGLE_MAPS_API_KEY}&fields=name,formatted_address,geometry,rating,user_ratings_total,opening_hours,vicinity"
                    place_response = requests.get(place_details_url, timeout=5)
                    
                    if place_response.status_code == 200:
                        place_data = place_response.json()
                        if place_data.get('status') == 'OK':
                            result = place_data['result']
                            places.append(result)
                            
                            # Create frameLocations tool result
                            if len(places) == 1:
                                # Single location - use frameEstablishingShot
                                tool_results.append({
                                    'type': 'frameEstablishingShot',
                                    'location': {
                                        'lat': result['geometry']['location']['lat'],
                                        'lng': result['geometry']['location']['lng']
                                    },
                                    'range': 500,
                                    'tilt': 65,
                                    'heading': 0
                                })
            except Exception as e:
                print(f"Error fetching place details: {str(e)}")
        
        # If we have multiple places, use frameLocations
        if len(places) > 1:
            locations = [{
                'lat': p['geometry']['location']['lat'],
                'lng': p['geometry']['location']['lng'],
                'name': p.get('name', ''),
                'rating': p.get('rating'),
                'user_ratings_total': p.get('user_ratings_total'),
                'formatted_address': p.get('formatted_address', ''),
                'vicinity': p.get('vicinity', ''),
                'opening_hours': p.get('opening_hours')
            } for p in places]
            
            tool_results = [{
                'type': 'frameLocations',
                'locations': locations
            }]
        
        return jsonify({
            'success': True,
            'response': response_text,
            'places': places,
            'tool_results': tool_results
        })
        
    except Exception as e:
        print(f"Error in 3D Maps AI chat: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Error processing request: {str(e)}'
        }), 500

# Delivery Orders API endpoints
@app.route('/api/delivery-orders')
def api_delivery_orders():
    """Get delivery orders"""
    if not is_logged_in():
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
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    data, error = make_api_request(f'/api/public/v1/crm/delivery-orders/{order_id}')
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify(data)


def extract_delivery_method_from_record(record, record_type=""):
    """Extract delivery method from a record (invoice or order) using multiple strategies"""
    delivery_method = None
    
    # Strategy 1: Direct field mapping - try various possible field names
    direct_fields = [
        'delivery_method', 'shipping_method', 'carrier', 'transport_method', 
        'logistics_method', 'delivery_mode', 'shipping_mode', 'transport_mode',
        'delivery_service', 'shipping_service', 'courier', 'logistics_provider',
        'transportmethode', 'transport_methode', 'vervoermethode', 'leveringsmethode'
    ]
    
    for field in direct_fields:
        if record.get(field):
            value = record[field]
            # Handle transport method objects like {'id': 13, 'name': 'Customer pick-up shop'}
            if isinstance(value, dict) and 'name' in value:
                return value['name']
            elif isinstance(value, dict) and 'id' in value:
                # Try to get name from transport method ID
                return f"Transport Method ID {value['id']}"
            else:
                value_str = str(value).strip()
                if value_str and value_str.lower() not in ['none', 'null', 'undefined', '', 'n/a']:
                    return value_str
    
    # Strategy 2: Check nested objects (like delivery_address, shipping_address)
    nested_objects = ['delivery_address', 'shipping_address', 'address', 'delivery_info', 'shipping_info']
    for obj_field in nested_objects:
        if isinstance(record.get(obj_field), dict):
            nested_obj = record[obj_field]
            for field in direct_fields:
                if nested_obj.get(field):
                    value = str(nested_obj[field]).strip()
                    if value and value.lower() not in ['none', 'null', 'undefined', '', 'n/a']:
                        return value
    
    # Strategy 3: Text analysis of description fields
    text_fields = [
        record.get('notes', ''),
        record.get('description', ''),
        record.get('reference', ''),
        record.get('buyer_reference', ''),
        record.get('internal_reference', ''),
        record.get('external_reference', ''),
        record.get('comment', ''),
        record.get('remarks', '')
    ]
    combined_text = ' '.join(str(field) for field in text_fields if field).lower()
    
    # Enhanced delivery keywords with variations
    delivery_keywords = {
        'yugen': 'Yugen',
        'shippr': 'Shippr', 
        'dhl': 'DHL',
        'ups': 'UPS',
        'fedex': 'FedEx',
        'postnl': 'PostNL',
        'post nl': 'PostNL',
        'dpd': 'DPD',
        'bpost': 'BPost',
        'gls': 'GLS',
        'tnt': 'TNT',
        'aramex': 'Aramex',
        'usps': 'USPS',
        'royal mail': 'Royal Mail',
        'la poste': 'La Poste',
        'colissimo': 'Colissimo',
        'chronopost': 'Chronopost'
    }
    
    for keyword, formatted_name in delivery_keywords.items():
        if keyword in combined_text:
            return formatted_name
    
    # Strategy 4: Pattern matching for common shipping patterns
    import re
    shipping_patterns = [
        r'shipped?\s+via\s+(\w+)',
        r'delivered?\s+by\s+(\w+)',
        r'courier[:\s]+(\w+)',
        r'carrier[:\s]+(\w+)',
        r'transport[:\s]+(\w+)'
    ]
    
    for pattern in shipping_patterns:
        match = re.search(pattern, combined_text, re.IGNORECASE)
        if match:
            return match.group(1).title()
    
    return None


@app.route('/api/analytics/deliveries')
def api_analytics_deliveries():
    """Comprehensive delivery analytics from purchase orders with transport methods.
    Query params:
      filter_by_delivery_methods: comma-separated list of delivery methods (e.g. "Yugen transport,External transportation - other")
      filter_by_start_date, filter_by_end_date: date range
      group_by: week|month (default: week)
    """
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401

    # Get query parameters
    delivery_methods = request.args.get('filter_by_delivery_methods', '').strip()
    start_date = request.args.get('filter_by_start_date')
    end_date = request.args.get('filter_by_end_date')
    group_by = request.args.get('group_by', 'week')
    
    # Collect all delivery data from multiple sources
    all_delivery_records = []
    data_sources = []
    
    # 1. Get addresses from core addresses endpoint
    try:
        params = {'per_page': 1000, 'page': 1}
        if start_date:
            params['filter_by_created_since'] = start_date
        if end_date:
            params['filter_by_updated_since'] = end_date
            
        raw, error = make_paginated_api_request('/api/public/v1/core/addresses', params=params)
        if not error:
            addresses = raw.get('result', {}).get('data', [])
            for addr in addresses:
                # Use the improved extraction logic
                delivery_method = extract_delivery_method_from_record(addr, "address")
                if not delivery_method:
                    delivery_method = 'Standard Delivery'
                
                # Format address
                address_parts = []
                for field in ['name', 'address_line1', 'address_line2', 'city', 'post_code', 'state']:
                    if addr.get(field):
                        address_parts.append(str(addr[field]))
                
                formatted_address = ', '.join(address_parts) if address_parts else 'Address not available'
                
                all_delivery_records.append({
                    'delivery_method': delivery_method,
                    'address': formatted_address,
                    'customer': addr.get('company', {}).get('name') if isinstance(addr.get('company'), dict) else 'Unknown',
                    'date': addr.get('created_at') or addr.get('updated_at'),
                    'amount': 0,  # Addresses don't have amounts
                    'id': addr.get('id'),
                    'source': 'addresses'
                })
            data_sources.append(f"Addresses: {len(addresses)} records")
    except Exception as e:
        data_sources.append(f"Addresses: Error - {str(e)}")
    
    # 2. Get sales invoices
    try:
        params = {'per_page': 1000, 'page': 1}
        if start_date:
            params['filter_by_start_date'] = start_date
        if end_date:
            params['filter_by_end_date'] = end_date
        
        raw, error = make_paginated_api_request('/api/public/v1/trade/sales-invoices', params=params)
        if not error:
            invoices = raw.get('result', {}).get('data', [])
            for invoice in invoices:
                # Use the improved extraction logic
                delivery_method = extract_delivery_method_from_record(invoice, "invoice")
                if not delivery_method:
                    delivery_method = 'Invoice Delivery'
                
                # Extract address
                address = 'Address from invoice'
                if invoice.get('company'):
                    company = invoice['company']
                    if isinstance(company, dict) and company.get('name'):
                        address = f"Delivered to {company['name']}"
                
                all_delivery_records.append({
                    'delivery_method': delivery_method,
                    'address': address,
                    'customer': invoice.get('buyer_name') or 'Unknown',
                    'date': invoice.get('date') or invoice.get('created_at'),
                    'amount': invoice.get('payable_amount_without_financial_discount') or invoice.get('balance') or 0,
                    'id': invoice.get('id'),
                    'source': 'invoices'
                })
            data_sources.append(f"Invoices: {len(invoices)} records")
    except Exception as e:
        data_sources.append(f"Invoices: Error - {str(e)}")
    
    # 3. Get purchase orders (PRIMARY SOURCE - contains transport_method field!)
    try:
        params = {'per_page': 500, 'page': 1}  # Limit to avoid timeout
        if start_date:
            params['filter_by_created_since'] = start_date
        if end_date:
            params['filter_by_updated_since'] = end_date
        
        raw, error = make_paginated_api_request('/api/public/v1/trade/purchase-orders', params=params)
        if not error:
            orders = raw.get('result', {}).get('data', [])
            transport_method_count = 0
            for order in orders:
                # Extract transport method directly from the transport_method field
                delivery_method = None
                if 'transport_method' in order and order['transport_method']:
                    transport_method_obj = order['transport_method']
                    if isinstance(transport_method_obj, dict) and 'name' in transport_method_obj:
                        delivery_method = transport_method_obj['name']
                        transport_method_count += 1
                
                # Fallback to extraction from other fields
                if not delivery_method:
                    delivery_method = extract_delivery_method_from_record(order, "order")
                
                if not delivery_method:
                    delivery_method = 'Purchase Order'
                
                # Extract address and company info
                address = 'Purchase order address'
                customer = 'Unknown'
                
                if order.get('address') and isinstance(order['address'], dict):
                    address = order['address'].get('name', 'Purchase order address')
                
                if order.get('company') and isinstance(order['company'], dict):
                    customer = order['company'].get('name', 'Unknown')
                
                all_delivery_records.append({
                    'delivery_method': delivery_method,
                    'address': address,
                    'customer': customer,
                    'date': order.get('date') or order.get('created_at'),
                    'amount': 0,  # Purchase orders typically don't have total amounts
                    'id': order.get('id'),
                    'source': 'purchase_orders',
                    'transaction_number': order.get('transaction_number'),
                    'status': order.get('status')
                })
            data_sources.append(f"Purchase Orders: {len(orders)} records, {transport_method_count} with transport methods")
    except Exception as e:
        data_sources.append(f"Purchase Orders: Error - {str(e)}")
    
    # Filter by delivery methods if specified
    if delivery_methods:
        method_list = [method.strip().lower() for method in delivery_methods.split(',') if method.strip()]
        filtered_records = []
        for record in all_delivery_records:
            if any(method in record['delivery_method'].lower() for method in method_list):
                filtered_records.append(record)
        all_delivery_records = filtered_records
    
    # Group records by time period and delivery method
    from datetime import datetime, timedelta
    
    def get_week_start(date_str):
        """Get the Monday of the week containing the given date"""
        if not date_str:
            return None
        try:
            date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            days_since_monday = date.weekday()
            monday = date - timedelta(days=days_since_monday)
            return monday.strftime('%Y-%m-%d')
        except:
            return None
    
    def get_month_start(date_str):
        """Get the first day of the month containing the given date"""
        if not date_str:
            return None
        try:
            date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return date.strftime('%Y-%m-01')
        except:
            return None
    
    # Aggregate data by delivery method and time period
    delivery_data = {}  # {delivery_method: {time_period: [addresses]}}
    
    for record in all_delivery_records:
        delivery_method = record['delivery_method']
        
        # Get time period
        if group_by == 'week':
            time_period = get_week_start(record['date'])
        else:  # month
            time_period = get_month_start(record['date'])
        
        if not time_period:
            continue
            
        # Initialize nested structure
        if delivery_method not in delivery_data:
            delivery_data[delivery_method] = {}
        if time_period not in delivery_data[delivery_method]:
            delivery_data[delivery_method][time_period] = []
        
        # Add record to the list
        delivery_data[delivery_method][time_period].append({
            'address': record['address'],
            'invoice_id': record['id'],
            'customer': record['customer'],
            'amount': record['amount'],
            'source': record['source']
        })
    
    # Format response for table display
    result = {
        'delivery_methods': list(delivery_data.keys()),
        'time_periods': [],
        'data': delivery_data,
        'summary': {},
        'data_sources': data_sources,
        'total_records': len(all_delivery_records)
    }
    
    # Get all unique time periods and sort them
    all_periods = set()
    for method_data in delivery_data.values():
        all_periods.update(method_data.keys())
    
    result['time_periods'] = sorted(list(all_periods))
    
    # Create summary statistics
    for method, periods in delivery_data.items():
        total_addresses = sum(len(addresses) for addresses in periods.values())
        total_amount = sum(
            sum(addr.get('amount', 0) for addr in addresses)
            for addresses in periods.values()
        )
        result['summary'][method] = {
            'total_addresses': total_addresses,
            'total_amount': total_amount,
            'time_periods_with_data': len(periods)
        }
    
    return jsonify({'result': result, 'total_records_processed': len(all_delivery_records)})


@app.route('/api/delivery-methods')
def api_delivery_methods():
    """Get available delivery methods from multiple sources including company transport methods, sales invoices and delivery orders"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    delivery_methods = set()
    api_errors = []
    data_sources = []
    
    try:
        # 1. Get transport methods from the official Duano API endpoint (PRIMARY SOURCE)
        official_data, official_error = make_paginated_api_request('/api/public/v1/core/transport-methods', params={'per_page': 100, 'page': 1})
        if not official_error and official_data:
            if 'result' in official_data and 'data' in official_data['result']:
                transport_methods = official_data['result']['data']
                for method in transport_methods:
                    # Extract name from transport method object
                    name = method.get('name') or method.get('label') or method.get('description')
                    if name and name.strip():
                        delivery_methods.add(name.strip())
                data_sources.append(f"Official transport methods: {len(transport_methods)} methods")
        else:
            if official_error:
                api_errors.append(f"Official transport methods error: {official_error}")
        
        # 2. Get delivery methods from sales invoices (limit to avoid timeout)
        params = {'per_page': 100, 'page': 1}
        raw, error = make_paginated_api_request('/api/public/v1/trade/sales-invoices', params=params)
        
        if error:
            api_errors.append(f"Sales invoices error: {error}")
        else:
            invoices = raw.get('result', {}).get('data', [])
            data_sources.append(f"Sales invoices: {len(invoices)} records processed")
            
            for invoice in invoices:
                method = extract_delivery_method_from_record(invoice, "invoice")
                if method:
                    delivery_methods.add(method)
        
        # 3. Get delivery methods from purchase orders (CORRECT ENDPOINT - contains transport_method field!)
        params = {'per_page': 100, 'page': 1}
        raw, error = make_paginated_api_request('/api/public/v1/trade/purchase-orders', params=params)
        if error:
            api_errors.append(f"Purchase orders error: {error}")
        else:
            orders = raw.get('result', {}).get('data', [])
            data_sources.append(f"Purchase orders: {len(orders)} records processed")
            
            for order in orders:
                method = extract_delivery_method_from_record(order, "order")
                if method:
                    delivery_methods.add(method)
        
        # Try additional endpoints that might contain delivery information
        additional_endpoints = [
            '/api/public/v1/core/addresses',
            '/api/public/v1/crm/crm-contact-persons'
        ]
        
        for endpoint in additional_endpoints:
            try:
                raw, error = make_paginated_api_request(endpoint, params={'per_page': 500, 'page': 1})
                if not error:
                    records = raw.get('result', {}).get('data', [])
                    endpoint_name = endpoint.split('/')[-1]
                    data_sources.append(f"{endpoint_name}: {len(records)} records processed")
                    
                    for record in records:
                        method = extract_delivery_method_from_record(record, endpoint_name)
                        if method:
                            delivery_methods.add(method)
            except Exception as e:
                api_errors.append(f"Error with {endpoint}: {str(e)}")
    
    except Exception as e:
        api_errors.append(f"General error: {str(e)}")
    
    # 4. Try to get transport methods from companies (transport methods stored with companies)
    try:
        company_data, company_error = make_api_request('/api/public/v1/core/companies', params={'per_page': 500, 'page': 1})
        if not company_error and company_data:
            companies = company_data.get('result', {}).get('data', [])
            company_transport_methods = 0
            
            for company in companies:
                # Look for transport method fields in company data
                for key, value in company.items():
                    if any(keyword in key.lower() for keyword in ['transport', 'delivery', 'shipping', 'carrier', 'method', 'logistics']):
                        if value and str(value).strip() and str(value).lower() not in ['none', 'null', '']:
                            delivery_methods.add(str(value).strip())
                            company_transport_methods += 1
            
            if company_transport_methods > 0:
                data_sources.append(f"Company transport methods: {company_transport_methods} methods from {len(companies)} companies")
    except Exception as e:
        api_errors.append(f"Company transport methods error: {str(e)}")
    
    # Always add common delivery methods to ensure they're available for visualization
    common_methods = [
        'Customer pick-up shop', 'Customer pick-up warehouse', 'External transportation - DPD',
        'External transportation - other', 'External transportation - SHIPPR', 'External transportation - TDL',
        'Yugen', 'Shippr', 'DHL', 'UPS', 'FedEx', 'PostNL', 'DPD', 'BPost', 'GLS',
        'TNT', 'Aramex', 'USPS', 'Royal Mail', 'La Poste', 'Colissimo', 'Chronopost',
        'Standard Delivery', 'Express Delivery', 'Overnight Delivery', 'Same Day Delivery'
    ]
    for method in common_methods:
        delivery_methods.add(method)
    
    # Remove empty/unknown values
    invalid_values = {'', 'Unknown', 'None', 'null', 'undefined', 'N/A', 'n/a', 'NULL'}
    delivery_methods = {method for method in delivery_methods if method not in invalid_values}
    
    # Convert to list of objects for dropdown
    result = [{'value': method, 'label': method} for method in sorted(delivery_methods)]
    
    response_data = {
        'result': result,
        'total_methods': len(delivery_methods),
        'data_sources': data_sources
    }
    if api_errors:
        response_data['warnings'] = api_errors
    
    return jsonify(response_data)


@app.route('/api/orders-by-delivery-method')
def api_orders_by_delivery_method():
    """Get count of purchase orders grouped by transport method for visualization"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get query parameters
    start_date = request.args.get('filter_by_start_date')
    end_date = request.args.get('filter_by_end_date')
    
    delivery_method_counts = {}
    total_orders = 0
    data_sources = []
    api_errors = []
    
    try:
        # Get purchase orders (PRIMARY SOURCE - contains transport_method field!)
        params = {'per_page': 1000, 'page': 1}
        if start_date:
            params['filter_by_created_since'] = start_date
        if end_date:
            params['filter_by_updated_since'] = end_date
            
        raw, error = make_paginated_api_request('/api/public/v1/trade/purchase-orders', params=params)
        if error:
            api_errors.append(f"Purchase orders error: {error}")
        else:
            orders = raw.get('result', {}).get('data', [])
            data_sources.append(f"Purchase orders: {len(orders)} records")
            
            for order in orders:
                # Extract transport method directly from the transport_method field
                delivery_method = None
                if 'transport_method' in order and order['transport_method']:
                    transport_method_obj = order['transport_method']
                    if isinstance(transport_method_obj, dict) and 'name' in transport_method_obj:
                        delivery_method = transport_method_obj['name']
                
                # Fallback to extraction from other fields
                if not delivery_method:
                    delivery_method = extract_delivery_method_from_record(order, "order")
                
                if not delivery_method:
                    delivery_method = 'Unknown Transport Method'
                
                if delivery_method not in delivery_method_counts:
                    delivery_method_counts[delivery_method] = {
                        'count': 0,
                        'total_amount': 0,
                        'orders': []
                    }
                
                delivery_method_counts[delivery_method]['count'] += 1
                total_orders += 1
                
                # Calculate total value from ordered items
                total_value = 0
                if order.get('ordered_items'):
                    for item in order['ordered_items']:
                        quantity = item.get('quantity', 0)
                        # Note: Purchase orders might not have prices, but we can count quantities
                        total_value += quantity
                
                delivery_method_counts[delivery_method]['total_amount'] += total_value
                
                # Store order details
                customer_name = 'Unknown'
                if order.get('company') and isinstance(order['company'], dict):
                    customer_name = order['company'].get('name', 'Unknown')
                
                delivery_method_counts[delivery_method]['orders'].append({
                    'id': order.get('id'),
                    'date': order.get('date') or order.get('created_at'),
                    'customer': customer_name,
                    'amount': total_value,
                    'reference': order.get('transaction_number', ''),
                    'status': order.get('status', ''),
                    'transport_method_id': transport_method_obj.get('id') if 'transport_method' in order and order['transport_method'] else None
                })
        
                
    except Exception as e:
        api_errors.append(f"General error: {str(e)}")
    
    # Format data for visualization
    chart_data = []
    for method, data in delivery_method_counts.items():
        chart_data.append({
            'delivery_method': method,
            'order_count': data['count'],
            'total_amount': data['total_amount'],
            'percentage': round((data['count'] / total_orders * 100), 2) if total_orders > 0 else 0,
            'sample_orders': data['orders'][:5]  # First 5 orders as examples
        })
    
    # Sort by order count descending
    chart_data.sort(key=lambda x: x['order_count'], reverse=True)
    
    response_data = {
        'result': chart_data,
        'summary': {
            'total_orders': total_orders,
            'total_delivery_methods': len(delivery_method_counts),
            'data_sources': data_sources
        }
    }
    
    if api_errors:
        response_data['warnings'] = api_errors
    
    return jsonify(response_data)



@app.route('/api/addresses')
def api_addresses():
    """Get all addresses from core addresses endpoint"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get query parameters for filtering
    params = {
        'per_page': request.args.get('per_page', 100),
        'page': request.args.get('page', 1)
    }
    
    # Add any filter parameters
    filter_params = [
        'filter_by_created_since', 'filter_by_updated_since', 
        'filter_by_is_active', 'filter_by_company', 'filter'
    ]
    
    for param in filter_params:
        if request.args.get(param):
            params[param] = request.args.get(param)
    
    data, error = make_paginated_api_request('/api/public/v1/core/addresses', params=params)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify(data)


@app.route('/api/debug/addresses')
def api_debug_addresses():
    """Debug endpoint to see actual address structure"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get a small sample of addresses to inspect structure
    params = {'per_page': 10, 'page': 1}
    raw, error = make_paginated_api_request('/api/public/v1/core/addresses', params=params)
    
    if error:
        return jsonify({'error': error}), 500
    
    addresses = raw.get('result', {}).get('data', [])
    
    # Return raw data for inspection
    return jsonify({
        'raw_response': raw,
        'sample_addresses': addresses[:5],  # First 5 addresses
        'address_keys': list(addresses[0].keys()) if addresses else [],
        'total_addresses': len(addresses)
    })


@app.route('/api/test/delivery-methods')
def api_test_delivery_methods():
    """Simple test endpoint for delivery methods"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated', 'authenticated': False}), 401
    
    # Return a simple test response
    test_methods = [
        {'value': 'Yugen', 'label': 'Yugen'},
        {'value': 'Shippr', 'label': 'Shippr'},
        {'value': 'DHL', 'label': 'DHL'},
        {'value': 'UPS', 'label': 'UPS'}
    ]
    
    return jsonify({
        'result': test_methods,
        'message': 'Test endpoint working',
        'authenticated': True
    })


@app.route('/api/debug/delivery-orders')
def api_debug_delivery_orders():
    """Debug endpoint to see actual delivery order structure"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get a small sample of delivery orders to inspect structure
    params = {'per_page': 5, 'page': 1}
    raw, error = make_paginated_api_request('/api/public/v1/crm/delivery-orders', params=params)
    
    if error:
        return jsonify({'error': error}), 500
    
    orders = raw.get('result', {}).get('data', [])
    
    # Return raw data for inspection
    return jsonify({
        'raw_response': raw,
        'sample_orders': orders[:3],  # First 3 orders
        'order_keys': list(orders[0].keys()) if orders else [],
        'total_orders': len(orders)
    })


@app.route('/api/debug/sales-invoices')
def api_debug_sales_invoices():
    """Debug endpoint to see actual sales invoice structure for delivery info"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get a small sample of sales invoices to inspect structure
    params = {'per_page': 5, 'page': 1}
    raw, error = make_paginated_api_request('/api/public/v1/trade/sales-invoices', params=params)
    
    if error:
        return jsonify({'error': error}), 500
    
    invoices = raw.get('result', {}).get('data', [])
    
    # Return raw data for inspection
    return jsonify({
        'raw_response': raw,
        'sample_invoices': invoices[:3],  # First 3 invoices
        'invoice_keys': list(invoices[0].keys()) if invoices else [],
        'total_invoices': len(invoices)
    })


@app.route('/api/debug/companies')
def api_debug_companies():
    """Debug endpoint to see actual company structure and available transport method fields"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get a small sample of companies to inspect structure
    params = {'per_page': 10, 'page': 1, 'include': 'country,company_status,sales_price_class,company_categories'}
    raw, error = make_paginated_api_request('/api/public/v1/core/companies', params=params)
    
    if error:
        return jsonify({'error': error}), 500
    
    companies = raw.get('result', {}).get('data', [])
    
    # Look for transport/delivery related fields
    transport_fields = []
    if companies:
        sample_company = companies[0]
        for key in sample_company.keys():
            if any(keyword in key.lower() for keyword in ['transport', 'delivery', 'shipping', 'carrier', 'method', 'logistics']):
                transport_fields.append({
                    'field': key,
                    'value': sample_company[key],
                    'type': type(sample_company[key]).__name__
                })
    
    # Return raw data for inspection
    return jsonify({
        'raw_response': raw,
        'sample_companies': companies[:3],  # First 3 companies
        'company_keys': list(companies[0].keys()) if companies else [],
        'total_companies': len(companies),
        'transport_related_fields': transport_fields,
        'all_field_names': sorted(companies[0].keys()) if companies else []
    })


@app.route('/api/transport-methods')
def api_transport_methods():
    """Get transport methods from the official Duano API endpoint"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get query parameters for filtering and ordering (matching Duano API documentation)
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
    
    # Add pagination
    params['per_page'] = request.args.get('per_page', 100)
    params['page'] = request.args.get('page', 1)
    
    # Use the official Duano API endpoint for transport methods
    data, error = make_paginated_api_request('/api/public/v1/core/transport-methods', params=params)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify(data)


@app.route('/api/transport-methods/<int:transport_method_id>')
def api_transport_method(transport_method_id):
    """Get specific transport method by ID from Duano API"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    data, error = make_api_request(f'/api/public/v1/core/transport-methods/{transport_method_id}')
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify(data)


@app.route('/api/debug/transport-methods')
def api_debug_transport_methods():
    """Debug endpoint to explore transport methods from multiple sources"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    results = {}
    
    # 1. Try the official transport methods endpoint
    try:
        official_data, official_error = make_api_request('/api/public/v1/core/transport-methods', params={'per_page': 50, 'page': 1})
        if official_error:
            results['official_endpoint'] = {'error': official_error}
        else:
            results['official_endpoint'] = {
                'success': True, 
                'data': official_data,
                'total_methods': len(official_data.get('result', {}).get('data', [])) if official_data else 0
            }
    except Exception as e:
        results['official_endpoint'] = {'error': f'Exception: {str(e)}'}
    
    # 2. Also try to get transport methods from companies
    try:
        company_data, company_error = make_api_request('/api/public/v1/core/companies', params={'per_page': 100, 'page': 1})
        if not company_error and company_data:
            companies = company_data.get('result', {}).get('data', [])
            transport_methods_from_companies = set()
            
            for company in companies:
                # Look for transport method fields in company data
                for key, value in company.items():
                    if any(keyword in key.lower() for keyword in ['transport', 'delivery', 'shipping', 'carrier', 'method', 'logistics']):
                        if value and str(value).strip() and str(value).lower() not in ['none', 'null', '']:
                            transport_methods_from_companies.add(str(value))
            
            results['companies_transport_fields'] = {
                'transport_methods_found': list(transport_methods_from_companies),
                'companies_checked': len(companies)
            }
    except Exception as e:
        results['companies_transport_fields'] = {'error': str(e)}
    
    return jsonify({
        'debug_results': results,
        'message': 'Debug information for transport methods from various sources'
    })


@app.route('/api/companies/<int:company_id>/orders')
def api_company_orders(company_id):
    """Get purchase orders for a specific company with transport method information"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    # First get the company information to extract transport method
    company_data, company_error = make_api_request(f'/api/public/v1/core/companies/{company_id}')
    company_transport_method = None
    company_info = None
    
    if not company_error and company_data:
        company_info = company_data.get('result', {})
        # Look for transport method in company data
        for key, value in company_info.items():
            if any(keyword in key.lower() for keyword in ['transport', 'delivery', 'shipping', 'carrier', 'method', 'logistics']):
                if value and str(value).strip() and str(value).lower() not in ['none', 'null', '']:
                    company_transport_method = str(value).strip()
                    break
    
    # Get purchase orders for this company (purchase orders contain transport_method field!)
    params = {
        'per_page': 100,
        'page': 1,
        'filter_by_company': company_id  # Filter by company
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
    
    data, error = make_paginated_api_request('/api/public/v1/trade/purchase-orders', params=params)
    
    if error:
        return jsonify({'error': error}), 500
    
    # Enhance orders with transport method information
    if data and 'result' in data and 'data' in data['result']:
        orders = data['result']['data']
        for order in orders:
            # Extract transport method from the order (purchase orders have transport_method field!)
            order_transport_method = None
            if 'transport_method' in order and order['transport_method']:
                transport_method_obj = order['transport_method']
                if isinstance(transport_method_obj, dict) and 'name' in transport_method_obj:
                    order_transport_method = transport_method_obj['name']
                    order['extracted_transport_method'] = order_transport_method
                    order['transport_method_source'] = 'order_direct'
            
            # Fallback to extraction from other fields
            if not order_transport_method:
                order_transport_method = extract_delivery_method_from_record(order, "order")
                if order_transport_method:
                    order['extracted_transport_method'] = order_transport_method
                    order['transport_method_source'] = 'order_extracted'
            
            # Fallback to company transport method
            if not order_transport_method and company_transport_method:
                order['extracted_transport_method'] = company_transport_method
                order['transport_method_source'] = 'company'
            
            # Also add company info for reference
            if company_info:
                order['company_info'] = {
                    'id': company_info.get('id'),
                    'name': company_info.get('name') or company_info.get('public_name'),
                    'transport_method': company_transport_method
                }
    
    return jsonify(data)


@app.route('/api/companies/<int:company_id>/supplier-orders')
def api_company_supplier_orders(company_id):
    """Get delivery orders where company is the supplier with transport method information"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    # First get the company information to extract transport method
    company_data, company_error = make_api_request(f'/api/public/v1/core/companies/{company_id}')
    company_transport_method = None
    
    if not company_error and company_data:
        company_info = company_data.get('result', {})
        # Look for transport method in company data
        for key, value in company_info.items():
            if any(keyword in key.lower() for keyword in ['transport', 'delivery', 'shipping', 'carrier', 'method', 'logistics']):
                if value and str(value).strip() and str(value).lower() not in ['none', 'null', '']:
                    company_transport_method = str(value).strip()
                    break
    
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
    
    # Enhance orders with company transport method information
    if data and 'result' in data and 'data' in data['result']:
        orders = data['result']['data']
        for order in orders:
            # Add transport method from company if not already present in order
            order_transport_method = extract_delivery_method_from_record(order, "order")
            if not order_transport_method and company_transport_method:
                order['company_transport_method'] = company_transport_method
                order['transport_method_source'] = 'company'
            elif order_transport_method:
                order['transport_method_source'] = 'order'
            
            # Also add company info for reference
            if company_info:
                order['supplier_info'] = {
                    'id': company_info.get('id'),
                    'name': company_info.get('name') or company_info.get('public_name'),
                    'transport_method': company_transport_method
                }
    
    return jsonify(data)


@app.route('/orders')
def orders():
    """Delivery orders page"""
    if not is_logged_in():
        return redirect(url_for('index'))
    
    return render_template('orders.html')


@app.route('/transport-methods-test')
def transport_methods_test():
    """Transport methods test page"""
    if not is_logged_in():
        return redirect(url_for('index'))
    
    return render_template('transport_methods.html')


@app.route('/api/purchase-orders-by-transport')
def api_purchase_orders_by_transport():
    """Get sales orders filtered by transport method - simple table data"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get query parameters
    transport_method = request.args.get('transport_method')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    try:
        # Get ALL purchase orders - use make_paginated_api_request to get everything
        params = {'per_page': 100, 'page': 1}  # make_paginated_api_request will get all pages
        
        # Apply date filtering after getting all data (client-side filtering)
        # API date filtering seems unreliable, so we'll filter after fetching
        
        # Try both sales orders and purchase orders to find transport method data
        all_orders = []
        sources_tried = []
        
        # 1. Try sales orders first (based on user's Duano screenshot showing "Verkoopbestellingen")
        sales_raw, sales_error = make_paginated_api_request('/api/public/v1/trade/sales-orders', params=params)
        if not sales_error and sales_raw:
            sales_orders = sales_raw.get('result', {}).get('data', [])
            all_orders.extend(sales_orders)
            sources_tried.append(f"Sales orders: {len(sales_orders)}")
        else:
            sources_tried.append(f"Sales orders: Error - {sales_error}")
        
        # 2. Try purchase orders
        purchase_raw, purchase_error = make_paginated_api_request('/api/public/v1/trade/purchase-orders', params=params)
        if not purchase_error and purchase_raw:
            purchase_orders = purchase_raw.get('result', {}).get('data', [])
            all_orders.extend(purchase_orders)
            sources_tried.append(f"Purchase orders: {len(purchase_orders)}")
        else:
            sources_tried.append(f"Purchase orders: Error - {purchase_error}")
        
        # Use combined orders
        orders = all_orders
        
        if len(orders) == 0:
            return jsonify({
                'result': [],
                'summary': {
                    'total_orders': 0,
                    'total_in_system': 0,
                    'filtered_by_transport_method': transport_method,
                    'date_range': {'start_date': start_date, 'end_date': end_date}
                },
                'debug': {
                    'sources_tried': sources_tried,
                    'message': 'No orders found in either sales orders or purchase orders endpoints'
                }
            })
        
        # If no orders found with date filtering, try without dates to debug
        if len(orders) == 0 and (start_date or end_date):
            raw_no_dates, error_no_dates = make_paginated_api_request('/api/public/v1/trade/purchase-orders', {'per_page': 100, 'page': 1})
            if not error_no_dates:
                orders_no_dates = raw_no_dates.get('result', {}).get('data', [])
                sample_dates = [o.get('date') or o.get('created_at') for o in orders_no_dates[:5]]
                
                return jsonify({
                    'result': [],
                    'summary': {
                        'total_orders': 0,
                        'total_in_system': len(orders_no_dates),
                        'filtered_by_transport_method': transport_method,
                        'date_range': {'start_date': start_date, 'end_date': end_date}
                    },
                    'debug': {
                        'total_orders_with_dates': len(orders),
                        'total_orders_without_dates': len(orders_no_dates),
                        'sample_order_dates': sample_dates,
                        'message': f'No orders found with date filter {start_date} to {end_date}. Found {len(orders_no_dates)} orders without date filter.'
                    }
                })
        
        # Filter and process orders
        filtered_orders = []
        debug_info = {
            'total_orders': len(orders), 
            'transport_methods_found': set(), 
            'filter_applied': transport_method,
            'sources_tried': sources_tried
        }
        
        for order in orders:
            # Apply client-side date filtering first
            order_date = order.get('date') or order.get('created_at')
            if start_date and order_date and order_date < start_date:
                continue
            if end_date and order_date and order_date > end_date:
                continue
            
            # Extract transport method
            order_transport_method = None
            transport_method_id = None
            
            if 'transport_method' in order and order['transport_method']:
                transport_method_obj = order['transport_method']
                if isinstance(transport_method_obj, dict):
                    order_transport_method = transport_method_obj.get('name')
                    transport_method_id = transport_method_obj.get('id')
                    debug_info['transport_methods_found'].add(order_transport_method)
            
            # Apply transport method filter (case-insensitive) - only if specified
            if transport_method and transport_method.strip():
                if not order_transport_method or transport_method.lower() not in order_transport_method.lower():
                    continue
            
            # Calculate total quantity
            total_quantity = 0
            if order.get('ordered_items'):
                for item in order['ordered_items']:
                    total_quantity += item.get('quantity', 0)
            
            # Extract company info
            company_name = 'Unknown'
            if order.get('company') and isinstance(order['company'], dict):
                company_name = order['company'].get('name', 'Unknown')
            
            # Extract address information
            address_info = 'N/A'
            address_name = 'N/A'
            
            if order.get('address') and isinstance(order['address'], dict):
                address_obj = order['address']
                address_name = address_obj.get('name', 'N/A')
                address_id = address_obj.get('id', 'N/A')
                
                # For now, show address name and ID - we'll enhance this later
                address_info = f"{address_name} (ID: {address_id})"
            
            # Format order for table
            filtered_orders.append({
                'id': order.get('id'),
                'date': order.get('date') or order.get('created_at'),
                'company': company_name,
                'transport_method': order_transport_method or 'Unknown',
                'transport_method_id': transport_method_id,
                'status': order.get('status'),
                'transaction_number': order.get('transaction_number'),
                'total_quantity': total_quantity,
                'address': address_info,
                'address_name': address_name,
                'trade_reference': order.get('trade_reference', ''),
                'requested_delivery_date': order.get('requested_delivery_date'),
                'ordered_items': order.get('ordered_items', [])
            })
        
        # Sort by date (newest first)
        filtered_orders.sort(key=lambda x: x['date'] or '', reverse=True)
        
        # Convert set to list for JSON serialization
        debug_info['transport_methods_found'] = list(debug_info['transport_methods_found'])
        
        return jsonify({
            'result': filtered_orders,
            'summary': {
                'total_orders': len(filtered_orders),
                'total_in_system': len(orders),
                'filtered_by_transport_method': transport_method,
                'date_range': {
                    'start_date': start_date,
                    'end_date': end_date
                }
            },
            'debug': debug_info
        })
        
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500


@app.route('/api/orders-with-full-addresses')
def api_orders_with_full_addresses():
    """Get all orders with full address details - simplified version"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get query parameters
    transport_method = request.args.get('transport_method')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    try:
        # Get all purchase orders using make_paginated_api_request for complete data
        params = {'per_page': 100, 'page': 1}
        
        # Try both sales orders and purchase orders
        all_orders = []
        sources_tried = []
        
        # 1. Try sales orders first (based on user's Duano screenshot)
        sales_raw, sales_error = make_paginated_api_request('/api/public/v1/trade/sales-orders', params)
        if not sales_error and sales_raw:
            sales_orders = sales_raw.get('result', {}).get('data', [])
            all_orders.extend(sales_orders)
            sources_tried.append(f"Sales orders: {len(sales_orders)}")
        else:
            sources_tried.append(f"Sales orders: Error - {sales_error}")
        
        # 2. Try purchase orders
        purchase_raw, purchase_error = make_paginated_api_request('/api/public/v1/trade/purchase-orders', params)
        if not purchase_error and purchase_raw:
            purchase_orders = purchase_raw.get('result', {}).get('data', [])
            all_orders.extend(purchase_orders)
            sources_tried.append(f"Purchase orders: {len(purchase_orders)}")
        else:
            sources_tried.append(f"Purchase orders: Error - {purchase_error}")
        
        # Process and filter orders
        filtered_orders = []
        transport_methods_found = set()
        address_ids_to_lookup = set()
        
        for order in all_orders:
            # Apply client-side date filtering
            order_date = order.get('date') or order.get('created_at')
            if start_date and order_date and order_date < start_date:
                continue
            if end_date and order_date and order_date > end_date:
                continue
            
            # Extract transport method
            order_transport_method = None
            transport_method_id = None
            
            if 'transport_method' in order and order['transport_method']:
                transport_method_obj = order['transport_method']
                if isinstance(transport_method_obj, dict):
                    order_transport_method = transport_method_obj.get('name')
                    transport_method_id = transport_method_obj.get('id')
                    transport_methods_found.add(order_transport_method)
            
            # Apply transport method filter
            if transport_method and transport_method.strip():
                if not order_transport_method or transport_method.lower() not in order_transport_method.lower():
                    continue
            
            # Extract address info - for now just use what's available in the order
            address_info = 'N/A'
            address_name = 'N/A'
            
            if order.get('address') and isinstance(order['address'], dict):
                address_obj = order['address']
                address_name = address_obj.get('name', 'N/A')
                address_id = address_obj.get('id', 'N/A')
                
                # Show address name and ID for now - we can enhance this later
                address_info = f"{address_name} (ID: {address_id})"
                
                # Collect address IDs for potential future lookup
                if address_id and address_id != 'N/A':
                    address_ids_to_lookup.add(address_id)
            
            # Calculate total quantity
            total_quantity = 0
            if order.get('ordered_items'):
                for item in order['ordered_items']:
                    total_quantity += item.get('quantity', 0)
            
            # Extract company info
            company_name = 'Unknown'
            if order.get('company') and isinstance(order['company'], dict):
                company_name = order['company'].get('name', 'Unknown')
            
            # Add to results
            filtered_orders.append({
                'id': order.get('id'),
                'date': order_date,
                'company': company_name,
                'transport_method': order_transport_method or 'Unknown',
                'transport_method_id': transport_method_id,
                'status': order.get('status'),
                'transaction_number': order.get('transaction_number'),
                'total_quantity': total_quantity,
                'address': address_info,
                'address_name': address_name,
                'trade_reference': order.get('trade_reference', ''),
                'requested_delivery_date': order.get('requested_delivery_date'),
                'ordered_items': order.get('ordered_items', [])
            })
        
        # Sort by date (newest first)
        filtered_orders.sort(key=lambda x: x['date'] or '', reverse=True)
        
        return jsonify({
            'result': filtered_orders,
            'summary': {
                'total_orders': len(filtered_orders),
                'total_in_system': len(all_orders),
                'filtered_by_transport_method': transport_method,
                'date_range': {
                    'start_date': start_date,
                    'end_date': end_date
                }
            },
            'debug': {
                'sources_tried': sources_tried,
                'transport_methods_found': list(transport_methods_found),
                'unique_address_ids': len(address_ids_to_lookup),
                'message': f'Found {len(all_orders)} total orders, {len(filtered_orders)} after filtering'
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500


@app.route('/api/debug/orders-summary')
def api_debug_orders_summary():
    """Debug endpoint to explore different order endpoints and find transport methods"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Try multiple order-related endpoints to find where transport methods are stored
    endpoints_to_try = [
        '/api/public/v1/crm/delivery-orders',
        '/api/public/v1/trade/sales-invoices', 
        '/api/public/v1/trade/purchase-orders',
        '/api/public/v1/core/transactions',
        '/api/public/v1/logistics/orders'
    ]
    
    results = {}
    
    for endpoint in endpoints_to_try:
        try:
            params = {'per_page': 10, 'page': 1}  # Small sample to check structure
            raw, error = make_api_request(endpoint, params=params)
            
            if error:
                results[endpoint] = {'error': error}
            else:
                data = raw.get('result', {}).get('data', []) if raw else []
                sample_record = data[0] if data else None
                
                # Look for transport method fields
                transport_method_found = False
                transport_method_value = None
                
                if sample_record:
                    for key, value in sample_record.items():
                        if 'transport' in key.lower():
                            transport_method_found = True
                            transport_method_value = value
                            break
                
                results[endpoint] = {
                    'success': True,
                    'total_records': len(data),
                    'sample_record_keys': list(sample_record.keys()) if sample_record else [],
                    'transport_method_found': transport_method_found,
                    'transport_method_value': transport_method_value,
                    'sample_record': sample_record
                }
                
        except Exception as e:
            results[endpoint] = {'error': f'Exception: {str(e)}'}
    
    return jsonify({
        'endpoint_exploration': results,
        'message': 'Exploring different endpoints to find transport method data'
    })


@app.route('/api/debug/find-transport-methods')
def api_debug_find_transport_methods():
    """Specifically look for the endpoint that contains transport method data like in the user's example"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Based on the user's example showing transaction data with transport_method field
    # Let's try to find the correct endpoint
    possible_endpoints = [
        '/api/public/v1/core/transactions',
        '/api/public/v1/trade/transactions', 
        '/api/public/v1/logistics/transactions',
        '/api/public/v1/crm/transactions',
        '/api/public/v1/core/orders',
        '/api/public/v1/trade/orders',
        '/api/public/v1/logistics/orders',
        '/api/public/v1/crm/orders'
    ]
    
    results = {}
    found_transport_methods = []
    
    for endpoint in possible_endpoints:
        try:
            params = {'per_page': 20, 'page': 1}
            raw, error = make_api_request(endpoint, params=params)
            
            if error:
                results[endpoint] = {'error': error}
                continue
                
            data = raw.get('result', {}).get('data', []) if raw else []
            
            # Look for records with transport_method field
            records_with_transport = []
            for record in data:
                if 'transport_method' in record and record['transport_method']:
                    records_with_transport.append({
                        'id': record.get('id'),
                        'transport_method': record['transport_method'],
                        'company': record.get('company'),
                        'date': record.get('date'),
                        'transaction_number': record.get('transaction_number')
                    })
                    
                    # Extract transport method for summary
                    if isinstance(record['transport_method'], dict) and 'name' in record['transport_method']:
                        found_transport_methods.append(record['transport_method']['name'])
            
            results[endpoint] = {
                'success': True,
                'total_records': len(data),
                'records_with_transport_method': len(records_with_transport),
                'sample_transport_records': records_with_transport[:3],  # First 3 examples
                'sample_record_structure': data[0] if data else None
            }
            
        except Exception as e:
            results[endpoint] = {'error': f'Exception: {str(e)}'}
    
    # Remove duplicates from transport methods
    unique_transport_methods = list(set(found_transport_methods))
    
    return jsonify({
        'results': results,
        'found_transport_methods': unique_transport_methods,
        'total_unique_transport_methods': len(unique_transport_methods),
        'message': 'Searching for the specific endpoint that contains transport_method field like in your example'
    })


# Pricing API endpoints
@app.route('/api/pricing/purchase-adjustments')
def api_purchase_price_adjustments():
    """Get purchase price adjustments"""
    if not is_logged_in():
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
    if not is_logged_in():
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
    if not is_logged_in():
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
    if not is_logged_in():
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
                    search_lower in company.get('address_line2', '').lower() or
                    search_lower in company.get('city', '').lower() or
                    search_lower in company.get('post_code', '').lower() or
                    search_lower in company.get('vat_number', '').lower() or
                    search_lower in company.get('phone_number', '').lower() or
                    search_lower in company.get('email', '').lower() or
                    search_lower in company.get('website', '').lower() or
                    (company.get('country') and search_lower in company['country'].get('name', '').lower()) or
                    (company.get('account_manager') and search_lower in company['account_manager'].get('name', '').lower()) or
                    any(search_lower in str(v).lower() for v in company.values() if v))
            ]
        
        return companies
    else:
        raise Exception(f'Failed to fetch CRM data: {response.status_code}')

@app.route('/api/crm/search-vat/<vat_number>', methods=['GET'])
def api_search_company_by_vat(vat_number):
    """Search company in CRM by VAT number"""
    if not is_logged_in():
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
    if not is_logged_in():
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


def recalculate_company_metrics_from_invoices(company_ids=None, max_companies=9999):
    """
    Recalculate company aggregates (revenue, invoice counts) from invoice tables.
    If company_ids is provided, only update those companies.
    max_companies limits processing (default 9999 = all).
    """
    if not supabase_client:
        return False
    
    try:
        # Get unique company IDs from both invoice tables if not provided
        if company_ids is None:
            company_ids = set()
            
            for year in ['2024', '2025']:
                try:
                    # Just get distinct company IDs - more efficient
                    batch = supabase_client.table(f'sales_{year}').select('company_id').limit(5000).execute()
                    if batch.data:
                        for record in batch.data:
                            if record.get('company_id'):
                                company_ids.add(record['company_id'])
                except Exception as e:
                    print(f"Error fetching company IDs from {year}: {e}")
        
        company_list = list(company_ids)[:max_companies]
        total_companies = len(company_list)
        print(f"📊 Recalculating metrics for {total_companies} companies...")
        updated_count = 0
        
        for company_id in company_list:
            try:
                # Get invoices from both years
                metrics_2024 = {'revenue': 0, 'count': 0, 'first_date': None, 'last_date': None}
                metrics_2025 = {'revenue': 0, 'count': 0, 'first_date': None, 'last_date': None}
                
                for year, metrics in [('2024', metrics_2024), ('2025', metrics_2025)]:
                    invoices = supabase_client.table(f'sales_{year}').select('total_amount, invoice_date, invoice_data').eq('company_id', company_id).execute()

                    if invoices.data:
                        metrics['count'] = len(invoices.data)
                        # Calculate revenue from line items (ex-VAT) - matches DUANO's "Omzet"
                        total_rev = 0
                        for inv in invoices.data:
                            invoice_data = inv.get('invoice_data') or {}
                            line_items = invoice_data.get('invoice_line_items') or []
                            line_revenue = sum(float(item.get('revenue') or 0) for item in line_items)
                            # Fall back to total_amount only if no line items
                            total_rev += line_revenue if line_revenue > 0 else float(inv.get('total_amount') or 0)
                        metrics['revenue'] = total_rev
                        
                        dates = [inv.get('invoice_date') for inv in invoices.data if inv.get('invoice_date')]
                        if dates:
                            metrics['first_date'] = min(dates)
                            metrics['last_date'] = max(dates)
                
                # Calculate combined metrics
                total_revenue = metrics_2024['revenue'] + metrics_2025['revenue']
                total_count = metrics_2024['count'] + metrics_2025['count']
                
                all_dates = [d for d in [metrics_2024['first_date'], metrics_2024['last_date'], 
                                          metrics_2025['first_date'], metrics_2025['last_date']] if d]
                
                # Update company record
                update_data = {
                    'total_revenue_2024': metrics_2024['revenue'],
                    'invoice_count_2024': metrics_2024['count'],
                    'total_revenue_2025': metrics_2025['revenue'],
                    'invoice_count_2025': metrics_2025['count'],
                    'total_revenue_all_time': total_revenue,
                    'invoice_count_all_time': total_count,
                    'average_invoice_value': total_revenue / total_count if total_count > 0 else 0,
                    'first_invoice_date': min(all_dates) if all_dates else None,
                    'last_invoice_date': max(all_dates) if all_dates else None,
                    'updated_at': datetime.now().isoformat()
                }
                
                # Check if company exists in companies table
                existing = supabase_client.table('companies').select('id').eq('company_id', company_id).execute()
                
                if existing.data:
                    supabase_client.table('companies').update(update_data).eq('company_id', company_id).execute()
                    updated_count += 1
                    
                    if updated_count % 50 == 0:
                        print(f"  ✅ Updated metrics for {updated_count} companies...")
            
            except Exception as e:
                print(f"  ⚠️  Error updating company {company_id}: {e}")
                continue
        
        print(f"✅ Successfully updated metrics for {updated_count} companies")
        return True
        
    except Exception as e:
        print(f"❌ Error recalculating company metrics: {e}")
        return False


@app.route('/api/sync-2025-invoices', methods=['POST'])
def api_sync_2025_invoices():
    """
    Sync 2025 sales invoices to Supabase since last update.
    Processes in batches - call multiple times if needed.
    Admin only - requires DUANO authentication.
    """
    if not is_admin():
        return jsonify({'error': 'Admin access required', 'success': False}), 403
    
    try:
        from datetime import datetime, timedelta
        import time as time_module
        
        print("🚀 Starting 2025 invoice sync...")
        sync_start = time_module.time()
        
        # Check sync options
        request_data = request.json if request.is_json else {}
        full_sync = request_data.get('full_sync', False)
        
        if full_sync:
            # Full sync from beginning of year
            start_date = '2025-01-01'
            print("📅 FULL SYNC requested - syncing all 2025 invoices")
        else:
            # Incremental sync - check for gaps AND missing early data
            all_dates_result = supabase_client.table('sales_2025').select('invoice_date').order('invoice_date', desc=False).limit(5000).execute()
            
            if all_dates_result.data:
                # Get unique dates sorted
                dates = sorted(set(r.get('invoice_date') for r in all_dates_result.data if r.get('invoice_date')))
                
                if dates:
                    oldest_date = dates[0]
                    most_recent = dates[-1]
                    
                    # FIRST: Check if we're missing early 2025 data (before oldest date)
                    oldest_dt = datetime.strptime(oldest_date, '%Y-%m-%d')
                    year_start = datetime(2025, 1, 1)
                    days_from_start = (oldest_dt - year_start).days
                    
                    if days_from_start > 14:  # More than 2 weeks missing from start of year
                        start_date = '2025-01-01'
                        print(f"🔍 Missing early 2025 data! Oldest invoice: {oldest_date}")
                        print(f"📅 Starting sync from beginning: {start_date}")
                    else:
                        # Check for gaps between dates
                        gap_start = None
                        for i in range(len(dates) - 1):
                            d1 = datetime.strptime(dates[i], '%Y-%m-%d')
                            d2 = datetime.strptime(dates[i + 1], '%Y-%m-%d')
                            gap_days = (d2 - d1).days
                            if gap_days > 5:  # Gap of more than 5 days
                                gap_start = dates[i]
                                print(f"🔍 Found gap in data: {dates[i]} -> {dates[i+1]} ({gap_days} days)")
                                break
                        
                        if gap_start:
                            start_date = gap_start
                            print(f"📅 Starting sync from gap: {start_date}")
                        else:
                            # No gap - just sync recent
                            start_date = (datetime.strptime(most_recent, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
                            print(f"📅 Data looks complete, syncing from: {start_date}")
                else:
                    start_date = '2025-01-01'
            else:
                start_date = '2025-01-01'
        
        end_date = datetime.now().strftime('%Y-%m-%d')
        
        # Get page from request for continuation
        request_page = request_data.get('page', 1)
        
        print(f"📅 Syncing invoices from {start_date} to {end_date}, starting page {request_page}")
        
        all_invoices = []
        page = request_page
        per_page = 50
        pages_fetched = 0
        max_pages_per_batch = 3  # Process 3 pages per call (~150 invoices)
        
        while pages_fetched < max_pages_per_batch:
            params = {
                'per_page': per_page,
                'page': page,
                'filter_by_start_date': start_date,
                'filter_by_end_date': end_date,
                'order_by_date': 'desc'
            }
            
            print(f"📡 Fetching page {page}...")
            page_start = time_module.time()
            
            # Direct API call with longer timeout
            headers = {
                'Authorization': f"Bearer {session['access_token']}",
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            url = f"{DOUANO_CONFIG['base_url']}/api/public/v1/trade/sales-invoices"
            
            try:
                response = requests.get(url, headers=headers, params=params, timeout=30)
                page_duration = time_module.time() - page_start
                print(f"⏱️ Page {page} response in {page_duration:.1f}s - Status: {response.status_code}")
                
                if response.status_code != 200:
                    return jsonify({
                        'error': f'DUANO API error: {response.status_code}',
                        'success': False,
                        'response': response.text[:500]
                    }), 500
                
                data = response.json()
            except requests.exceptions.Timeout:
                return jsonify({
                    'error': 'DUANO API timeout - API is responding slowly',
                    'success': False,
                    'page': page
                }), 500
            except Exception as e:
                return jsonify({
                    'error': f'Request failed: {str(e)}',
                    'success': False
                }), 500
            
            invoices = data.get('result', {}).get('data', [])
            
            if not invoices:
                break
            
            all_invoices.extend(invoices)
            print(f"📄 Page {page}: {len(invoices)} invoices (Total: {len(all_invoices)})")
            
            # Check pagination
            current_page = data.get('result', {}).get('current_page', page)
            last_page = data.get('result', {}).get('last_page', page)
            
            if current_page >= last_page:
                # All pages done
                next_page = None
                break
            
            page += 1
            pages_fetched += 1
            
            # Check if we're running out of time (max 15 seconds for fetching)
            if time_module.time() - sync_start > 15:
                print(f"⏱️ Stopping fetch early to avoid timeout, next page: {page}")
                next_page = page
                break
        else:
            # Loop completed without break - more pages available
            next_page = page + 1 if pages_fetched >= max_pages_per_batch else None
        
        if not all_invoices:
            return jsonify({'message': 'No new invoices found', 'count': 0, 'success': True, 'complete': True})
        
        print(f"✅ Total invoices fetched: {len(all_invoices)}")
        
        # Save to Supabase
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500
        
        saved_count = 0
        updated_count = 0
        error_count = 0
        
        # Process in batches of 10 to speed up
        batch_size = 10
        for batch_start in range(0, len(all_invoices), batch_size):
            batch = all_invoices[batch_start:batch_start + batch_size]
            
            for invoice in batch:
                try:
                    # Extract key fields
                    company = invoice.get('company', {})
                    if isinstance(company, dict):
                        company_id = company.get('id')
                        company_name = company.get('name') or company.get('public_name')
                    else:
                        company_id = None
                        company_name = None
                    
                    # Get the amount - prefer line item revenue (ex-VAT)
                    line_items = invoice.get('invoice_line_items', [])
                    if line_items:
                        amount = sum(float(item.get('revenue') or 0) for item in line_items)
                    else:
                        amount = 0

                    # Fall back to total_amount only if no line items
                    if amount == 0:
                        amount = float(invoice.get('total_amount') or invoice.get('balance') or 0)
                    
                    record = {
                        'invoice_id': invoice.get('id'),
                        'invoice_data': invoice,
                        'company_id': company_id,
                        'company_name': company_name,
                        'invoice_number': invoice.get('invoice_number') or invoice.get('number'),
                        'invoice_date': invoice.get('date'),
                        'due_date': invoice.get('due_date'),
                        'total_amount': amount if amount else None,
                        'balance': invoice.get('balance'),
                        'is_paid': invoice.get('balance', 0) == 0
                    }
                    
                    # Upsert - insert or update on conflict
                    supabase_client.table('sales_2025').upsert(record, on_conflict='invoice_id').execute()
                    saved_count += 1
                    
                except Exception as e:
                    error_count += 1
                    if "Resource temporarily unavailable" not in str(e):
                        print(f"❌ Error saving invoice {invoice.get('id')}: {e}")
            
            # Check time - stop if running long to avoid timeout
            elapsed = time_module.time() - sync_start
            if elapsed > 25:
                print(f"⏱️ Stopping save early at {batch_start + len(batch)} invoices to avoid timeout")
                break
        
        # Determine if more pages to process
        is_complete = next_page is None
        
        result = {
            'success': True,
            'total_fetched': len(all_invoices),
            'saved': saved_count,
            'errors': error_count,
            'date_range': f'{start_date} to {end_date}',
            'complete': is_complete,
            'next_page': next_page,
            'message': f'Synced {saved_count} invoices' + ('' if is_complete else f' (continue from page {next_page})')
        }
        
        elapsed = time_module.time() - sync_start
        print(f"✅ Sync batch complete in {elapsed:.1f}s: {result}")
        
        return jsonify(result)
        
    except Exception as e:
        import traceback
        print(f"❌ Error in sync: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/api/sync-invoices', methods=['POST'])
def api_sync_invoices():
    """
    Unified invoice sync endpoint - auto-detects year from invoice dates.
    Routes invoices to sales_2024, sales_2025, or sales_2026 based on invoice_date.
    """
    if not is_admin():
        return jsonify({'error': 'Admin access required', 'success': False}), 403

    try:
        from datetime import datetime, timedelta
        import time as time_module

        print("🚀 Starting unified invoice sync...")
        sync_start = time_module.time()

        request_data = request.json if request.is_json else {}
        full_sync = request_data.get('full_sync', False)

        # For full sync, start from beginning of 2024 to sync all years
        # For incremental, sync last 7 days
        if full_sync:
            start_date = '2024-01-01'
            print("📅 FULL SYNC requested - syncing all invoices from 2024, 2025, and 2026")
        else:
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            print(f"📅 Incremental sync from: {start_date}")

        end_date = datetime.now().strftime('%Y-%m-%d')
        request_page = request_data.get('page', 1)

        print(f"📅 Syncing invoices from {start_date} to {end_date}, starting page {request_page}")

        all_invoices = []
        page = request_page
        per_page = 50
        pages_fetched = 0
        max_pages_per_batch = 3

        while pages_fetched < max_pages_per_batch:
            params = {
                'per_page': per_page,
                'page': page,
                'filter_by_start_date': start_date,
                'filter_by_end_date': end_date,
                'order_by_date': 'desc'
            }

            print(f"📡 Fetching page {page}...")

            headers = {
                'Authorization': f"Bearer {session['access_token']}",
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            url = f"{DOUANO_CONFIG['base_url']}/api/public/v1/trade/sales-invoices"

            try:
                response = requests.get(url, headers=headers, params=params, timeout=30)

                if response.status_code != 200:
                    return jsonify({
                        'error': f'DUANO API error: {response.status_code}',
                        'success': False
                    }), 500

                data = response.json()
            except requests.exceptions.Timeout:
                return jsonify({
                    'error': 'DUANO API timeout',
                    'success': False,
                    'page': page
                }), 500

            invoices = data.get('result', {}).get('data', [])

            if not invoices:
                break

            all_invoices.extend(invoices)
            print(f"📄 Page {page}: {len(invoices)} invoices (Total: {len(all_invoices)})")

            current_page = data.get('result', {}).get('current_page', page)
            last_page = data.get('result', {}).get('last_page', page)

            if current_page >= last_page:
                next_page = None
                break

            page += 1
            pages_fetched += 1

            if time_module.time() - sync_start > 15:
                next_page = page
                break
        else:
            next_page = page + 1 if pages_fetched >= max_pages_per_batch else None

        if not all_invoices:
            return jsonify({'message': 'No new invoices found', 'count': 0, 'success': True, 'complete': True})

        print(f"✅ Total invoices fetched: {len(all_invoices)}")

        # Save to Supabase - auto-route by year
        saved_by_year = {'2024': 0, '2025': 0, '2026': 0}
        error_count = 0

        for invoice in all_invoices:
            try:
                # Determine year from invoice_date
                invoice_date = invoice.get('date', '')
                if invoice_date:
                    year = invoice_date[:4]
                else:
                    year = '2026'  # Default to current year

                # Only handle 2024, 2025, 2026
                if year not in ['2024', '2025', '2026']:
                    continue

                table_name = f'sales_{year}'

                # Extract data
                company = invoice.get('company', {})
                if isinstance(company, dict):
                    company_id = company.get('id')
                    company_name = company.get('name') or company.get('public_name')
                else:
                    company_id = None
                    company_name = None

                amount = (
                    invoice.get('payable_amount_without_financial_discount') or
                    invoice.get('payable_amount_with_financial_discount') or
                    invoice.get('total_amount') or
                    invoice.get('balance') or
                    0
                )

                if amount == 0:
                    line_items = invoice.get('invoice_line_items', [])
                    if line_items:
                        amount = sum(float(item.get('payable_amount') or item.get('revenue') or 0) for item in line_items)

                record = {
                    'invoice_id': invoice.get('id'),
                    'invoice_data': invoice,
                    'company_id': company_id,
                    'company_name': company_name,
                    'invoice_number': invoice.get('invoice_number') or invoice.get('number'),
                    'invoice_date': invoice_date,
                    'due_date': invoice.get('due_date'),
                    'total_amount': amount if amount else None,
                    'balance': invoice.get('balance'),
                    'is_paid': True  # Always true - not tracking payment status
                }

                supabase_client.table(table_name).upsert(record, on_conflict='invoice_id').execute()
                saved_by_year[year] += 1

            except Exception as e:
                error_count += 1
                print(f"❌ Error saving invoice {invoice.get('id')}: {e}")

            if time_module.time() - sync_start > 25:
                break

        is_complete = next_page is None
        total_saved = sum(saved_by_year.values())

        result = {
            'success': True,
            'total_fetched': len(all_invoices),
            'saved': total_saved,
            'saved_by_year': saved_by_year,
            'errors': error_count,
            'date_range': f'{start_date} to {end_date}',
            'complete': is_complete,
            'next_page': next_page,
            'message': f'Synced {total_saved} invoices (2024: {saved_by_year["2024"]}, 2025: {saved_by_year["2025"]}, 2026: {saved_by_year["2026"]})'
        }

        print(f"✅ Sync complete: {result}")
        return jsonify(result)

    except Exception as e:
        import traceback
        print(f"❌ Error in sync: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e), 'success': False}), 500


# =====================================================
# PRODUCT & PRICING SYNC ENDPOINTS
# =====================================================

@app.route('/api/sync-product-categories', methods=['POST'])
def api_sync_product_categories():
    """Sync all product categories from Douano to Supabase."""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    if not supabase_client:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    douano_client = get_douano_client()
    if not douano_client:
        return jsonify({'error': 'Douano client not configured'}), 500
    
    try:
        print("🔄 Starting product categories sync...")
        
        # Fetch all categories from Douano
        response = douano_client.products.get_product_categories(per_page=100)
        categories = response.get('result', {}).get('data', [])
        
        saved_count = 0
        updated_count = 0
        errors = []
        
        for category in categories:
            try:
                category_data = {
                    'id': category['id'],
                    'name': category['name'],
                    'is_active': True,
                    'douano_created_at': category.get('created_at'),
                    'douano_updated_at': category.get('updated_at'),
                    'last_sync_at': datetime.now().isoformat()
                }
                
                # Check if category already exists
                existing = supabase_client.table('product_categories').select('id').eq('id', category['id']).execute()
                
                if existing.data:
                    # Update existing
                    supabase_client.table('product_categories').update(category_data).eq('id', category['id']).execute()
                    updated_count += 1
                else:
                    # Insert new
                    supabase_client.table('product_categories').insert(category_data).execute()
                    saved_count += 1
                    
            except Exception as e:
                error_msg = f"Error saving category {category.get('id', 'unknown')}: {e}"
                print(f"  ⚠️  {error_msg}")
                errors.append(error_msg)
        
        print(f"✅ Synced {len(categories)} categories: {saved_count} new, {updated_count} updated")
        
        return jsonify({
            'success': True,
            'total': len(categories),
            'saved': saved_count,
            'updated': updated_count,
            'errors': errors
        })
        
    except Exception as e:
        print(f"❌ Error syncing categories: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/sync-products', methods=['POST'])
def api_sync_products():
    """Sync all products from Douano to Supabase."""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    if not supabase_client:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    douano_client = get_douano_client()
    if not douano_client:
        return jsonify({'error': 'Douano client not configured'}), 500
    
    try:
        print("🔄 Starting products sync...")
        
        # Fetch all products from Douano (paginated)
        all_products = []
        page = 1
        per_page = 50
        
        while True:
            response = douano_client.products.get_products(per_page=per_page, page=page)
            result = response.get('result', {})
            products = result.get('data', [])
            
            if not products:
                break
            
            all_products.extend(products)
            
            # Check if there are more pages
            if result.get('current_page') >= result.get('last_page', 1):
                break
            
            page += 1
            time.sleep(0.1)  # Rate limiting
        
        saved_count = 0
        updated_count = 0
        errors = []
        
        for product in all_products:
            try:
                product_data = {
                    'id': product['id'],
                    'name': product['name'],
                    'sku': product.get('sku'),
                    'category_id': product.get('product_category_id'),
                    'unit': product.get('unit'),
                    'description': product.get('description'),
                    'is_active': product.get('is_active', True),
                    'is_sellable': product.get('is_sellable', True),
                    'is_composed': product.get('is_composed', False),
                    'douano_created_at': product.get('created_at'),
                    'douano_updated_at': product.get('updated_at'),
                    'last_sync_at': datetime.now().isoformat()
                }
                
                # Check if product already exists
                existing = supabase_client.table('products').select('id').eq('id', product['id']).execute()
                
                if existing.data:
                    # Update existing
                    supabase_client.table('products').update(product_data).eq('id', product['id']).execute()
                    updated_count += 1
                else:
                    # Insert new
                    supabase_client.table('products').insert(product_data).execute()
                    saved_count += 1
                    
            except Exception as e:
                error_msg = f"Error saving product {product.get('id', 'unknown')}: {e}"
                print(f"  ⚠️  {error_msg}")
                errors.append(error_msg)
        
        print(f"✅ Synced {len(all_products)} products: {saved_count} new, {updated_count} updated")
        
        return jsonify({
            'success': True,
            'total': len(all_products),
            'saved': saved_count,
            'updated': updated_count,
            'errors': errors
        })
        
    except Exception as e:
        print(f"❌ Error syncing products: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/sync-price-lists', methods=['POST'])
def api_sync_price_lists():
    """Sync all sales price lists from Douano to Supabase."""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    if not supabase_client:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    douano_client = get_douano_client()
    if not douano_client:
        return jsonify({'error': 'Douano client not configured'}), 500
    
    try:
        print("🔄 Starting price lists sync...")
        
        # Fetch all price lists from Douano
        try:
            response = douano_client.pricing.get_sales_price_lists(per_page=100)
            print(f"📥 Raw response: {response}")
            price_lists = response.get('result', {}).get('data', []) if isinstance(response, dict) else response.get('data', []) if isinstance(response, dict) else []
        except Exception as api_error:
            print(f"❌ API Error: {api_error}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'API Error: {str(api_error)}'}), 500
        
        saved_count = 0
        updated_count = 0
        errors = []
        
        for price_list in price_lists:
            try:
                price_list_data = {
                    'id': price_list['id'],
                    'name': price_list['name'],
                    'description': price_list.get('description'),
                    'is_active': price_list.get('is_active', True),
                    'is_default': price_list.get('is_default', False),
                    'douano_created_at': price_list.get('created_at'),
                    'douano_updated_at': price_list.get('updated_at'),
                    'last_sync_at': datetime.now().isoformat()
                }
                
                # Check if price list already exists
                existing = supabase_client.table('sales_price_lists').select('id').eq('id', price_list['id']).execute()
                
                if existing.data:
                    # Update existing
                    supabase_client.table('sales_price_lists').update(price_list_data).eq('id', price_list['id']).execute()
                    updated_count += 1
                else:
                    # Insert new
                    supabase_client.table('sales_price_lists').insert(price_list_data).execute()
                    saved_count += 1
                    
            except Exception as e:
                error_msg = f"Error saving price list {price_list.get('id', 'unknown')}: {e}"
                print(f"  ⚠️  {error_msg}")
                errors.append(error_msg)
        
        print(f"✅ Synced {len(price_lists)} price lists: {saved_count} new, {updated_count} updated")
        
        return jsonify({
            'success': True,
            'total': len(price_lists),
            'saved': saved_count,
            'updated': updated_count,
            'errors': errors
        })
        
    except Exception as e:
        print(f"❌ Error syncing price lists: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/sync-product-prices', methods=['POST'])
def api_sync_product_prices():
    """Sync all product prices (products in price lists) from Douano to Supabase."""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    if not supabase_client:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    douano_client = get_douano_client()
    if not douano_client:
        return jsonify({'error': 'Douano client not configured'}), 500
    
    try:
        print("🔄 Starting product prices sync...")
        
        # Fetch all price list items from Douano (paginated)
        all_items = []
        page = 1
        per_page = 100
        
        while True:
            response = douano_client.pricing.get_sales_price_list_items(per_page=per_page, page=page)
            result = response.get('result', {})
            items = result.get('data', [])
            
            if not items:
                break
            
            all_items.extend(items)
            
            # Check if there are more pages
            if result.get('current_page') >= result.get('last_page', 1):
                break
            
            page += 1
            time.sleep(0.1)  # Rate limiting
        
        saved_count = 0
        updated_count = 0
        errors = []
        
        for item in all_items:
            try:
                # Extract relevant data
                product = item.get('product', {})
                price_list = item.get('sales_price_list', {})
                
                product_id = product.get('id')
                price_list_id = price_list.get('id')
                price = item.get('price')
                
                if not product_id or not price_list_id or price is None:
                    continue
                
                price_data = {
                    'product_id': product_id,
                    'price_list_id': price_list_id,
                    'price': float(price),
                    'cost_price': float(item['cost_price']) if item.get('cost_price') else None,
                    'currency': item.get('currency', 'EUR'),
                    'is_active': item.get('is_active', True),
                    'last_sync_at': datetime.now().isoformat()
                }
                
                # Check if price already exists
                existing = supabase_client.table('product_prices').select('id').eq('product_id', product_id).eq('price_list_id', price_list_id).execute()
                
                if existing.data:
                    # Update existing
                    supabase_client.table('product_prices').update(price_data).eq('id', existing.data[0]['id']).execute()
                    updated_count += 1
                else:
                    # Insert new
                    supabase_client.table('product_prices').insert(price_data).execute()
                    saved_count += 1
                    
            except Exception as e:
                error_msg = f"Error saving price for product {item.get('product', {}).get('id', 'unknown')}: {e}"
                print(f"  ⚠️  {error_msg}")
                errors.append(error_msg)
        
        print(f"✅ Synced {len(all_items)} product prices: {saved_count} new, {updated_count} updated")
        
        return jsonify({
            'success': True,
            'total': len(all_items),
            'saved': saved_count,
            'updated': updated_count,
            'errors': errors
        })
        
    except Exception as e:
        print(f"❌ Error syncing product prices: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/sync-company-pricing', methods=['POST'])
def api_sync_company_pricing():
    """Sync company-specific pricing (price lists and discounts) from Douano to Supabase."""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    if not supabase_client:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    douano_client = get_douano_client()
    if not douano_client:
        return jsonify({'error': 'Douano client not configured'}), 500
    
    try:
        print("🔄 Starting company pricing sync...")
        
        # Get all companies from Douano (paginated)
        all_companies = []
        page = 1
        per_page = 50
        
        while True:
            response = douano_client.crm.get_companies(filter_by_is_customer=True, per_page=per_page, page=page)
            result = response.get('result', {})
            companies = result.get('data', [])
            
            if not companies:
                break
            
            all_companies.extend(companies)
            
            # Check if there are more pages
            if result.get('current_page') >= result.get('last_page', 1):
                break
            
            page += 1
            time.sleep(0.1)  # Rate limiting
        
        saved_count = 0
        updated_count = 0
        errors = []
        
        for company in all_companies:
            try:
                # Get detailed company info (includes commercial settings)
                company_detail = douano_client.crm.get_company(company['id'])
                company_data = company_detail.get('result', {})
                
                # Extract commercial information
                commercial = company_data.get('commercial', {})
                
                company_id = company_data.get('id')
                if not company_id:
                    continue
                
                # Check if company exists in our companies table
                existing_company = supabase_client.table('companies').select('id').eq('company_id', company_id).execute()
                
                if not existing_company.data:
                    # Skip if company doesn't exist in our system yet
                    continue
                
                our_company_id = existing_company.data[0]['id']
                
                pricing_data = {
                    'company_id': our_company_id,
                    'price_list_id': commercial.get('sales_price_list_id'),
                    'standard_discount_percentage': float(commercial.get('standard_discount_percentage', 0)),
                    'extra_discount_percentage': float(commercial.get('extra_discount_percentage', 0)),
                    'financial_discount_percentage': float(commercial.get('financial_discount_percentage', 0)),
                    'payment_term_days': commercial.get('payment_term', 30),
                    'is_active': company_data.get('is_active', True),
                    'last_sync_at': datetime.now().isoformat()
                }
                
                # Check if pricing already exists
                existing = supabase_client.table('company_pricing').select('id').eq('company_id', our_company_id).execute()
                
                if existing.data:
                    # Update existing
                    supabase_client.table('company_pricing').update(pricing_data).eq('id', existing.data[0]['id']).execute()
                    updated_count += 1
                else:
                    # Insert new
                    supabase_client.table('company_pricing').insert(pricing_data).execute()
                    saved_count += 1
                    
            except Exception as e:
                error_msg = f"Error saving pricing for company {company.get('id', 'unknown')}: {e}"
                print(f"  ⚠️  {error_msg}")
                errors.append(error_msg)
        
        print(f"✅ Synced company pricing for {len(all_companies)} companies: {saved_count} new, {updated_count} updated")
        
        return jsonify({
            'success': True,
            'total': len(all_companies),
            'saved': saved_count,
            'updated': updated_count,
            'errors': errors
        })
        
    except Exception as e:
        print(f"❌ Error syncing company pricing: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/sync-all-products', methods=['POST'])
def api_sync_all_products():
    """Convenience endpoint to sync all product-related data in sequence."""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    if not supabase_client:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    douano_client = get_douano_client()
    if not douano_client:
        return jsonify({'error': 'Douano client not configured'}), 500
    
    try:
        print("🚀 Starting full product & pricing sync...")
        
        results = {
            'categories': {'synced': 0, 'new': 0, 'updated': 0, 'errors': 0},
            'products': {'synced': 0, 'new': 0, 'updated': 0, 'errors': 0},
            'price_lists': {'synced': 0, 'new': 0, 'updated': 0, 'errors': 0},
            'product_prices': {'synced': 0, 'new': 0, 'updated': 0, 'errors': 0},
            'company_pricing': {'synced': 0, 'new': 0, 'updated': 0, 'errors': 0}
        }
        
        # 1. Sync categories
        print("\n📚 Step 1/5: Syncing product categories...")
        try:
            response = douano_client.products.get_product_categories(per_page=100)
            print(f"📥 Categories response type: {type(response)}")
            print(f"📥 Categories response keys: {response.keys() if isinstance(response, dict) else 'Not a dict'}")
            
            # Handle different response formats
            if isinstance(response, dict):
                if 'result' in response:
                    categories = response['result'].get('data', [])
                elif 'data' in response:
                    categories = response['data']
                else:
                    categories = []
                    print(f"⚠️ Unexpected response structure: {list(response.keys())}")
            else:
                categories = []
                print(f"⚠️ Response is not a dict: {type(response)}")
            
            print(f"📦 Found {len(categories)} categories")
            
            for category in categories:
                try:
                    supabase_client.table('product_categories').upsert({
                        'douano_id': category['id'],
                        'name': category.get('name'),
                        'code': category.get('code'),
                        'parent_category_id': category.get('parent_category_id'),
                        'douano_created_at': category.get('created_at'),
                        'douano_updated_at': category.get('updated_at'),
                        'last_synced_at': datetime.now().isoformat()
                    }, on_conflict='douano_id').execute()
                    results['categories']['synced'] += 1
                except Exception as e:
                    results['categories']['errors'] += 1
                    if results['categories']['errors'] <= 3:  # Only print first 3 errors
                        print(f"  ⚠️  Error saving category {category.get('id')}: {e}")
            print(f"✅ Synced {results['categories']['synced']} categories")
        except Exception as e:
            print(f"❌ Error syncing categories: {e}")
            results['categories']['error'] = str(e)
        
        # 2. Sync products
        print("\n📦 Step 2/5: Syncing products...")
        try:
            page = 1
            while True:
                response = douano_client.products.get_products(per_page=100, page=page)
                
                # Handle different response formats
                if isinstance(response, dict):
                    if 'result' in response:
                        products = response['result'].get('data', [])
                    elif 'data' in response:
                        products = response['data']
                    else:
                        products = []
                else:
                    products = []
                
                if not products:
                    break
                    
                print(f"📦 Processing page {page}: {len(products)} products")
                
                for product in products:
                    try:
                        supabase_client.table('products').upsert({
                            'douano_id': product['id'],
                            'name': product.get('name'),
                            'code': product.get('code'),
                            'category_id': product.get('category_id'),
                            'unit': product.get('unit'),
                            'description': product.get('description'),
                            'is_active': product.get('is_active', True),
                            'douano_created_at': product.get('created_at'),
                            'douano_updated_at': product.get('updated_at'),
                            'last_synced_at': datetime.now().isoformat()
                        }, on_conflict='douano_id').execute()
                        results['products']['synced'] += 1
                    except Exception as e:
                        results['products']['errors'] += 1
                        if results['products']['errors'] <= 3:  # Only print first 3 errors
                            print(f"  ⚠️  Error saving product {product.get('id')}: {e}")
                page += 1
            print(f"✅ Synced {results['products']['synced']} products")
        except Exception as e:
            print(f"❌ Error syncing products: {e}")
            results['products']['error'] = str(e)
        
        # 3. Sync price lists
        print("\n💰 Step 3/5: Syncing price lists...")
        try:
            response = douano_client.pricing.get_sales_price_lists(per_page=100)
            print(f"📥 Price lists response type: {type(response)}")
            
            # Handle different response formats
            if isinstance(response, dict):
                if 'result' in response:
                    price_lists = response['result'].get('data', [])
                elif 'data' in response:
                    price_lists = response['data']
                else:
                    price_lists = []
                    print(f"⚠️ Unexpected price list response structure: {list(response.keys())}")
            else:
                price_lists = []
                print(f"⚠️ Price list response is not a dict: {type(response)}")
            
            print(f"💰 Found {len(price_lists)} price lists")
            
            for price_list in price_lists:
                try:
                    supabase_client.table('sales_price_lists').upsert({
                        'douano_id': price_list['id'],
                        'name': price_list.get('name'),
                        'description': price_list.get('description'),
                        'is_active': price_list.get('is_active', True),
                        'douano_created_at': price_list.get('created_at'),
                        'douano_updated_at': price_list.get('updated_at'),
                        'last_synced_at': datetime.now().isoformat()
                    }, on_conflict='douano_id').execute()
                    results['price_lists']['synced'] += 1
                except Exception as e:
                    results['price_lists']['errors'] += 1
            print(f"✅ Synced {results['price_lists']['synced']} price lists")
        except Exception as e:
            print(f"❌ Error syncing price lists: {e}")
            results['price_lists']['error'] = str(e)
        
        # 4. Sync product prices
        print("\n💵 Step 4/5: Syncing product prices...")
        try:
            page = 1
            while page <= 10:  # Limit to 10 pages for safety
                response = douano_client.pricing.get_sales_price_list_items(per_page=100, page=page)
                
                # Handle different response formats
                if isinstance(response, dict):
                    if 'result' in response:
                        items = response['result'].get('data', [])
                    elif 'data' in response:
                        items = response['data']
                    else:
                        items = []
                else:
                    items = []
                
                if not items:
                    break
                    
                print(f"💵 Processing page {page}: {len(items)} price list items")
                
                for item in items:
                    try:
                        supabase_client.table('product_prices').upsert({
                            'douano_id': item['id'],
                            'price_list_id': item.get('sales_price_list_id'),
                            'product_id': item.get('product_id'),
                            'price': item.get('price'),
                            'last_synced_at': datetime.now().isoformat()
                        }, on_conflict='douano_id').execute()
                        results['product_prices']['synced'] += 1
                    except Exception as e:
                        results['product_prices']['errors'] += 1
                page += 1
            print(f"✅ Synced {results['product_prices']['synced']} product prices")
        except Exception as e:
            print(f"❌ Error syncing product prices: {e}")
            results['product_prices']['error'] = str(e)
        
        # 5. Sync company pricing
        print("\n🏢 Step 5/5: Syncing company pricing...")
        try:
            page = 1
            while page <= 10:  # Limit to 10 pages for safety
                response = douano_client.crm.get_companies(filter_by_is_customer=True, per_page=100, page=page)
                
                # Handle different response formats
                if isinstance(response, dict):
                    if 'result' in response:
                        companies = response['result'].get('data', [])
                    elif 'data' in response:
                        companies = response['data']
                    else:
                        companies = []
                else:
                    companies = []
                
                if not companies:
                    break
                    
                print(f"🏢 Processing page {page}: {len(companies)} companies")
                
                for company in companies:
                    try:
                        # Small delay to avoid rate limiting
                        time.sleep(0.2)
                        
                        # Get detailed company info
                        company_detail = douano_client.crm.get_company(company['id'])
                        
                        # Handle different response formats
                        if isinstance(company_detail, dict):
                            if 'result' in company_detail:
                                detail_data = company_detail['result']
                            else:
                                detail_data = company_detail
                        else:
                            detail_data = {}
                        
                        # Check if this company exists in our DB
                        existing = supabase_client.table('companies').select('id').eq('douano_company_id', company['id']).execute()
                        if existing.data:
                            company_id = existing.data[0]['id']
                            supabase_client.table('company_pricing').upsert({
                                'company_id': company_id,
                                'price_list_id': detail_data.get('sales_price_list_id'),
                                'standard_discount': detail_data.get('standard_discount', 0),
                                'extra_discount': detail_data.get('extra_discount', 0),
                                'financial_discount': detail_data.get('financial_discount', 0),
                                'payment_term_days': detail_data.get('payment_term_days', 30),
                                'last_synced_at': datetime.now().isoformat()
                            }, on_conflict='company_id').execute()
                            results['company_pricing']['synced'] += 1
                    except Exception as e:
                        results['company_pricing']['errors'] += 1
                page += 1
            print(f"✅ Synced {results['company_pricing']['synced']} company pricing records")
        except Exception as e:
            print(f"❌ Error syncing company pricing: {e}")
            results['company_pricing']['error'] = str(e)
        
        print("\n✅ Full product & pricing sync complete!")
        
        return jsonify({
            'success': True,
            'message': 'Full product & pricing sync complete',
            'results': results
        })
        
    except Exception as e:
        print(f"❌ Error in full sync: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


_background_task_running = False

@app.route('/api/refresh-company-metrics', methods=['POST'])
def api_refresh_company_metrics():
    """Manually trigger recalculation of company metrics from invoice data - runs in background.
    Admin only.
    """
    global _background_task_running
    
    if not is_admin():
        return jsonify({'error': 'Admin access required'}), 403
    
    if _background_task_running:
        return jsonify({
            'success': False,
            'message': 'A background task is already running. Please wait for it to complete.'
        }), 429
    
    try:
        import threading
        
        print("🔄 Starting background company metrics refresh...")
        _background_task_running = True
        
        # Run in background thread
        def background_metrics_update():
            global _background_task_running
            try:
                recalculate_company_metrics_from_invoices(max_companies=9999)  # Process all
                print("✅ Background metrics update complete!")
            except Exception as e:
                print(f"❌ Background metrics update failed: {e}")
            finally:
                _background_task_running = False
        
        thread = threading.Thread(target=background_metrics_update)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Metrics recalculation started in background. This will take 2-3 minutes. Do NOT click other buttons while it runs.'
        })
    
    except Exception as e:
        print(f"Error refreshing company metrics: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/2025-sales-stats', methods=['GET'])
def api_2025_sales_stats():
    """Get statistics about 2025 sales data in Supabase."""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500
        
        # Get total count
        count_result = supabase_client.table('sales_2025').select('id', count='exact').execute()
        total_count = count_result.count if hasattr(count_result, 'count') else len(count_result.data)
        
        # Get sum of revenue (ex-VAT from line items)
        amounts_result = supabase_client.table('sales_2025').select('total_amount, balance, is_paid, invoice_data').range(0, 9999).execute()

        # Calculate revenue from line items (ex-VAT) - matches DUANO's "Omzet"
        total_revenue = 0
        for r in amounts_result.data:
            invoice_data = r.get('invoice_data') or {}
            line_items = invoice_data.get('invoice_line_items') or []
            line_revenue = sum(float(item.get('revenue') or 0) for item in line_items)
            total_revenue += line_revenue if line_revenue > 0 else float(r.get('total_amount') or 0)

        total_balance = sum(float(r.get('balance') or 0) for r in amounts_result.data)
        paid_count = sum(1 for r in amounts_result.data if r.get('is_paid'))
        
        # Get unique companies (use range to get more records)
        companies_result = supabase_client.table('sales_2025').select('company_id').range(0, 9999).execute()
        unique_companies = len(set(r.get('company_id') for r in companies_result.data if r.get('company_id')))
        
        stats = {
            'total_invoices': total_count,
            'total_revenue': round(total_revenue, 2),
            'total_outstanding': round(total_balance, 2),
            'paid_invoices': paid_count,
            'unpaid_invoices': total_count - paid_count,
            'unique_companies': unique_companies
        }
        
        return jsonify(stats)
        
    except Exception as e:
        print(f"Error getting 2025 sales stats: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/sales-2024')
def sales_2024():
    """2024 Sales Data page"""
    if not is_logged_in():
        return redirect(url_for('login'))
    
    return render_template('sales_2024.html')


@app.route('/api/sync-2024-invoices', methods=['POST'])
def api_sync_2024_invoices():
    """
    Sync all 2024 invoices from Douano API to Supabase.
    Admin only - requires DUANO authentication.
    """
    if not is_admin():
        return jsonify({'error': 'Admin access required', 'success': False}), 403
    
    try:
        # Fetch all 2024 invoices from Douano API
        all_invoices = []
        page = 1
        per_page = 100
        
        while True:
            params = {
                'per_page': per_page,
                'page': page,
                'filter_by_start_date': '2024-01-01',
                'filter_by_end_date': '2024-12-31'
            }
            
            print(f"Fetching 2024 invoices page {page}...")
            raw_response, error = make_paginated_api_request('/api/public/v1/trade/sales-invoices', params=params)
            
            if error:
                print(f"API Error: {error}")
                return jsonify({'error': f'API request failed: {error}'}), 500
            
            result = raw_response.get('result', {})
            invoices = result.get('data', [])
            
            if not invoices:
                break
                
            all_invoices.extend(invoices)
            print(f"Fetched {len(invoices)} invoices from page {page}")
            
            # Check if there are more pages
            pagination = result.get('pagination', {})
            if page >= pagination.get('total_pages', 1):
                break
                
            page += 1
        
        print(f"Total 2024 invoices fetched: {len(all_invoices)}")
        
        if not all_invoices:
            return jsonify({'success': True, 'message': 'No 2024 invoices found', 'total_fetched': 0, 'saved': 0, 'updated': 0, 'errors': 0})
        
        # Save to Supabase
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500
        
        saved_count = 0
        updated_count = 0
        error_count = 0
        
        for idx, invoice in enumerate(all_invoices):
            # Add small delay every 50 invoices to prevent resource exhaustion
            if idx > 0 and idx % 50 == 0:
                time.sleep(0.1)
            
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    # Extract key fields
                    company = invoice.get('company', {})
                    if isinstance(company, dict):
                        company_id = company.get('id')
                        company_name = company.get('name') or company.get('public_name')
                    else:
                        company_id = None
                        company_name = None
                    
                    # Get the amount - prefer line item revenue (ex-VAT)
                    line_items = invoice.get('invoice_line_items', [])
                    if line_items:
                        amount = sum(float(item.get('revenue') or 0) for item in line_items)
                    else:
                        amount = 0

                    # Fall back to total_amount only if no line items
                    if amount == 0:
                        amount = float(invoice.get('total_amount') or invoice.get('balance') or 0)
                    
                    record = {
                        'invoice_id': invoice.get('id'),
                        'invoice_data': invoice,
                        'company_id': company_id,
                        'company_name': company_name,
                        'invoice_number': invoice.get('invoice_number') or invoice.get('number'),
                        'invoice_date': invoice.get('date'),
                        'due_date': invoice.get('due_date'),
                        'total_amount': amount if amount else None,
                        'balance': invoice.get('balance'),
                        'is_paid': invoice.get('balance', 0) == 0
                    }
                    
                    # Check if record exists
                    existing = supabase_client.table('sales_2024').select('id').eq('invoice_id', record['invoice_id']).execute()
                    
                    if existing.data:
                        # Update
                        record['updated_at'] = datetime.now().isoformat()
                        supabase_client.table('sales_2024').update(record).eq('invoice_id', record['invoice_id']).execute()
                        updated_count += 1
                    else:
                        # Insert
                        supabase_client.table('sales_2024').insert(record).execute()
                        saved_count += 1
                    
                    break  # Success, exit retry loop
                    
                except Exception as e:
                    retry_count += 1
                    if retry_count >= max_retries:
                        error_count += 1
                        # Only print non-resource errors after all retries
                        if "Resource temporarily unavailable" not in str(e):
                            print(f"❌ Error saving invoice {invoice.get('id')} after {max_retries} retries: {e}")
                        break
                    # Exponential backoff
                    time.sleep(0.05 * (2 ** retry_count))
        
        # Recalculate company metrics to update frontend display
        if saved_count > 0 or updated_count > 0:
            print("📊 Updating company metrics...")
            recalculate_company_metrics_from_invoices()
        
        return jsonify({
            'success': True,
            'message': f'Successfully synced {len(all_invoices)} 2024 invoices',
            'total_fetched': len(all_invoices),
            'saved': saved_count,
            'updated': updated_count,
            'errors': error_count
        })
        
    except Exception as e:
        print(f"❌ Error in 2024 sync: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/2024-sales-stats', methods=['GET'])
def api_2024_sales_stats():
    """Get statistics about 2024 sales data in Supabase."""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500
        
        # Get total count
        count_result = supabase_client.table('sales_2024').select('id', count='exact').execute()
        total_count = count_result.count if hasattr(count_result, 'count') else len(count_result.data)
        
        # Get sum of revenue (ex-VAT from line items)
        amounts_result = supabase_client.table('sales_2024').select('total_amount, balance, is_paid, invoice_data').range(0, 9999).execute()

        # Calculate revenue from line items (ex-VAT) - matches DUANO's "Omzet"
        total_revenue = 0
        for r in amounts_result.data:
            invoice_data = r.get('invoice_data') or {}
            line_items = invoice_data.get('invoice_line_items') or []
            line_revenue = sum(float(item.get('revenue') or 0) for item in line_items)
            total_revenue += line_revenue if line_revenue > 0 else float(r.get('total_amount') or 0)

        total_balance = sum(float(r.get('balance') or 0) for r in amounts_result.data)
        paid_count = sum(1 for r in amounts_result.data if r.get('is_paid'))
        
        # Get unique companies (use range to get more records)
        companies_result = supabase_client.table('sales_2024').select('company_id').range(0, 9999).execute()
        unique_companies = len(set(r.get('company_id') for r in companies_result.data if r.get('company_id')))
        
        stats = {
            'total_invoices': total_count,
            'total_revenue': round(total_revenue, 2),
            'total_outstanding': round(total_balance, 2),
            'paid_invoices': paid_count,
            'unpaid_invoices': total_count - paid_count,
            'unique_companies': unique_companies
        }
        
        return jsonify(stats)
        
    except Exception as e:
        print(f"Error getting 2024 sales stats: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/data')
def data():
    """Unified Data Analysis page"""
    if not is_logged_in():
        return redirect(url_for('index'))

    # Mapbox API key for map view
    mapbox_api_key = "pk.eyJ1IjoiaGVuZHJpa3l1Z2VuIiwiYSI6ImNtY24zZnB4YTAwNTYybnMzNGVpemZxdGEifQ.HIpLMTGycSiEsf7ytxaSJg"

    return render_template('data.html', mapbox_api_key=mapbox_api_key)


@app.route('/map')
def companies_map():
    """Map view of all companies with filtering"""
    if not is_logged_in():
        return redirect(url_for('index'))

    # Mapbox API key
    mapbox_api_key = "pk.eyJ1IjoiaGVuZHJpa3l1Z2VuIiwiYSI6ImNtY24zZnB4YTAwNTYybnMzNGVpemZxdGEifQ.HIpLMTGycSiEsf7ytxaSJg"

    return render_template('map.html', mapbox_api_key=mapbox_api_key)


@app.route('/retailer-details/<int:company_id>')
def retailer_details(company_id):
    """Detailed analytics page for major retailers"""
    if not is_logged_in():
        return redirect(url_for('login'))
    
    # Get year parameter
    year = request.args.get('year', '2025')
    
    return render_template('retailer_details.html', company_id=company_id, year=year)


def safe_parse_aantal(value):
    """Safely parse 'aantal' field, handling NULL strings and invalid values."""
    if value is None or value == 'NULL' or value == '':
        return 0
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


@app.route('/api/ai-query-retailer', methods=['POST'])
def api_ai_query_retailer():
    """AI-powered natural language queries for retailer data using Gemini."""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        data = request.json
        question = data.get('question', '').strip()
        company_id = data.get('company_id')
        current_filters = data.get('current_filters', {})
        filtered_data = data.get('filtered_data', [])
        
        if not question:
            return jsonify({'success': False, 'error': 'Question is required'})
        
        if not gemini_client:
            return jsonify({'success': False, 'error': 'Gemini AI is not configured. Please set GEMINI_API_KEY.'})
        
        # Prepare data summary for AI context
        if len(filtered_data) > 0:
            # Calculate aggregated statistics
            total_units = sum(safe_parse_aantal(row.get('aantal', 0)) for row in filtered_data)
            unique_customers = len(set(row.get('naam_klant') for row in filtered_data if row.get('naam_klant')))
            unique_products = len(set(row.get('product') for row in filtered_data if row.get('product')))
            unique_flavors = len(set(row.get('smaak') for row in filtered_data if row.get('smaak')))
            
            # Product breakdown
            product_stats = {}
            for row in filtered_data:
                product = row.get('product', 'Unknown')
                product_stats[product] = product_stats.get(product, 0) + safe_parse_aantal(row.get('aantal', 0))
            
            # Flavor breakdown
            flavor_stats = {}
            for row in filtered_data:
                flavor = row.get('smaak', 'Unknown')
                flavor_stats[flavor] = flavor_stats.get(flavor, 0) + safe_parse_aantal(row.get('aantal', 0))
            
            # Location breakdown
            location_stats = {}
            for row in filtered_data:
                location = row.get('naam_klant', 'Unknown')
                if location and location != 'Unknown':
                    if location not in location_stats:
                        location_stats[location] = {
                            'units': 0,
                            'city': row.get('stad', ''),
                            'province': row.get('provincie', ''),
                            'chain': row.get('keten', '')
                        }
                    location_stats[location]['units'] += safe_parse_aantal(row.get('aantal', 0))
            
            # Province breakdown
            province_stats = {}
            for row in filtered_data:
                prov = row.get('provincie', 'Unknown')
                province_stats[prov] = province_stats.get(prov, 0) + safe_parse_aantal(row.get('aantal', 0))
            
            # Chain breakdown
            chain_stats = {}
            for row in filtered_data:
                chain = row.get('keten', 'Unknown')
                chain_stats[chain] = chain_stats.get(chain, 0) + safe_parse_aantal(row.get('aantal', 0))
            
            # Month breakdown
            month_stats = {}
            for row in filtered_data:
                month = row.get('maand', 'Unknown')
                month_stats[month] = month_stats.get(month, 0) + safe_parse_aantal(row.get('aantal', 0))
            
            # Create context for AI
            context = f"""
You are analyzing sales data for a major retailer. Here is the current dataset summary:

CURRENT FILTERS APPLIED:
- Year: {current_filters.get('year', 'all')}
- Month: {current_filters.get('month', 'all')}
- Product: {current_filters.get('product', 'all')}
- Flavor: {current_filters.get('flavor', 'all')}
- Chain: {current_filters.get('chain', 'all')}
- Province: {current_filters.get('province', 'all')}

OVERALL STATISTICS:
- Total records: {len(filtered_data)}
- Total units sold: {total_units:,}
- Unique locations/customers: {unique_customers}
- Unique products: {unique_products}
- Unique flavors: {unique_flavors}

TOP 10 PRODUCTS (by units):
{chr(10).join(f"  - {prod}: {units:,} units" for prod, units in sorted(product_stats.items(), key=lambda x: x[1], reverse=True)[:10])}

TOP 10 FLAVORS (by units):
{chr(10).join(f"  - {flav}: {units:,} units" for flav, units in sorted(flavor_stats.items(), key=lambda x: x[1], reverse=True)[:10])}

TOP 10 LOCATIONS (by units):
{chr(10).join(f"  - {loc} ({stats['city']}, {stats['province']}): {stats['units']:,} units" for loc, stats in sorted(location_stats.items(), key=lambda x: x[1]['units'], reverse=True)[:10])}

BY PROVINCE:
{chr(10).join(f"  - {prov}: {units:,} units" for prov, units in sorted(province_stats.items(), key=lambda x: x[1], reverse=True))}

BY CHAIN:
{chr(10).join(f"  - {chain}: {units:,} units" for chain, units in sorted(chain_stats.items(), key=lambda x: x[1], reverse=True))}

BY MONTH:
{chr(10).join(f"  - {month}: {units:,} units" for month, units in sorted(month_stats.items(), key=lambda x: x[1], reverse=True))}

USER QUESTION: {question}

Please provide a clear, concise answer based on the data above. Include specific numbers and insights. Format your response in a conversational way.
"""
        
            # Use Gemini with more efficient model
            response = gemini_client.models.generate_content(
                model='gemini-1.5-flash',
                contents=context,
                config={
                    'temperature': 0.7,
                    'max_output_tokens': 500
                }
            )
            
            answer = response.text if hasattr(response, 'text') else str(response)
            
            return jsonify({
                'success': True,
                'answer': answer,
                'data_points': len(filtered_data)
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No data available to analyze'
            })
            
    except Exception as e:
        print(f"Error in AI query: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/alerts')
def alerts():
    """Pattern disruption alerts for sales team."""
    if not is_logged_in():
        return redirect(url_for('index'))
    return render_template('alerts.html')


@app.route('/api/2024-companies-analysis', methods=['GET'])
def api_2024_companies_analysis():
    """Get detailed company analysis from 2024 sales data."""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500
        
        # Get all invoice data with raw JSON (fetch in batches to bypass limits)
        all_invoices = []
        batch_size = 1000
        offset = 0
        
        while True:
            batch_result = supabase_client.table('sales_2024').select('*').range(offset, offset + batch_size - 1).execute()
            
            if not batch_result.data:
                break
                
            all_invoices.extend(batch_result.data)
            print(f"DEBUG: Fetched batch {offset//batch_size + 1}: {len(batch_result.data)} records (Total: {len(all_invoices)})")
            
            # If we got less than batch_size records, we've reached the end
            if len(batch_result.data) < batch_size:
                break
                
            offset += batch_size
            
            # Safety break to avoid infinite loop
            if offset > 50000:
                print("DEBUG: Safety break - reached 50k records")
                break
        
        # Create a mock result object
        class MockResult:
            def __init__(self, data):
                self.data = data
        
        invoices_result = MockResult(all_invoices)
        
        if not invoices_result.data:
            return jsonify({'companies': [], 'total_companies': 0})
        
        print(f"DEBUG: Total invoices in sales_2024 table: {len(invoices_result.data)}")
        
        # Also check the count using the count query
        count_check = supabase_client.table('sales_2024').select('id', count='exact').execute()
        actual_count = count_check.count if hasattr(count_check, 'count') else len(count_check.data)
        print(f"DEBUG: Actual count from count query: {actual_count}")
        
        # Process company data from raw invoice JSON
        companies_data = {}
        processed_invoices = 0
        skipped_invoices = 0
        
        for invoice in invoices_result.data:
            invoice_data = invoice.get('invoice_data', {})
            company_info = invoice_data.get('company', {})
            
            # Use company_id from the extracted field if company info is missing
            company_id = None
            if company_info and company_info.get('id'):
                company_id = company_info.get('id')
            elif invoice.get('company_id'):
                company_id = invoice.get('company_id')
                # If we don't have company_info but have company_id, create basic info
                if not company_info:
                    company_info = {
                        'id': company_id,
                        'name': invoice.get('company_name') or 'Unknown Company'
                    }
            else:
                # Skip invoices without any company identification
                continue
            
            # Initialize company if not exists
            if company_id not in companies_data:
                companies_data[company_id] = {
                    'id': company_id,
                    'name': company_info.get('name') or company_info.get('public_name') or 'Unknown Company',
                    'vat_number': company_info.get('vat_number', ''),
                    'email': company_info.get('email', ''),
                    'phone': company_info.get('phone_number', ''),
                    'website': company_info.get('website', ''),
                    'address': {
                        'street': company_info.get('address_line1', ''),
                        'street2': company_info.get('address_line2', ''),
                        'city': company_info.get('city', ''),
                        'postal_code': company_info.get('post_code', ''),
                        'country': company_info.get('country', {}).get('name', '') if company_info.get('country') else ''
                    },
                    'contact_person': company_info.get('contact_person', {}).get('name', '') if company_info.get('contact_person') else '',
                    'industry': company_info.get('industry', ''),
                    'company_size': company_info.get('company_size', ''),
                    'invoices': [],
                    'total_revenue': 0,
                    'invoice_count': 0,
                    'average_invoice_value': 0,
                    'first_invoice_date': None,
                    'last_invoice_date': None,
                    'payment_terms': set(),
                    'currencies': set()
                }
            
            # Add invoice data - calculate revenue from line items (ex-VAT)
            company = companies_data[company_id]
            line_items = invoice_data.get('invoice_line_items') or []
            line_revenue = sum(float(item.get('revenue') or 0) for item in line_items)
            invoice_amount = line_revenue if line_revenue > 0 else float(invoice.get('total_amount') or 0)
            invoice_date = invoice.get('invoice_date')

            company['invoices'].append({
                'id': invoice.get('invoice_id'),
                'number': invoice.get('invoice_number'),
                'date': invoice_date,
                'amount': invoice_amount,
                'balance': float(invoice.get('balance') or 0),
                'is_paid': invoice.get('is_paid', False)
            })

            company['total_revenue'] += invoice_amount
            company['invoice_count'] += 1
            
            # Track dates
            if invoice_date:
                if not company['first_invoice_date'] or invoice_date < company['first_invoice_date']:
                    company['first_invoice_date'] = invoice_date
                if not company['last_invoice_date'] or invoice_date > company['last_invoice_date']:
                    company['last_invoice_date'] = invoice_date
            
            # Extract additional details from raw data
            if invoice_data.get('payment_terms'):
                company['payment_terms'].add(str(invoice_data.get('payment_terms')))
            if invoice_data.get('currency'):
                company['currencies'].add(invoice_data.get('currency'))
        
        # Finalize company data
        companies_list = []
        for company in companies_data.values():
            company['average_invoice_value'] = round(company['total_revenue'] / company['invoice_count'], 2) if company['invoice_count'] > 0 else 0
            company['payment_terms'] = list(company['payment_terms'])
            company['currencies'] = list(company['currencies'])
            company['total_revenue'] = round(company['total_revenue'], 2)
            
            # Sort invoices by date (newest first)
            company['invoices'].sort(key=lambda x: x['date'] or '1900-01-01', reverse=True)
            
            companies_list.append(company)
        
        # Sort companies by total revenue (highest first)
        companies_list.sort(key=lambda x: x['total_revenue'], reverse=True)
        
        return jsonify({
            'companies': companies_list,
            'total_companies': len(companies_list),
            'total_revenue': sum(c['total_revenue'] for c in companies_list),
            'total_invoices': sum(c['invoice_count'] for c in companies_list)
        })
        
    except Exception as e:
        print(f"Error getting 2024 companies analysis: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/2025-companies-analysis', methods=['GET'])
def api_2025_companies_analysis():
    """Get detailed company analysis from 2025 sales data."""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500
        
        # Get all invoice data with raw JSON (fetch in batches to bypass limits)
        all_invoices = []
        batch_size = 1000
        offset = 0
        
        while True:
            batch_result = supabase_client.table('sales_2025').select('*').range(offset, offset + batch_size - 1).execute()
            
            if not batch_result.data:
                break
                
            all_invoices.extend(batch_result.data)
            print(f"DEBUG: Fetched batch {offset//batch_size + 1}: {len(batch_result.data)} records (Total: {len(all_invoices)})")
            
            # If we got less than batch_size records, we've reached the end
            if len(batch_result.data) < batch_size:
                break
                
            offset += batch_size
            
            # Safety break to avoid infinite loop
            if offset > 50000:
                print("DEBUG: Safety break - reached 50k records")
                break
        
        # Create a mock result object
        class MockResult:
            def __init__(self, data):
                self.data = data
        
        invoices_result = MockResult(all_invoices)
        
        if not invoices_result.data:
            return jsonify({'companies': [], 'total_companies': 0})
        
        print(f"DEBUG: Total invoices in sales_2025 table: {len(invoices_result.data)}")
        
        # Process company data from raw invoice JSON
        companies_data = {}
        
        for invoice in invoices_result.data:
            invoice_data = invoice.get('invoice_data', {})
            company_info = invoice_data.get('company', {})
            
            # Use company_id from the extracted field if company info is missing
            company_id = None
            if company_info and company_info.get('id'):
                company_id = company_info.get('id')
            elif invoice.get('company_id'):
                company_id = invoice.get('company_id')
                # If we don't have company_info but have company_id, create basic info
                if not company_info:
                    company_info = {
                        'id': company_id,
                        'name': invoice.get('company_name') or 'Unknown Company'
                    }
            else:
                # Skip invoices without any company identification
                continue
            
            # Initialize company if not exists
            if company_id not in companies_data:
                companies_data[company_id] = {
                    'id': company_id,
                    'name': company_info.get('name') or company_info.get('public_name') or 'Unknown Company',
                    'vat_number': company_info.get('vat_number', ''),
                    'email': company_info.get('email', ''),
                    'phone': company_info.get('phone_number', ''),
                    'website': company_info.get('website', ''),
                    'address': {
                        'street': company_info.get('address_line1', ''),
                        'street2': company_info.get('address_line2', ''),
                        'city': company_info.get('city', ''),
                        'postal_code': company_info.get('post_code', ''),
                        'country': company_info.get('country', {}).get('name', '') if company_info.get('country') else ''
                    },
                    'contact_person': company_info.get('contact_person', {}).get('name', '') if company_info.get('contact_person') else '',
                    'industry': company_info.get('industry', ''),
                    'company_size': company_info.get('company_size', ''),
                    'invoices': [],
                    'total_revenue': 0,
                    'invoice_count': 0,
                    'average_invoice_value': 0,
                    'first_invoice_date': None,
                    'last_invoice_date': None,
                    'payment_terms': set(),
                    'currencies': set()
                }
            
            # Add invoice data - calculate revenue from line items (ex-VAT)
            company = companies_data[company_id]
            line_items = invoice_data.get('invoice_line_items') or []
            line_revenue = sum(float(item.get('revenue') or 0) for item in line_items)
            invoice_amount = line_revenue if line_revenue > 0 else float(invoice.get('total_amount') or 0)
            invoice_date = invoice.get('invoice_date')

            company['invoices'].append({
                'id': invoice.get('invoice_id'),
                'number': invoice.get('invoice_number'),
                'date': invoice_date,
                'amount': invoice_amount,
                'balance': float(invoice.get('balance') or 0),
                'is_paid': invoice.get('is_paid', False)
            })

            company['total_revenue'] += invoice_amount
            company['invoice_count'] += 1
            
            # Track dates
            if invoice_date:
                if not company['first_invoice_date'] or invoice_date < company['first_invoice_date']:
                    company['first_invoice_date'] = invoice_date
                if not company['last_invoice_date'] or invoice_date > company['last_invoice_date']:
                    company['last_invoice_date'] = invoice_date
            
            # Extract additional details from raw data
            if invoice_data.get('payment_terms'):
                company['payment_terms'].add(str(invoice_data.get('payment_terms')))
            if invoice_data.get('currency'):
                company['currencies'].add(invoice_data.get('currency'))
        
        # Finalize company data
        companies_list = []
        for company in companies_data.values():
            company['average_invoice_value'] = round(company['total_revenue'] / company['invoice_count'], 2) if company['invoice_count'] > 0 else 0
            company['payment_terms'] = list(company['payment_terms'])
            company['currencies'] = list(company['currencies'])
            company['total_revenue'] = round(company['total_revenue'], 2)
            
            # Sort invoices by date (newest first)
            company['invoices'].sort(key=lambda x: x['date'] or '1900-01-01', reverse=True)
            
            companies_list.append(company)
        
        # Sort companies by total revenue (highest first)
        companies_list.sort(key=lambda x: x['total_revenue'], reverse=True)
        
        total_invoices_calculated = sum(c['invoice_count'] for c in companies_list)
        print(f"DEBUG 2025: Raw records fetched: {len(invoices_result.data)}")
        print(f"DEBUG 2025: Companies processed: {len(companies_list)}")
        print(f"DEBUG 2025: Total invoices calculated: {total_invoices_calculated}")
        
        return jsonify({
            'companies': companies_list,
            'total_companies': len(companies_list),
            'total_revenue': sum(c['total_revenue'] for c in companies_list),
            'total_invoices': total_invoices_calculated
        })
        
    except Exception as e:
        print(f"Error getting 2025 companies analysis: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/companies-with-alerts', methods=['GET'])
def api_companies_with_alerts():
    """Get companies with their active alerts for planning."""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500
        
        # Get all companies
        companies_result = supabase_client.table('companies').select('*').execute()
        companies = companies_result.data if companies_result.data else []
        print(f"📊 Found {len(companies)} companies")
        
        # Get all active alerts
        alerts_result = supabase_client.table('customer_alerts').select('*').eq('status', 'active').execute()
        alerts = alerts_result.data if alerts_result.data else []
        print(f"🔔 Found {len(alerts)} active alerts")
        
        # Debug: Show sample alert priorities
        if alerts:
            priorities = set(a.get('priority') for a in alerts[:10])
            print(f"📋 Sample alert priorities: {priorities}")
        
        # Create a map of company_id to alerts
        company_alerts_map = {}
        for alert in alerts:
            company_id = alert.get('company_id')
            if company_id not in company_alerts_map:
                company_alerts_map[company_id] = []
            company_alerts_map[company_id].append({
                'id': alert.get('id'),
                'alert_type': alert.get('alert_type'),
                'priority': alert.get('priority', '').lower() if alert.get('priority') else 'low',
                'description': alert.get('description'),
                'recommendation': alert.get('recommendation'),
                'created_at': alert.get('created_at')
            })
        
        # Enrich companies with alert data
        for company in companies:
            company_id = company.get('company_id')
            if company_id in company_alerts_map:
                company['alerts'] = company_alerts_map[company_id]
                company['has_alerts'] = True
                company['alert_count'] = len(company_alerts_map[company_id])
                # Get highest priority (normalize to lowercase for frontend)
                priorities = [a['priority'].lower() if a['priority'] else 'low' for a in company_alerts_map[company_id]]
                if 'critical' in priorities:
                    company['highest_priority'] = 'critical'
                elif 'high' in priorities:
                    company['highest_priority'] = 'high'
                elif 'medium' in priorities:
                    company['highest_priority'] = 'medium'
                else:
                    company['highest_priority'] = 'low'
            else:
                company['alerts'] = []
                company['has_alerts'] = False
                company['alert_count'] = 0
                company['highest_priority'] = None
        
        # Filter only companies with valid geocoding
        valid_companies = [c for c in companies if c.get('latitude') and c.get('longitude')]
        
        return jsonify({
            'success': True,
            'companies': valid_companies,
            'total_companies': len(valid_companies),
            'companies_with_alerts': len([c for c in valid_companies if c.get('has_alerts')]),
            'total_alerts': len(alerts)
        })
        
    except Exception as e:
        print(f"Error getting companies with alerts: {e}")
        return jsonify({'error': str(e)}), 500


def extract_flavours_from_invoice(invoice_data):
    """Extract flavour names from invoice line items.

    Yugen product names follow patterns like:
    - "Box Yugen Ginger Lemon Bio Cans 24x32cl"
    - "Yugen Original Tonic Bio 24x32cl"
    - "Pallet Yugen Elderflower Bio Cans 24x32cl"

    Returns a list of unique flavour names.
    """
    if not invoice_data:
        return []

    line_items = invoice_data.get('invoice_line_items') or []
    flavours = set()

    # Known Yugen flavours to match against
    known_flavours = [
        'Ginger Lemon', 'Original Tonic', 'Elderflower', 'Yuzu Citrus',
        'Cucumber Mint', 'Hibiscus Rose', 'Grapefruit', 'Blood Orange',
        'Lemon', 'Lime', 'Apple Ginger', 'Passion Fruit', 'Mango',
        'Peach', 'Raspberry', 'Strawberry', 'Blueberry', 'Pomegranate'
    ]

    for item in line_items:
        product = item.get('product') or {}
        product_name = product.get('name') or item.get('description') or ''

        if not product_name:
            continue

        # Try to match known flavours first
        product_upper = product_name.upper()
        for flavour in known_flavours:
            if flavour.upper() in product_upper:
                flavours.add(flavour)
                break
        else:
            # Try to extract flavour from "Yugen [Flavour] Bio" pattern
            import re
            # Match pattern: Yugen <flavour words> Bio
            match = re.search(r'Yugen\s+([A-Za-z\s]+?)\s+Bio', product_name, re.IGNORECASE)
            if match:
                flavour_text = match.group(1).strip()
                # Clean up common prefixes/suffixes
                flavour_text = re.sub(r'^(Box|Pallet|Case)\s+', '', flavour_text, flags=re.IGNORECASE)
                if flavour_text and len(flavour_text) > 2:
                    flavours.add(flavour_text.title())

    return sorted(list(flavours))


@app.route('/api/companies-from-db', methods=['GET'])
def api_companies_from_db():
    """
    Get companies data calculated DIRECTLY from invoice tables.
    No external API calls - pure database aggregation.
    """
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500
        
        year_filter = request.args.get('year', '2026')
        print(f"📊 Loading companies from invoices for year: {year_filter}")

        # Step 1: Fetch ALL invoices from the database (fast - data already there)
        all_invoices = []
        invoices_2026_count = 0
        invoices_2025_count = 0
        invoices_2024_count = 0

        if year_filter in ['2026', 'combined']:
            # Fetch all 2026 invoices in batches with retry logic
            offset = 0
            batch_size = 1000
            max_retries = 3
            while True:
                for retry in range(max_retries):
                    try:
                        result = supabase_client.table('sales_2026').select(
                            'company_id, company_name, total_amount, invoice_date, invoice_data'
                        ).range(offset, offset + batch_size - 1).execute()
                        break  # Success
                    except Exception as e:
                        if retry < max_retries - 1:
                            print(f"  ⚠️ Retry {retry + 1} for 2026 batch at offset {offset}: {e}")
                            time.sleep(0.5 * (retry + 1))
                        else:
                            raise
                if not result.data:
                    break
                batch_count = len(result.data)
                invoices_2026_count += batch_count
                for inv in result.data:
                    inv['year'] = '2026'
                all_invoices.extend(result.data)
                print(f"  📄 Fetched 2026 batch: {batch_count} invoices (total: {invoices_2026_count})")
                if batch_count < batch_size:
                    break
                offset += batch_size
                time.sleep(0.1)

        if year_filter in ['2025', 'combined']:
            # Fetch all 2025 invoices in batches with retry logic
            offset = 0
            batch_size = 1000
            max_retries = 3
            while True:
                for retry in range(max_retries):
                    try:
                        result = supabase_client.table('sales_2025').select(
                            'company_id, company_name, total_amount, invoice_date, invoice_data'
                        ).range(offset, offset + batch_size - 1).execute()
                        break  # Success
                    except Exception as e:
                        if retry < max_retries - 1:
                            print(f"  ⚠️ Retry {retry + 1} for 2025 batch at offset {offset}: {e}")
                            time.sleep(0.5 * (retry + 1))  # Exponential backoff
                        else:
                            raise
                if not result.data:
                    break
                batch_count = len(result.data)
                invoices_2025_count += batch_count
                for inv in result.data:
                    inv['year'] = '2025'
                all_invoices.extend(result.data)
                print(f"  📄 Fetched 2025 batch: {batch_count} invoices (total: {invoices_2025_count})")
                if batch_count < batch_size:
                    break
                offset += batch_size
                time.sleep(0.1)  # Small delay between batches
        
        if year_filter in ['2024', 'combined']:
            # Fetch all 2024 invoices in batches with retry logic
            offset = 0
            batch_size = 1000
            max_retries = 3
            while True:
                for retry in range(max_retries):
                    try:
                        result = supabase_client.table('sales_2024').select(
                            'company_id, company_name, total_amount, invoice_date, invoice_data'
                        ).range(offset, offset + batch_size - 1).execute()
                        break  # Success
                    except Exception as e:
                        if retry < max_retries - 1:
                            print(f"  ⚠️ Retry {retry + 1} for 2024 batch at offset {offset}: {e}")
                            time.sleep(0.5 * (retry + 1))
                        else:
                            raise
                if not result.data:
                    break
                batch_count = len(result.data)
                invoices_2024_count += batch_count
                for inv in result.data:
                    inv['year'] = '2024'
                all_invoices.extend(result.data)
                print(f"  📄 Fetched 2024 batch: {batch_count} invoices (total: {invoices_2024_count})")
                if batch_count < batch_size:
                    break
                offset += batch_size
        
        print(f"✅ Total invoices loaded: {len(all_invoices)} (2024: {invoices_2024_count}, 2025: {invoices_2025_count}, 2026: {invoices_2026_count})")
        
        # Debug: Check first invoice for revenue calculation
        if all_invoices:
            sample = all_invoices[0]
            inv_data = sample.get('invoice_data') or {}
            line_items = inv_data.get('invoice_line_items') or []
            line_revenue = sum(float(item.get('revenue') or 0) for item in line_items)
            payable = inv_data.get('payable_amount_without_financial_discount')
            print(f"📋 Sample invoice: line_item_revenue={line_revenue} (ex-VAT), payable={payable} (incl-VAT), total_amount={sample.get('total_amount')}")
        
        # Step 2: Aggregate invoices by company (pure Python - very fast)
        company_metrics = {}
        for inv in all_invoices:
            cid = inv.get('company_id')
            if not cid:
                continue
            
            if cid not in company_metrics:
                # Get VAT from invoice_data if available
                invoice_data = inv.get('invoice_data') or {}
                company_info = invoice_data.get('company') or {}
                vat_number = company_info.get('vat_number')
                
                company_metrics[cid] = {
                    'company_id': cid,
                    'name': inv.get('company_name', 'Unknown'),
                    'vat_number': vat_number,
                    'total_revenue': 0.0,
                    'invoice_count': 0,
                    'invoices': [],
                    'revenue_2024': 0.0,
                    'count_2024': 0,
                    'revenue_2025': 0.0,
                    'count_2025': 0,
                    'revenue_2026': 0.0,
                    'count_2026': 0,
                    'latest_invoice_date': None,
                    'latest_invoice_data': None,
                }
            
            # Get the amount - DUANO's "Omzet" is the sum of line item revenues (ex-VAT)
            invoice_data = inv.get('invoice_data') or {}
            
            # Calculate revenue from line items (this matches DUANO's "Omzet" which is ex-VAT)
            line_items = invoice_data.get('invoice_line_items') or []
            amount = sum(float(item.get('revenue') or 0) for item in line_items)
            
            # If no line items or revenue is 0, fall back to total_amount (but this would be incl-VAT)
            if amount == 0:
                amount = float(inv.get('total_amount') or 0)
            
            company_metrics[cid]['total_revenue'] += amount
            company_metrics[cid]['invoice_count'] += 1
            company_metrics[cid]['invoices'].append(inv.get('invoice_date'))

            # Track latest invoice for flavour extraction
            inv_date = inv.get('invoice_date')
            if inv_date and (not company_metrics[cid]['latest_invoice_date'] or inv_date > company_metrics[cid]['latest_invoice_date']):
                company_metrics[cid]['latest_invoice_date'] = inv_date
                company_metrics[cid]['latest_invoice_data'] = invoice_data

            # Track by year
            inv_year = inv.get('year')
            if inv_year == '2024':
                company_metrics[cid]['revenue_2024'] += amount
                company_metrics[cid]['count_2024'] += 1
            elif inv_year == '2025':
                company_metrics[cid]['revenue_2025'] += amount
                company_metrics[cid]['count_2025'] += 1
            else:
                company_metrics[cid]['revenue_2026'] += amount
                company_metrics[cid]['count_2026'] += 1
        
        # Step 3: Try to enrich with company details from companies table (optional)
        # Fetch ALL companies with pagination (Supabase default limit is 1000)
        company_details = {}
        try:
            offset = 0
            batch_size = 1000
            while True:
                comp_result = supabase_client.table('companies').select(
                    'id, company_id, email, phone_number, website, latitude, longitude, '
                    'city, country_name, address_line1, post_code, company_tag, '
                    'company_categories, raw_company_data, public_name, customer_since, '
                    'assigned_salesperson, contact_person_name, geocoded_address, flavour_prices, '
                    'addresses, lead_source, lead_status, channel, language, priority, province, '
                    'sub_type, business_type, parent_company, suppliers, crm_notes, activations, '
                    'products_proposed, products_sampled, products_listed, products_won, '
                    'contact_person_role, contact_2_name, contact_2_role, contact_2_email, contact_2_phone, '
                    'contact_3_name, contact_3_role, contact_3_email, contact_3_phone, '
                    'imported_from_crm, crm_import_date, external_account_number, crm_review_status'
                ).range(offset, offset + batch_size - 1).execute()

                if not comp_result.data:
                    break

                for c in comp_result.data:
                    # Skip merged CRM imports (their data was transferred to target company)
                    if c.get('crm_review_status') == 'merged':
                        continue
                    # Key by both id and company_id for flexible lookup
                    # (sales tables may use either depending on how data was imported)
                    company_details[c['company_id']] = c
                    if c.get('id') and c['id'] != c['company_id']:
                        company_details[c['id']] = c

                if len(comp_result.data) < batch_size:
                    break
                offset += batch_size

            print(f"📊 Loaded {len(company_details)} companies for enrichment (indexed by id and company_id)")
        except Exception as e:
            print(f"Could not fetch company details (optional): {e}")
        
        # Step 4: Build final company list
        companies_list = []
        total_revenue = 0
        total_invoices = 0
        
        for cid, metrics in company_metrics.items():
            # Get dates
            dates = [d for d in metrics['invoices'] if d]
            first_date = min(dates) if dates else None
            last_date = max(dates) if dates else None
            
            # Get optional enrichment data
            details = company_details.get(cid, {})
            
            # Use year-specific metrics if filtering
            if year_filter == '2024':
                revenue = metrics['revenue_2024']
                invoice_count = metrics['count_2024']
            elif year_filter == '2025':
                revenue = metrics['revenue_2025']
                invoice_count = metrics['count_2025']
            elif year_filter == '2026':
                revenue = metrics['revenue_2026']
                invoice_count = metrics['count_2026']
            else:
                revenue = metrics['total_revenue']
                invoice_count = metrics['invoice_count']
            
            # Skip if no invoices in selected period
            if invoice_count == 0:
                continue
            
            avg_invoice = revenue / invoice_count if invoice_count > 0 else 0
            
            # Get the Supabase row ID (used for notes, trips, etc.)
            # This is different from company_id which is the Duano ID
            supabase_id = details.get('id')  # Supabase auto-increment id
            duano_company_id = details.get('company_id') or cid  # Duano company_id

            company_data = {
                'id': cid,
                'company_id': cid,  # Keep using invoice company_id for consistency
                'supabase_id': supabase_id,  # Supabase row ID - use this for notes/trips
                'name': metrics['name'],
                'public_name': details.get('public_name'),
                'customer_since': details.get('customer_since'),
                'vat_number': metrics.get('vat_number'),
                'email': details.get('email'),
                'phone': details.get('phone_number'),
                'website': details.get('website'),
                'company_tag': details.get('company_tag'),
                'contact_person': details.get('contact_person_name'),
                'assigned_salesperson': details.get('assigned_salesperson'),
                'lead_source': details.get('lead_source'),
                # Categories for filtering
                'company_categories': details.get('company_categories'),
                'raw_company_data': details.get('raw_company_data'),
                # Geocoding
                'latitude': details.get('latitude'),
                'longitude': details.get('longitude'),
                # Metrics - calculated fresh from invoices
                'total_revenue': round(revenue, 2),
                'invoice_count': invoice_count,
                'average_invoice_value': round(avg_invoice, 2),
                'first_invoice_date': first_date,
                'last_invoice_date': last_date,
                'address': {
                    'city': details.get('city', ''),
                    'country': details.get('country_name', ''),
                    'street': details.get('address_line1', ''),
                    'postal_code': details.get('post_code', '')
                },
                'addresses': details.get('addresses', []),  # All company addresses (delivery locations, etc.)
                'geocoded_address': details.get('geocoded_address'),
                # Flavours from latest invoice
                'current_flavours': extract_flavours_from_invoice(metrics.get('latest_invoice_data')),
                # Flavour prices (per-flavour retail prices)
                'flavour_prices': details.get('flavour_prices', {}) or {},
                # CRM import fields
                'lead_status': details.get('lead_status'),
                'channel': details.get('channel'),
                'language': details.get('language'),
                'priority': details.get('priority'),
                'province': details.get('province'),
                'sub_type': details.get('sub_type'),
                'business_type': details.get('business_type'),
                'parent_company': details.get('parent_company'),
                'suppliers': details.get('suppliers', []),
                'crm_notes': details.get('crm_notes'),
                'activations': details.get('activations'),
                'external_account_number': details.get('external_account_number'),
                # Product tracking
                'products_proposed': details.get('products_proposed', []),
                'products_sampled': details.get('products_sampled', []),
                'products_listed': details.get('products_listed', []),
                'products_won': details.get('products_won', []),
                # Additional contacts
                'contact_person_role': details.get('contact_person_role'),
                'contact_2_name': details.get('contact_2_name'),
                'contact_2_role': details.get('contact_2_role'),
                'contact_2_email': details.get('contact_2_email'),
                'contact_2_phone': details.get('contact_2_phone'),
                'contact_3_name': details.get('contact_3_name'),
                'contact_3_role': details.get('contact_3_role'),
                'contact_3_email': details.get('contact_3_email'),
                'contact_3_phone': details.get('contact_3_phone'),
                # Import tracking
                'imported_from_crm': details.get('imported_from_crm', False),
                'crm_import_date': details.get('crm_import_date')
            }

            # Add year breakdown for combined view
            if year_filter == 'combined':
                company_data['years_data'] = {
                    '2024': {
                        'total_revenue': round(metrics['revenue_2024'], 2),
                        'invoice_count': metrics['count_2024']
                    },
                    '2025': {
                        'total_revenue': round(metrics['revenue_2025'], 2),
                        'invoice_count': metrics['count_2025']
                    },
                    '2026': {
                        'total_revenue': round(metrics['revenue_2026'], 2),
                        'invoice_count': metrics['count_2026']
                    }
                }
            
            companies_list.append(company_data)
            total_revenue += revenue
            total_invoices += invoice_count
        
        # Sort by revenue descending
        companies_list.sort(key=lambda x: x['total_revenue'], reverse=True)

        # Step 5: Fetch alerts for all companies and attach to company data
        alerts_by_company = {}
        try:
            alerts_result = supabase_client.table('customer_alerts').select(
                'company_id, alert_type, priority, description'
            ).eq('status', 'active').neq('alert_type', 'PAYMENT_ISSUES').execute()

            if alerts_result.data:
                for alert in alerts_result.data:
                    cid = alert['company_id']
                    if cid not in alerts_by_company:
                        alerts_by_company[cid] = []
                    alerts_by_company[cid].append({
                        'type': alert['alert_type'],
                        'priority': alert['priority'],
                        'description': alert.get('description', '')
                    })
                print(f"📢 Found {len(alerts_result.data)} active alerts for {len(alerts_by_company)} companies")
        except Exception as e:
            print(f"Could not fetch alerts (optional): {e}")

        # Attach alerts to companies
        for company in companies_list:
            company['alerts'] = alerts_by_company.get(company['id'], [])

        # Step 6: Add CRM-imported companies that don't have invoices yet
        existing_company_ids = set(c['company_id'] for c in companies_list)
        crm_companies_added = 0
        try:
            # Fetch companies that were imported from CRM but don't have invoices
            for details in company_details.values():
                cid = details.get('company_id')
                if cid and cid not in existing_company_ids and details.get('imported_from_crm'):
                    existing_company_ids.add(cid)  # Prevent duplicates
                    crm_company = {
                        'id': cid,
                        'company_id': cid,
                        'supabase_id': details.get('id'),
                        'name': details.get('name') or details.get('public_name') or 'Unknown',
                        'public_name': details.get('public_name'),
                        'customer_since': details.get('customer_since'),
                        'email': details.get('email'),
                        'phone': details.get('phone_number'),
                        'website': details.get('website'),
                        'company_tag': details.get('company_tag'),
                        'contact_person': details.get('contact_person_name'),
                        'assigned_salesperson': details.get('assigned_salesperson'),
                        'lead_source': details.get('lead_source'),
                        'company_categories': details.get('company_categories'),
                        'raw_company_data': details.get('raw_company_data'),
                        'latitude': details.get('latitude'),
                        'longitude': details.get('longitude'),
                        'total_revenue': 0,
                        'invoice_count': 0,
                        'average_invoice_value': 0,
                        'first_invoice_date': None,
                        'last_invoice_date': None,
                        'address': {
                            'city': details.get('city', ''),
                            'country': details.get('country_name', ''),
                            'street': details.get('address_line1', ''),
                            'postal_code': details.get('post_code', '')
                        },
                        'addresses': details.get('addresses', []),
                        'geocoded_address': details.get('geocoded_address'),
                        'current_flavours': [],
                        'flavour_prices': {},
                        # CRM fields
                        'lead_status': details.get('lead_status'),
                        'channel': details.get('channel'),
                        'language': details.get('language'),
                        'priority': details.get('priority'),
                        'province': details.get('province'),
                        'sub_type': details.get('sub_type'),
                        'business_type': details.get('business_type'),
                        'parent_company': details.get('parent_company'),
                        'suppliers': details.get('suppliers', []),
                        'crm_notes': details.get('crm_notes'),
                        'activations': details.get('activations'),
                        'external_account_number': details.get('external_account_number'),
                        'products_proposed': details.get('products_proposed', []),
                        'products_sampled': details.get('products_sampled', []),
                        'products_listed': details.get('products_listed', []),
                        'products_won': details.get('products_won', []),
                        'contact_person_role': details.get('contact_person_role'),
                        'contact_2_name': details.get('contact_2_name'),
                        'contact_2_role': details.get('contact_2_role'),
                        'contact_2_email': details.get('contact_2_email'),
                        'contact_2_phone': details.get('contact_2_phone'),
                        'contact_3_name': details.get('contact_3_name'),
                        'contact_3_role': details.get('contact_3_role'),
                        'contact_3_email': details.get('contact_3_email'),
                        'contact_3_phone': details.get('contact_3_phone'),
                        'imported_from_crm': True,
                        'crm_import_date': details.get('crm_import_date'),
                        'alerts': []
                    }
                    companies_list.append(crm_company)
                    crm_companies_added += 1
            print(f"📥 Added {crm_companies_added} CRM-imported companies without invoices")
        except Exception as e:
            print(f"Could not add CRM companies: {e}")

        # Re-sort after adding CRM companies (by revenue, then by name for 0-revenue)
        companies_list.sort(key=lambda x: (-x['total_revenue'], x.get('name', '').lower()))

        print(f"✅ Returning {len(companies_list)} companies, {total_invoices} invoices, €{round(total_revenue, 2)} revenue")

        return jsonify({
            'companies': companies_list,
            'total_companies': len(companies_list),
            'total_revenue': round(total_revenue, 2),
            'total_invoices': total_invoices,
            'year_filter': year_filter,
            'debug_raw_invoice_count': len(all_invoices)
        })
        
    except Exception as e:
        print(f"❌ Error in companies from DB: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/companies/<int:company_id>/contact', methods=['PUT'])
def api_update_company_contact(company_id):
    """Update company contact details (phone, email, website, contact person, salesperson)."""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Build update payload with only provided fields
        update_fields = {}

        if 'contact_person_name' in data:
            update_fields['contact_person_name'] = data['contact_person_name']
        if 'email' in data:
            update_fields['email'] = data['email']
        if 'phone_number' in data:
            update_fields['phone_number'] = data['phone_number']
        if 'website' in data:
            update_fields['website'] = data['website']
        if 'assigned_salesperson' in data:
            update_fields['assigned_salesperson'] = data['assigned_salesperson']
        if 'lead_source' in data:
            update_fields['lead_source'] = data['lead_source']

        if not update_fields:
            return jsonify({'error': 'No valid fields to update'}), 400

        # Update in Supabase
        result = supabase_client.table('companies').update(update_fields).eq('company_id', company_id).execute()

        if result.data:
            print(f"✅ Updated company {company_id} contact details: {update_fields}")
            return jsonify({'success': True, 'updated': update_fields})
        else:
            return jsonify({'error': 'Company not found'}), 404

    except Exception as e:
        print(f"Error updating company contact: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/company-invoices/<int:company_id>', methods=['GET'])
def api_company_invoices(company_id):
    """Get all invoices for a specific company."""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500
        
        year_filter = request.args.get('year', '2026')
        invoices = []

        # Fetch invoices based on year filter
        if year_filter == 'combined':
            # Get from all years
            for year in ['2024', '2025', '2026']:
                result = supabase_client.table(f'sales_{year}').select('*').eq('company_id', company_id).execute()
                for invoice in result.data:
                    invoice['year'] = int(year)
                    invoices.append(invoice)
        else:
            # Get from specific year
            if year_filter in ['2024', '2025', '2026']:
                result = supabase_client.table(f'sales_{year_filter}').select('*').eq('company_id', company_id).execute()
                for invoice in result.data:
                    invoice['year'] = int(year_filter)
                    invoices.append(invoice)
            else:
                # Default to 2026 if invalid year
                result = supabase_client.table('sales_2026').select('*').eq('company_id', company_id).execute()
                for invoice in result.data:
                    invoice['year'] = 2026
                    invoices.append(invoice)
        
        # Process invoices for frontend
        processed_invoices = []
        for invoice in invoices:
            # Handle None values safely
            total_amount = invoice.get('total_amount')
            balance = invoice.get('balance')

            # Extract address from invoice_data (if available)
            invoice_data = invoice.get('invoice_data', {}) or {}
            if isinstance(invoice_data, str):
                try:
                    import json
                    invoice_data = json.loads(invoice_data)
                except:
                    invoice_data = {}

            # Get delivery address from invoice data
            # Priority: delivery_address (enriched) > address.full_details > address
            delivery_address = None

            # First try the enriched delivery_address we added
            if invoice_data.get('delivery_address') and isinstance(invoice_data.get('delivery_address'), dict):
                addr = invoice_data['delivery_address']
                delivery_address = {
                    'name': addr.get('name', ''),
                    'street': addr.get('address_line1') or addr.get('street', ''),
                    'city': addr.get('city', ''),
                    'post_code': addr.get('post_code', ''),
                    'country': addr.get('country', {}).get('name') if isinstance(addr.get('country'), dict) else addr.get('country', '')
                }
            # Then try address with full_details
            elif invoice_data.get('address') and isinstance(invoice_data.get('address'), dict):
                addr = invoice_data['address']
                # Check for full_details first (enriched data)
                if addr.get('full_details') and isinstance(addr.get('full_details'), dict):
                    details = addr['full_details']
                    delivery_address = {
                        'name': details.get('name', addr.get('name', '')),
                        'street': details.get('address_line1') or details.get('street', ''),
                        'city': details.get('city', ''),
                        'post_code': details.get('post_code', ''),
                        'country': details.get('country', {}).get('name') if isinstance(details.get('country'), dict) else details.get('country', '')
                    }
                else:
                    # Use basic address info
                    delivery_address = {
                        'name': addr.get('name', ''),
                        'street': addr.get('address_line1') or addr.get('street', ''),
                        'city': addr.get('city', ''),
                        'post_code': addr.get('post_code', ''),
                        'country': addr.get('country', {}).get('name') if isinstance(addr.get('country'), dict) else addr.get('country', '')
                    }

            processed_invoices.append({
                'id': invoice['id'],
                'number': invoice.get('invoice_number', invoice['id']),
                'date': invoice.get('invoice_date'),
                'amount': float(total_amount) if total_amount is not None else 0.0,
                'balance': float(balance) if balance is not None else 0.0,
                'is_paid': invoice.get('is_paid', True),
                'year': invoice.get('year', 2026),
                'delivery_address': delivery_address
            })
        
        # Sort by date descending
        processed_invoices.sort(key=lambda x: x['date'] or '', reverse=True)
        
        return jsonify({
            'invoices': processed_invoices,
            'total_invoices': len(processed_invoices),
            'company_id': company_id
        })
        
    except Exception as e:
        print(f"Error getting company invoices: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/major-retailer-detailed/<int:company_id>', methods=['GET'])
def api_major_retailer_detailed(company_id):
    """Get AGGREGATED data for major retailers from their specialized databases.
    Returns summaries instead of raw data to avoid timeouts with 85k+ records.
    """
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500
        
        import time as time_module
        start_time = time_module.time()
        time_limit = 25  # Stop before Gunicorn timeout
        
        # Map company IDs to their database tables
        MAJOR_RETAILERS = {
            'Delhaize': {
                'company_ids': [1324],
                'tables': ['Delhaize 2025', 'Delhaize 2024', 'Delhaize 2023', 'Delhaize 2022'],
                'company_name': 'Delhaize Le Lion/De Leeuw'
            },
            'Geers': {
                'company_ids': [1340],
                'tables': ['Geers 2025', 'Geers 2024', 'Geers 2023', 'Geers 2022'],
                'company_name': 'Dranken Geers NV'
            },
            'InterDrinks': {
                'company_ids': [9986],
                'tables': ['Inter Drinks 2025', 'Inter Drinks 2024', 'Inter Drinks 2023'],
                'company_name': 'SPRL Inter - Drinks'
            },
            'Biofresh': {
                'company_ids': [1213],
                'tables': ['Biofresh 2025', 'Biofresh 2024', 'Biofresh 2023', 'Biofresh 2022'],
                'company_name': 'Biofresh Belgium NV'
            },
            'Terroirist': {
                'company_ids': [1712],
                'tables': ['Terroirist 2025', 'Terroirist 2024'],
                'company_name': 'TERROIRIST CVBA'
            }
        }
        
        # Find which retailer this company belongs to
        retailer_key = None
        for key, config in MAJOR_RETAILERS.items():
            if company_id in config['company_ids']:
                retailer_key = key
                break
        
        if not retailer_key:
            return jsonify({'success': False, 'error': 'Not a major retailer'})
        
        retailer_config = MAJOR_RETAILERS[retailer_key]
        year_filter = request.args.get('year')
        
        # Aggregate data server-side instead of returning all raw records
        aggregated = {
            'by_product': {},
            'by_flavor': {},
            'by_month': {},
            'by_year': {},
            'by_customer': {},
            'by_city': {},
            'total_quantity': 0,
            'total_records': 0
        }
        
        tables_to_fetch = retailer_config['tables']
        if year_filter:
            tables_to_fetch = [t for t in tables_to_fetch if year_filter in t]
        
        for table_name in tables_to_fetch:
            # Check time limit
            if time_module.time() - start_time > time_limit:
                print(f"⚠️ Time limit reached, returning partial data")
                break
                
            try:
                print(f"📡 Aggregating data from {table_name}...")
                offset = 0
                batch_size = 1000
                table_records = 0
                
                while True:
                    # Check time limit
                    if time_module.time() - start_time > time_limit:
                        break
                    
                    result = supabase_client.table(table_name).select(
                        'aantal,jaar,maand,product,smaak,naam_klant,stad'
                    ).range(offset, offset + batch_size - 1).execute()
                    
                    if not result.data:
                        break
                    
                    # Aggregate in Python
                    for record in result.data:
                        # Handle 'NULL' strings and other invalid values
                        qty_val = record.get('aantal')
                        try:
                            qty = int(qty_val) if qty_val and str(qty_val).upper() != 'NULL' else 0
                        except (ValueError, TypeError):
                            qty = 0
                        
                        aggregated['total_quantity'] += qty
                        aggregated['total_records'] += 1
                        table_records += 1
                        
                        # By product
                        product = record.get('product') or 'Unknown'
                        if product not in aggregated['by_product']:
                            aggregated['by_product'][product] = 0
                        aggregated['by_product'][product] += qty
                        
                        # By flavor
                        flavor = record.get('smaak') or 'Unknown'
                        if flavor not in aggregated['by_flavor']:
                            aggregated['by_flavor'][flavor] = 0
                        aggregated['by_flavor'][flavor] += qty
                        
                        # By year
                        year = str(record.get('jaar') or 'Unknown')
                        if year not in aggregated['by_year']:
                            aggregated['by_year'][year] = 0
                        aggregated['by_year'][year] += qty
                        
                        # By month (year-month)
                        month = record.get('maand')
                        if year and month:
                            month_key = f"{year}-{str(month).zfill(2)}"
                            if month_key not in aggregated['by_month']:
                                aggregated['by_month'][month_key] = 0
                            aggregated['by_month'][month_key] += qty
                        
                        # By customer (top customers)
                        customer = record.get('naam_klant') or 'Unknown'
                        if customer not in aggregated['by_customer']:
                            aggregated['by_customer'][customer] = 0
                        aggregated['by_customer'][customer] += qty
                        
                        # By city
                        city = record.get('stad') or 'Unknown'
                        if city not in aggregated['by_city']:
                            aggregated['by_city'][city] = 0
                        aggregated['by_city'][city] += qty
                    
                    if len(result.data) < batch_size:
                        break
                    offset += batch_size
                
                print(f"  ✅ Aggregated {table_records:,} records from {table_name}")
                        
            except Exception as e:
                print(f"Error fetching {table_name}: {e}")
                continue
        
        # Sort and limit aggregations for response
        def top_items(d, limit=50):
            return dict(sorted(d.items(), key=lambda x: x[1], reverse=True)[:limit])
        
        result = {
            'success': True,
            'retailer_name': retailer_config['company_name'],
            'retailer_key': retailer_key,
            'total_records': aggregated['total_records'],
            'total_quantity': aggregated['total_quantity'],
            'by_product': top_items(aggregated['by_product'], 100),
            'by_flavor': top_items(aggregated['by_flavor'], 50),
            'by_year': dict(sorted(aggregated['by_year'].items())),
            'by_month': dict(sorted(aggregated['by_month'].items())),
            'by_customer': top_items(aggregated['by_customer'], 100),
            'by_city': top_items(aggregated['by_city'], 50),
        }
        
        print(f"✅ Returning aggregated data for {retailer_config['company_name']}: {aggregated['total_records']:,} records, {aggregated['total_quantity']:,} units")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error getting detailed retailer data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/major-retailer/<int:company_id>', methods=['GET'])
def api_major_retailer_data(company_id):
    """Get detailed data for major retailers from their specialized databases."""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500
        
        # Map company IDs to their database tables
        # These are the major retailers with specialized databases
        MAJOR_RETAILERS = {
            # Delhaize Le Lion/De Leeuw
            'Delhaize': {
                'company_ids': [1324],
                'tables': ['Delhaize 2025', 'Delhaize 2024', 'Delhaize 2023', 'Delhaize 2022'],
                'company_name': 'Delhaize Le Lion/De Leeuw',
                'vat_number': 'BE0402206045'
            },
            # Dranken Geers NV
            'Geers': {
                'company_ids': [1340],
                'tables': ['Geers 2025', 'Geers 2024', 'Geers 2023', 'Geers 2022'],
                'company_name': 'Dranken Geers NV',
                'vat_number': 'BE0433309292'
            },
            # SPRL Inter - Drinks
            'InterDrinks': {
                'company_ids': [9986],
                'tables': ['Inter Drinks 2025', 'Inter Drinks 2024', 'Inter Drinks 2023'],
                'company_name': 'SPRL Inter - Drinks',
                'vat_number': 'BE0433262574'
            },
            # Biofresh Belgium NV
            'Biofresh': {
                'company_ids': [1213],
                'tables': ['Biofresh 2025', 'Biofresh 2024', 'Biofresh 2023', 'Biofresh 2022'],
                'company_name': 'Biofresh Belgium NV',
                'vat_number': 'BE0438873629'
            },
            # TERROIRIST CVBA
            'Terroirist': {
                'company_ids': [1712],
                'tables': ['Terroirist 2025', 'Terroirist 2024'],
                'company_name': 'TERROIRIST CVBA',
                'vat_number': 'BE0695559284'
            }
        }
        
        # Find which retailer this company belongs to
        retailer_key = None
        for key, config in MAJOR_RETAILERS.items():
            if company_id in config['company_ids']:
                retailer_key = key
                break
        
        if not retailer_key:
            return jsonify({'is_major_retailer': False})
        
        retailer_config = MAJOR_RETAILERS[retailer_key]
        
        # Fetch data from all years for this retailer
        all_data = []
        stats_by_year = {}
        
        for table_name in retailer_config['tables']:
            try:
                print(f"📡 Fetching ALL data from {table_name}...")
                
                # Fetch ALL data efficiently with pagination
                # Select only the fields we need (not SELECT *)
                table_data = []
                offset = 0
                batch_size = 1000
                
                while True:
                    result = supabase_client.table(table_name).select(
                        'source,code_klant,naam_klant,adres_straat_huisnr,postcode,stad,land,provincie,'
                        'tel_nr,email,verantwoordelijke,aantal,week,maand,jaar,product,smaak,verpakking,'
                        'douane_klant_naam,douane_klant_nr,douane_bedrijfs_cat,keten,type_zaak'
                    ).range(offset, offset + batch_size - 1).execute()
                    
                    if not result.data or len(result.data) == 0:
                        break
                    
                    table_data.extend(result.data)
                    print(f"  📦 Batch {offset//batch_size + 1}: {len(result.data)} records")
                    
                    # If we got less than batch_size, we've reached the end
                    if len(result.data) < batch_size:
                        break
                    
                    offset += batch_size
                
                if table_data:
                    year = table_name.split()[-1]  # Extract year from table name
                    
                    print(f"✅ Loaded {len(table_data)} total records from {table_name}")
                    
                    # Calculate stats for this year using helper function
                    total_quantity = sum(safe_parse_aantal(row.get('aantal', 0)) for row in table_data)
                    unique_customers = len(set(row.get('naam_klant') for row in table_data if row.get('naam_klant')))
                    unique_products = len(set(row.get('product') for row in table_data if row.get('product')))
                    
                    stats_by_year[year] = {
                        'total_quantity': total_quantity,
                        'unique_customers': unique_customers,
                        'unique_products': unique_products,
                        'total_records': len(table_data)
                    }
                    
                    # Add year to each row
                    for row in table_data:
                        row['_year'] = year
                        all_data.append(row)
                        
            except Exception as e:
                print(f"Error fetching {table_name}: {e}")
                continue
        
        # Aggregate statistics
        total_quantity = sum(stats.get('total_quantity', 0) for stats in stats_by_year.values())
        
        # Product breakdown
        product_stats = {}
        for row in all_data:
            product = row.get('product', 'Unknown')
            if product not in product_stats:
                product_stats[product] = {'total': 0, 'by_year': {}}
            
            quantity = safe_parse_aantal(row.get('aantal', 0))
            product_stats[product]['total'] += quantity
            
            year = row.get('_year', 'Unknown')
            if year not in product_stats[product]['by_year']:
                product_stats[product]['by_year'][year] = 0
            product_stats[product]['by_year'][year] += quantity
        
        # Top products
        top_products = sorted(product_stats.items(), key=lambda x: x[1]['total'], reverse=True)[:10]
        
        # Customer breakdown (end customers)
        customer_stats = {}
        for row in all_data:
            customer = row.get('naam_klant', 'Unknown')
            if customer and customer != 'Unknown':
                if customer not in customer_stats:
                    customer_stats[customer] = {
                        'total': 0,
                        'city': row.get('stad', ''),
                        'province': row.get('provincie', ''),
                        'type': row.get('type_zaak', '')
                    }
                quantity = safe_parse_aantal(row.get('aantal', 0))
                customer_stats[customer]['total'] += quantity
        
        top_customers = sorted(customer_stats.items(), key=lambda x: x[1]['total'], reverse=True)[:15]
        
        return jsonify({
            'is_major_retailer': True,
            'retailer_name': retailer_config['company_name'],
            'retailer_key': retailer_key,
            'stats_by_year': stats_by_year,
            'total_quantity': total_quantity,
            'total_records': len(all_data),
            'product_stats': dict(top_products),
            'top_customers': [{'name': name, **stats} for name, stats in top_customers],
            'available_years': list(stats_by_year.keys())
        })
        
    except Exception as e:
        print(f"Error getting major retailer data: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/alerts', methods=['GET'])
def api_get_alerts():
    """
    Fetch stored alerts from database with optional filtering.
    Much faster than recalculating - use this for regular page loads.
    """
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500
        
        # Get query parameters for filtering
        status = request.args.get('status', 'active')
        priority = request.args.get('priority')
        alert_type = request.args.get('type')
        
        # Build query
        query = supabase_client.table('customer_alerts').select('*')
        
        # Apply filters
        if status:
            query = query.eq('status', status)
        if priority:
            query = query.eq('priority', priority)
        if alert_type:
            query = query.eq('alert_type', alert_type)
        
        # Order by priority and date
        query = query.order('priority', desc=True).order('created_at', desc=True)
        
        # Execute query
        result = query.execute()
        alerts = result.data
        
        # Fetch raw_company_data for each alert's company
        # Build a mapping of company_id to raw_company_data for efficiency
        company_ids = list(set([alert.get('company_id') for alert in alerts if alert.get('company_id')]))
        
        company_data_map = {}
        if company_ids:
            try:
                # Fetch all companies in one query
                companies_result = supabase_client.table('companies').select('company_id, raw_company_data').in_('company_id', company_ids).execute()
                for company in companies_result.data:
                    company_data_map[company['company_id']] = company.get('raw_company_data')
            except Exception as e:
                print(f"Error fetching company data: {e}")
        
        # Add raw_company_data to each alert
        for alert in alerts:
            company_id = alert.get('company_id')
            if company_id and company_id in company_data_map:
                alert['raw_company_data'] = company_data_map[company_id]
            else:
                alert['raw_company_data'] = None
        summary = {
            'total_alerts': len(alerts),
            'high_priority': len([a for a in alerts if a['priority'] == 'HIGH']),
            'medium_priority': len([a for a in alerts if a['priority'] == 'MEDIUM']),
            'low_priority': len([a for a in alerts if a['priority'] == 'LOW']),
            'by_type': {}
        }
        
        for alert in alerts:
            alert_type = alert['alert_type']
            if alert_type not in summary['by_type']:
                summary['by_type'][alert_type] = 0
            summary['by_type'][alert_type] += 1
        
        # Get most recent analysis date
        analysis_date = alerts[0]['analysis_date'] if alerts else datetime.now().isoformat()
        
        return jsonify({
            'alerts': alerts,
            'summary': summary,
            'analysis_date': analysis_date,
            'from_cache': True
        })
        
    except Exception as e:
        error_msg = str(e)
        print(f"Error fetching alerts: {error_msg}")
        
        # Check if table doesn't exist
        if 'does not exist' in error_msg or '42P01' in error_msg:
            return jsonify({
                'error': 'Database table not created yet',
                'message': 'Please run the SQL migration first. See create_alerts_table_simple.sql',
                'setup_required': True,
                'alerts': [],
                'summary': {
                    'total_alerts': 0,
                    'high_priority': 0,
                    'medium_priority': 0,
                    'low_priority': 0,
                    'by_type': {}
                },
                'analysis_date': datetime.now().isoformat()
            }), 200  # Return 200 so frontend can show setup message
        
        return jsonify({'error': str(e)}), 500


@app.route('/api/alerts/refresh', methods=['POST'])
def api_refresh_alerts():
    """
    Recalculate all alerts and update database.
    Use this for scheduled updates or manual refresh.
    """
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500
        
        # First check if the table exists by trying to query it
        try:
            supabase_client.table('customer_alerts').select('id').limit(1).execute()
        except Exception as e:
            error_msg = str(e)
            if 'does not exist' in error_msg or '42P01' in error_msg:
                return jsonify({
                    'success': False,
                    'error': 'Database table not created yet',
                    'message': 'Please run the SQL migration first. Open Supabase SQL Editor and run the SQL from create_alerts_table_simple.sql',
                    'setup_required': True
                }), 400
            raise
        
        from datetime import datetime, timedelta
        import statistics
        
        print("🔍 Starting comprehensive alert analysis...")
        
        # Get all companies
        companies_result = supabase_client.table('companies').select('*').execute()
        
        all_alerts = []
        current_date = datetime.now()
        companies_processed = 0
        
        for company in companies_result.data:
            company_id = company['company_id']
            
            # Rate limiting
            if companies_processed > 0 and companies_processed % 10 == 0:
                time.sleep(0.1)
            
            # Get all invoices for this company
            all_invoices = []
            
            for year in ['2024', '2025']:
                max_retries = 3
                retry_count = 0
                
                while retry_count < max_retries:
                    try:
                        invoices_result = supabase_client.table(f'sales_{year}').select('invoice_date, total_amount, id, invoice_number, balance, invoice_data').eq('company_id', company_id).execute()
                        for invoice in invoices_result.data:
                            if invoice.get('invoice_date'):
                                # Calculate revenue from line items (ex-VAT)
                                invoice_data = invoice.get('invoice_data') or {}
                                line_items = invoice_data.get('invoice_line_items') or []
                                line_revenue = sum(float(item.get('revenue') or 0) for item in line_items)
                                amount = line_revenue if line_revenue > 0 else float(invoice.get('total_amount') or 0)

                                all_invoices.append({
                                    'date': datetime.strptime(invoice['invoice_date'], '%Y-%m-%d'),
                                    'amount': amount,
                                    'balance': float(invoice.get('balance', 0)) if invoice.get('balance') else 0,
                                    'id': invoice['id'],
                                    'number': invoice.get('invoice_number', invoice['id'])
                                })
                        break
                    except Exception as e:
                        retry_count += 1
                        if retry_count >= max_retries:
                            if "Resource temporarily unavailable" not in str(e):
                                print(f"Error fetching invoices for company {company_id}: {e}")
                            break
                        time.sleep(0.05 * (2 ** retry_count))
            
            companies_processed += 1
            
            # Need at least 2 invoices for most analyses
            if len(all_invoices) < 2:
                # Check for one-time customers (only 1 invoice)
                if len(all_invoices) == 1:
                    days_since = (current_date - all_invoices[0]['date']).days
                    if days_since > 90:  # No return in 90+ days
                        all_alerts.append({
                            'type': 'ONE_TIME_CUSTOMER',
                            'priority': 'MEDIUM',
                            'company_id': company_id,
                            'company_name': company['name'],
                            'public_name': company.get('public_name'),
                            'email': company.get('email_addresses') or company.get('email'),
                            'description': f'Customer made only one purchase {days_since} days ago and never returned',
                            'recommendation': 'Reach out with a follow-up offer or check satisfaction',
                            'metrics': {
                                'total_orders': 1,
                                'first_order_date': all_invoices[0]['date'].strftime('%Y-%m-%d'),
                                'first_order_amount': all_invoices[0]['amount'],
                                'days_since_order': days_since
                            }
                        })
                continue
            
            # Sort by date
            all_invoices.sort(key=lambda x: x['date'])
            
            # Calculate intervals and amounts
            intervals = []
            amounts = []
            for i in range(len(all_invoices)):
                amounts.append(all_invoices[i]['amount'])
                if i > 0:
                    interval = (all_invoices[i]['date'] - all_invoices[i-1]['date']).days
                    intervals.append(interval)
            
            # Skip if not enough data
            if len(intervals) < 2:
                continue
            
            # Calculate metrics
            avg_interval = statistics.mean(intervals)
            std_interval = statistics.stdev(intervals) if len(intervals) > 1 else 0
            avg_amount = statistics.mean(amounts)
            days_since_last = (current_date - all_invoices[-1]['date']).days
            
            # 1. PATTERN DISRUPTION ALERT
            expected_next_order = all_invoices[-1]['date'] + timedelta(days=avg_interval)
            days_overdue = (current_date - expected_next_order).days
            
            if days_overdue > (std_interval * 2) and days_overdue > 14:  # More than 2 std devs + at least 2 weeks
                severity = 'HIGH' if days_overdue > avg_interval else 'MEDIUM'
                
                all_alerts.append({
                    'type': 'PATTERN_DISRUPTION',
                    'priority': severity,
                    'company_id': company_id,
                    'company_name': company['name'],
                    'public_name': company.get('public_name'),
                    'email': company.get('email_addresses') or company.get('email'),
                    'description': f'Customer typically orders every {int(avg_interval)} days but is now {days_overdue} days overdue',
                    'recommendation': 'Immediate outreach recommended - customer may have switched suppliers',
                    'metrics': {
                        'total_orders': len(all_invoices),
                        'avg_interval_days': int(avg_interval),
                        'days_since_last_order': days_since_last,
                        'days_overdue': days_overdue,
                        'last_order_amount': all_invoices[-1]['amount'],
                        'last_order_date': all_invoices[-1]['date'].strftime('%Y-%m-%d'),
                        'total_lifetime_value': sum(amounts)
                    }
                })
            
            # 2. DECLINING ORDER VALUE ALERT
            if len(amounts) >= 4:
                recent_avg = statistics.mean(amounts[-3:])  # Last 3 orders
                earlier_avg = statistics.mean(amounts[:len(amounts)-3])  # Earlier orders
                decline_pct = ((recent_avg - earlier_avg) / earlier_avg * 100) if earlier_avg > 0 else 0
                
                if decline_pct < -20:  # 20%+ decline
                    all_alerts.append({
                        'type': 'DECLINING_VALUE',
                        'priority': 'MEDIUM',
                        'company_id': company_id,
                        'company_name': company['name'],
                        'public_name': company.get('public_name'),
                        'email': company.get('email_addresses') or company.get('email'),
                        'description': f'Order value has declined by {abs(int(decline_pct))}% in recent orders',
                        'recommendation': 'Investigate if customer needs have changed or if there\'s price sensitivity',
                        'metrics': {
                            'total_orders': len(all_invoices),
                            'earlier_avg_value': earlier_avg,
                            'recent_avg_value': recent_avg,
                            'decline_percentage': decline_pct,
                            'last_order_date': all_invoices[-1]['date'].strftime('%Y-%m-%d')
                        }
                    })
            
            # 3. INCREASING GAP ALERT (Orders becoming less frequent)
            if len(intervals) >= 4:
                recent_intervals = intervals[-3:]
                earlier_intervals = intervals[:len(intervals)-3]
                recent_avg_interval = statistics.mean(recent_intervals)
                earlier_avg_interval = statistics.mean(earlier_intervals)
                gap_increase = recent_avg_interval - earlier_avg_interval
                
                if gap_increase > 30:  # Orders now 30+ days less frequent
                    all_alerts.append({
                        'type': 'INCREASING_GAP',
                        'priority': 'MEDIUM',
                        'company_id': company_id,
                        'company_name': company['name'],
                        'public_name': company.get('public_name'),
                        'email': company.get('email_addresses') or company.get('email'),
                        'description': f'Time between orders has increased by {int(gap_increase)} days',
                        'recommendation': 'Customer engagement declining - reach out to understand their needs',
                        'metrics': {
                            'total_orders': len(all_invoices),
                            'earlier_avg_gap': int(earlier_avg_interval),
                            'recent_avg_gap': int(recent_avg_interval),
                            'gap_increase_days': int(gap_increase),
                            'last_order_date': all_invoices[-1]['date'].strftime('%Y-%m-%d')
                        }
                    })
            
            # 4. HIGH VALUE AT RISK ALERT
            total_value = sum(amounts)
            if total_value > 5000 and days_since_last > 60:  # High value customer quiet for 60+ days
                all_alerts.append({
                    'type': 'HIGH_VALUE_AT_RISK',
                    'priority': 'HIGH',
                    'company_id': company_id,
                    'company_name': company['name'],
                    'public_name': company.get('public_name'),
                    'email': company.get('email_addresses') or company.get('email'),
                    'description': f'High-value customer (€{int(total_value)} lifetime) has been inactive for {days_since_last} days',
                    'recommendation': 'Priority outreach - offer VIP treatment or exclusive deals',
                    'metrics': {
                        'total_orders': len(all_invoices),
                        'lifetime_value': total_value,
                        'avg_order_value': avg_amount,
                        'days_since_last_order': days_since_last,
                        'last_order_date': all_invoices[-1]['date'].strftime('%Y-%m-%d')
                    }
                })
            
            # 5. PAYMENT ISSUES ALERT
            unpaid_balance = sum(inv['balance'] for inv in all_invoices if inv['balance'] > 0)
            if unpaid_balance > 500:
                all_alerts.append({
                    'type': 'PAYMENT_ISSUES',
                    'priority': 'HIGH',
                    'company_id': company_id,
                    'company_name': company['name'],
                    'public_name': company.get('public_name'),
                    'email': company.get('email_addresses') or company.get('email'),
                    'description': f'Outstanding balance of €{int(unpaid_balance)} across multiple invoices',
                    'recommendation': 'Follow up on payment - may indicate cash flow issues',
                    'metrics': {
                        'total_orders': len(all_invoices),
                        'outstanding_balance': unpaid_balance,
                        'last_order_date': all_invoices[-1]['date'].strftime('%Y-%m-%d')
                    }
                })
            
            # 6. DORMANT CUSTOMER ALERT (used to order regularly, now completely stopped)
            if len(all_invoices) >= 5 and days_since_last > 120:
                all_alerts.append({
                    'type': 'DORMANT_CUSTOMER',
                    'priority': 'HIGH',
                    'company_id': company_id,
                    'company_name': company['name'],
                    'public_name': company.get('public_name'),
                    'email': company.get('email_addresses') or company.get('email'),
                    'description': f'Regular customer ({len(all_invoices)} orders) has been dormant for {days_since_last} days',
                    'recommendation': 'Win-back campaign - investigate why they stopped ordering',
                    'metrics': {
                        'total_orders': len(all_invoices),
                        'lifetime_value': total_value,
                        'days_since_last_order': days_since_last,
                        'last_order_date': all_invoices[-1]['date'].strftime('%Y-%m-%d')
                    }
                })
        
        # Sort alerts by priority and date
        priority_order = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
        all_alerts.sort(key=lambda x: (priority_order.get(x['priority'], 0), x['metrics'].get('days_since_last_order', 0)), reverse=True)
        
        print(f"✅ Analysis complete: {len(all_alerts)} alerts detected")
        
        # Save alerts to database
        print("💾 Saving alerts to database...")
        saved_count = 0
        updated_count = 0
        
        for alert in all_alerts:
            try:
                # Check if this alert already exists for this company+type
                existing = supabase_client.table('customer_alerts').select('id, first_detected_at').eq('company_id', alert['company_id']).eq('alert_type', alert['type']).eq('status', 'active').execute()
                
                alert_data = {
                    'company_id': alert['company_id'],
                    'company_name': alert['company_name'],
                    'public_name': alert.get('public_name'),
                    'email': alert.get('email'),
                    'alert_type': alert['type'],
                    'priority': alert['priority'],
                    'description': alert['description'],
                    'recommendation': alert['recommendation'],
                    'metrics': alert['metrics'],
                    'status': 'active',
                    'analysis_date': current_date.isoformat(),
                    'last_detected_at': current_date.isoformat()
                }
                
                if existing.data:
                    # Update existing alert
                    alert_data['first_detected_at'] = existing.data[0]['first_detected_at']
                    supabase_client.table('customer_alerts').update(alert_data).eq('id', existing.data[0]['id']).execute()
                    updated_count += 1
                else:
                    # Insert new alert
                    alert_data['first_detected_at'] = current_date.isoformat()
                    supabase_client.table('customer_alerts').insert(alert_data).execute()
                    saved_count += 1
                
            except Exception as e:
                print(f"  ⚠️  Error saving alert for company {alert['company_id']}: {e}")
        
        # Mark alerts as resolved if they no longer appear
        try:
            # Get all active alert IDs from current analysis
            current_alert_keys = {(a['company_id'], a['type']) for a in all_alerts}
            
            # Get all active alerts from database
            active_alerts = supabase_client.table('customer_alerts').select('id, company_id, alert_type').eq('status', 'active').execute()
            
            resolved_count = 0
            for db_alert in active_alerts.data:
                key = (db_alert['company_id'], db_alert['alert_type'])
                if key not in current_alert_keys:
                    # This alert no longer exists - mark as resolved
                    supabase_client.table('customer_alerts').update({
                        'status': 'resolved',
                        'updated_at': current_date.isoformat()
                    }).eq('id', db_alert['id']).execute()
                    resolved_count += 1
            
            if resolved_count > 0:
                print(f"✅ Marked {resolved_count} alerts as resolved")
        
        except Exception as e:
            print(f"  ⚠️  Error resolving old alerts: {e}")
        
        # Calculate summary statistics
        alert_summary = {
            'total_alerts': len(all_alerts),
            'high_priority': len([a for a in all_alerts if a['priority'] == 'HIGH']),
            'medium_priority': len([a for a in all_alerts if a['priority'] == 'MEDIUM']),
            'low_priority': len([a for a in all_alerts if a['priority'] == 'LOW']),
            'by_type': {},
            'saved': saved_count,
            'updated': updated_count
        }
        
        for alert in all_alerts:
            alert_type = alert['type']
            if alert_type not in alert_summary['by_type']:
                alert_summary['by_type'][alert_type] = 0
            alert_summary['by_type'][alert_type] += 1
        
        print(f"💾 Saved {saved_count} new alerts, updated {updated_count} existing alerts")
        
        return jsonify({
            'success': True,
            'alerts': all_alerts,
            'summary': alert_summary,
            'analysis_date': current_date.strftime('%Y-%m-%d %H:%M:%S'),
            'companies_analyzed': companies_processed
        })
        
    except Exception as e:
        print(f"Error in alert refresh: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/alerts/<int:alert_id>/dismiss', methods=['POST'])
def api_dismiss_alert(alert_id):
    """Mark an alert as dismissed."""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500
        
        from datetime import datetime
        
        # Get user info if available (you can enhance this with actual user tracking)
        dismissed_by = request.json.get('dismissed_by', 'user') if request.json else 'user'
        notes = request.json.get('notes', '') if request.json else ''
        
        # Update alert status
        result = supabase_client.table('customer_alerts').update({
            'status': 'dismissed',
            'dismissed_at': datetime.now().isoformat(),
            'dismissed_by': dismissed_by,
            'notes': notes
        }).eq('id', alert_id).execute()
        
        if result.data:
            return jsonify({'success': True, 'message': 'Alert dismissed'})
        else:
            return jsonify({'error': 'Alert not found'}), 404
        
    except Exception as e:
        print(f"Error dismissing alert: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/alerts/<int:alert_id>/action', methods=['POST'])
def api_action_alert(alert_id):
    """Mark an alert as actioned."""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500
        
        from datetime import datetime
        
        # Get action details
        actioned_by = request.json.get('actioned_by', 'user') if request.json else 'user'
        notes = request.json.get('notes', '') if request.json else ''
        
        # Update alert status
        result = supabase_client.table('customer_alerts').update({
            'status': 'actioned',
            'actioned_at': datetime.now().isoformat(),
            'actioned_by': actioned_by,
            'notes': notes
        }).eq('id', alert_id).execute()
        
        if result.data:
            return jsonify({'success': True, 'message': 'Alert marked as actioned'})
        else:
            return jsonify({'error': 'Alert not found'}), 404
        
    except Exception as e:
        print(f"Error actioning alert: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/alerts/bulk-dismiss', methods=['POST'])
def api_bulk_dismiss_alerts():
    """Dismiss multiple alerts at once."""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500
        
        from datetime import datetime
        
        alert_ids = request.json.get('alert_ids', [])
        dismissed_by = request.json.get('dismissed_by', 'user')
        
        if not alert_ids:
            return jsonify({'error': 'No alert IDs provided'}), 400
        
        # Update all alerts
        for alert_id in alert_ids:
            supabase_client.table('customer_alerts').update({
                'status': 'dismissed',
                'dismissed_at': datetime.now().isoformat(),
                'dismissed_by': dismissed_by
            }).eq('id', alert_id).execute()
        
        return jsonify({
            'success': True,
            'message': f'{len(alert_ids)} alerts dismissed'
        })
        
    except Exception as e:
        print(f"Error bulk dismissing alerts: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/alerts/stats', methods=['GET'])
def api_alert_stats():
    """Get alert statistics and history."""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500
        
        # Get all alerts grouped by status
        all_alerts = supabase_client.table('customer_alerts').select('*').execute()
        
        stats = {
            'by_status': {},
            'by_type': {},
            'by_priority': {},
            'total': len(all_alerts.data)
        }
        
        for alert in all_alerts.data:
            # Count by status
            status = alert['status']
            stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
            
            # Count by type (only active)
            if status == 'active':
                alert_type = alert['alert_type']
                stats['by_type'][alert_type] = stats['by_type'].get(alert_type, 0) + 1
            
            # Count by priority (only active)
            if status == 'active':
                priority = alert['priority']
                stats['by_priority'][priority] = stats['by_priority'].get(priority, 0) + 1
        
        return jsonify(stats)
        
    except Exception as e:
        print(f"Error getting alert stats: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/pattern-disruptions', methods=['GET'])
def api_pattern_disruptions():
    """Detect companies with disrupted ordering patterns."""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500
        
        from datetime import datetime, timedelta
        import statistics
        
        # Get all companies with their invoices
        companies_result = supabase_client.table('companies').select('*').execute()
        
        disrupted_patterns = []
        current_date = datetime.now()
        
        # Process companies with rate limiting to prevent resource exhaustion
        companies_processed = 0
        companies_to_process = companies_result.data
        
        for company in companies_to_process:
            company_id = company['company_id']
            
            # Add small delay every 10 companies to prevent resource exhaustion
            if companies_processed > 0 and companies_processed % 10 == 0:
                time.sleep(0.1)  # 100ms pause every 10 companies
            
            # Get all invoices for this company from both years
            all_invoices = []
            
            for year in ['2024', '2025']:
                max_retries = 3
                retry_count = 0
                
                while retry_count < max_retries:
                    try:
                        invoices_result = supabase_client.table(f'sales_{year}').select('invoice_date, total_amount, id, invoice_number, invoice_data').eq('company_id', company_id).execute()
                        for invoice in invoices_result.data:
                            if invoice.get('invoice_date'):
                                # Calculate revenue from line items (ex-VAT)
                                invoice_data = invoice.get('invoice_data') or {}
                                line_items = invoice_data.get('invoice_line_items') or []
                                line_revenue = sum(float(item.get('revenue') or 0) for item in line_items)
                                amount = line_revenue if line_revenue > 0 else float(invoice.get('total_amount') or 0)

                                all_invoices.append({
                                    'date': datetime.strptime(invoice['invoice_date'], '%Y-%m-%d'),
                                    'amount': amount,
                                    'id': invoice['id'],
                                    'number': invoice.get('invoice_number', invoice['id'])
                                })
                        break  # Success, exit retry loop
                    except Exception as e:
                        retry_count += 1
                        if retry_count >= max_retries:
                            # Only print after all retries exhausted
                            if "Resource temporarily unavailable" not in str(e):
                                print(f"Error fetching invoices for company {company_id} after {max_retries} retries: {e}")
                            break
                        # Exponential backoff: 0.05s, 0.1s, 0.2s
                        time.sleep(0.05 * (2 ** retry_count))
            
            companies_processed += 1
            
            # Need at least 3 invoices to detect a pattern
            if len(all_invoices) < 3:
                continue
            
            # Sort by date
            all_invoices.sort(key=lambda x: x['date'])
            
            # Calculate intervals between invoices (in days)
            intervals = []
            for i in range(1, len(all_invoices)):
                interval = (all_invoices[i]['date'] - all_invoices[i-1]['date']).days
                intervals.append(interval)
            
            if len(intervals) < 2:
                continue
            
            # Analyze pattern
            pattern_analysis = analyze_ordering_pattern(all_invoices, intervals, current_date)
            
            if pattern_analysis['is_disrupted']:
                disrupted_patterns.append({
                    'company_id': company_id,
                    'company_name': company['name'],
                    'public_name': company.get('public_name'),
                    'email': company.get('email_addresses'),
                    'total_invoices': len(all_invoices),
                    'last_invoice_date': all_invoices[-1]['date'].strftime('%Y-%m-%d'),
                    'last_invoice_amount': all_invoices[-1]['amount'],
                    'days_since_last_order': (current_date - all_invoices[-1]['date']).days,
                    'expected_interval_days': pattern_analysis['expected_interval'],
                    'average_interval_days': pattern_analysis['average_interval'],
                    'pattern_strength': pattern_analysis['pattern_strength'],
                    'disruption_severity': pattern_analysis['disruption_severity'],
                    'risk_level': pattern_analysis['risk_level'],
                    'pattern_description': pattern_analysis['description'],
                    'recommendation': pattern_analysis['recommendation'],
                    'total_revenue': float(company.get('total_revenue_all_time', 0)) if company.get('total_revenue_all_time') else 0,
                    'average_order_value': sum(inv['amount'] for inv in all_invoices) / len(all_invoices) if all_invoices else 0
                })
        
        # Sort by risk level and days since last order
        risk_order = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
        disrupted_patterns.sort(key=lambda x: (risk_order.get(x['risk_level'], 0), x['days_since_last_order']), reverse=True)
        
        return jsonify({
            'disrupted_patterns': disrupted_patterns,
            'total_disruptions': len(disrupted_patterns),
            'high_risk_count': len([p for p in disrupted_patterns if p['risk_level'] == 'HIGH']),
            'medium_risk_count': len([p for p in disrupted_patterns if p['risk_level'] == 'MEDIUM']),
            'analysis_date': current_date.strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        print(f"Error in pattern disruption analysis: {e}")
        return jsonify({'error': str(e)}), 500


def analyze_ordering_pattern(invoices, intervals, current_date):
    """Analyze ordering pattern and detect disruptions."""
    import statistics
    
    if len(intervals) < 2:
        return {'is_disrupted': False}
    
    # Calculate statistics
    avg_interval = statistics.mean(intervals)
    median_interval = statistics.median(intervals)
    
    # Calculate standard deviation if we have enough data
    if len(intervals) >= 3:
        std_dev = statistics.stdev(intervals)
        pattern_consistency = 1 - (std_dev / avg_interval) if avg_interval > 0 else 0
    else:
        std_dev = 0
        pattern_consistency = 0.5
    
    # Days since last invoice
    days_since_last = (current_date - invoices[-1]['date']).days
    
    # Determine if there's a consistent pattern (low standard deviation relative to mean)
    has_consistent_pattern = pattern_consistency > 0.3 and len(intervals) >= 4
    
    # Expected next order date based on pattern
    expected_interval = median_interval if has_consistent_pattern else avg_interval
    expected_next_date = invoices[-1]['date'] + timedelta(days=expected_interval)
    days_overdue = (current_date - expected_next_date).days
    
    # Determine disruption
    is_disrupted = False
    disruption_severity = 'NONE'
    risk_level = 'LOW'
    
    if has_consistent_pattern and days_overdue > 0:
        # Calculate disruption severity based on how overdue they are
        overdue_ratio = days_overdue / expected_interval
        
        if overdue_ratio > 2.0:  # More than 2x their normal interval
            disruption_severity = 'SEVERE'
            risk_level = 'HIGH'
            is_disrupted = True
        elif overdue_ratio > 1.5:  # 1.5x their normal interval
            disruption_severity = 'MODERATE'
            risk_level = 'MEDIUM'
            is_disrupted = True
        elif overdue_ratio > 1.0:  # Past their expected date
            disruption_severity = 'MILD'
            risk_level = 'MEDIUM'
            is_disrupted = True
    elif not has_consistent_pattern and days_since_last > 90:  # No clear pattern but long absence
        disruption_severity = 'IRREGULAR'
        risk_level = 'MEDIUM'
        is_disrupted = True
    
    # Generate description and recommendation
    if has_consistent_pattern:
        if avg_interval <= 14:
            frequency_desc = "weekly"
        elif avg_interval <= 35:
            frequency_desc = "monthly"
        elif avg_interval <= 70:
            frequency_desc = "bi-monthly"
        else:
            frequency_desc = f"every {int(avg_interval)} days"
        
        description = f"Regular {frequency_desc} ordering pattern (avg: {int(avg_interval)} days)"
    else:
        description = f"Irregular ordering pattern (avg: {int(avg_interval)} days, high variation)"
    
    # Generate recommendations
    if disruption_severity == 'SEVERE':
        recommendation = "URGENT: Customer significantly overdue. Immediate contact recommended."
    elif disruption_severity == 'MODERATE':
        recommendation = "Customer overdue for reorder. Contact within 1-2 days."
    elif disruption_severity == 'MILD':
        recommendation = "Customer approaching reorder time. Consider proactive outreach."
    elif disruption_severity == 'IRREGULAR':
        recommendation = "Irregular customer with long absence. Check-in recommended."
    else:
        recommendation = "Pattern normal. Monitor for future changes."
    
    return {
        'is_disrupted': is_disrupted,
        'expected_interval': int(expected_interval),
        'average_interval': int(avg_interval),
        'pattern_strength': round(pattern_consistency, 2),
        'disruption_severity': disruption_severity,
        'risk_level': risk_level,
        'description': description,
        'recommendation': recommendation,
        'days_overdue': max(0, days_overdue),
        'has_consistent_pattern': has_consistent_pattern
    }


@app.route('/api/combined-companies-analysis', methods=['GET'])
def api_combined_companies_analysis():
    """Get combined company analysis from both 2024 and 2025 sales data."""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500
        
        # Get data from both years
        def fetch_year_data(year):
            all_invoices = []
            batch_size = 1000
            offset = 0
            
            while True:
                batch_result = supabase_client.table(f'sales_{year}').select('*').range(offset, offset + batch_size - 1).execute()
                
                if not batch_result.data:
                    break
                    
                all_invoices.extend(batch_result.data)
                
                if len(batch_result.data) < batch_size:
                    break
                    
                offset += batch_size
                
                if offset > 50000:
                    break
            
            return all_invoices
        
        # Fetch both years
        invoices_2024 = fetch_year_data('2024')
        invoices_2025 = fetch_year_data('2025')
        
        print(f"DEBUG Combined: 2024 records: {len(invoices_2024)}, 2025 records: {len(invoices_2025)}")
        
        # Process combined company data
        companies_data = {}
        
        def process_invoices(invoices, year):
            for invoice in invoices:
                invoice_data = invoice.get('invoice_data', {})
                company_info = invoice_data.get('company', {})
                
                # Use company_id from the extracted field if company info is missing
                company_id = None
                if company_info and company_info.get('id'):
                    company_id = company_info.get('id')
                elif invoice.get('company_id'):
                    company_id = invoice.get('company_id')
                    if not company_info:
                        company_info = {
                            'id': company_id,
                            'name': invoice.get('company_name') or 'Unknown Company'
                        }
                else:
                    continue
                
                # Initialize company if not exists
                if company_id not in companies_data:
                    companies_data[company_id] = {
                        'id': company_id,
                        'name': company_info.get('name') or company_info.get('public_name') or 'Unknown Company',
                        'vat_number': company_info.get('vat_number', ''),
                        'email': company_info.get('email', ''),
                        'phone': company_info.get('phone_number', ''),
                        'website': company_info.get('website', ''),
                        'address': {
                            'street': company_info.get('address_line1', ''),
                            'street2': company_info.get('address_line2', ''),
                            'city': company_info.get('city', ''),
                            'postal_code': company_info.get('post_code', ''),
                            'country': company_info.get('country', {}).get('name', '') if company_info.get('country') else ''
                        },
                        'contact_person': company_info.get('contact_person', {}).get('name', '') if company_info.get('contact_person') else '',
                        'industry': company_info.get('industry', ''),
                        'company_size': company_info.get('company_size', ''),
                        'years_data': {
                            '2024': {'invoices': [], 'total_revenue': 0, 'invoice_count': 0, 'first_date': None, 'last_date': None},
                            '2025': {'invoices': [], 'total_revenue': 0, 'invoice_count': 0, 'first_date': None, 'last_date': None}
                        },
                        'total_revenue': 0,
                        'invoice_count': 0,
                        'average_invoice_value': 0,
                        'first_invoice_date': None,
                        'last_invoice_date': None,
                        'payment_terms': set(),
                        'currencies': set()
                    }
                
                # Add invoice data to specific year - calculate revenue from line items (ex-VAT)
                company = companies_data[company_id]
                line_items = invoice_data.get('invoice_line_items') or []
                line_revenue = sum(float(item.get('revenue') or 0) for item in line_items)
                invoice_amount = line_revenue if line_revenue > 0 else float(invoice.get('total_amount') or 0)
                invoice_date = invoice.get('invoice_date')

                # Extract more details from raw invoice data
                raw_invoice = invoice_data

                invoice_record = {
                    'id': invoice.get('invoice_id'),
                    'number': invoice.get('invoice_number'),
                    'date': invoice_date,
                    'due_date': invoice.get('due_date'),
                    'amount': invoice_amount,
                    'balance': float(invoice.get('balance') or 0),
                    'is_paid': invoice.get('is_paid', False),
                    'year': year,
                    'currency': raw_invoice.get('currency', 'EUR'),
                    'payment_terms': raw_invoice.get('payment_terms', ''),
                    'buyer_name': raw_invoice.get('buyer_name', ''),
                    'buyer_reference': raw_invoice.get('buyer_reference', ''),
                    'description': raw_invoice.get('description', ''),
                    'notes': raw_invoice.get('notes', ''),
                    'created_at': raw_invoice.get('created_at', ''),
                    'updated_at': raw_invoice.get('updated_at', ''),
                    'line_items_count': len(raw_invoice.get('invoice_line_items', [])),
                    'has_attachments': bool(raw_invoice.get('attachments', [])),
                    'invoice_type': raw_invoice.get('type', ''),
                    'status': raw_invoice.get('status', '')
                }

                # Add to year-specific data
                company['years_data'][str(year)]['invoices'].append(invoice_record)
                company['years_data'][str(year)]['total_revenue'] += invoice_amount
                company['years_data'][str(year)]['invoice_count'] += 1
                
                # Update year-specific dates
                if invoice_date:
                    year_data = company['years_data'][str(year)]
                    if not year_data['first_date'] or invoice_date < year_data['first_date']:
                        year_data['first_date'] = invoice_date
                    if not year_data['last_date'] or invoice_date > year_data['last_date']:
                        year_data['last_date'] = invoice_date
                
                # Update overall totals
                company['total_revenue'] += invoice_amount
                company['invoice_count'] += 1
                
                # Track overall dates
                if invoice_date:
                    if not company['first_invoice_date'] or invoice_date < company['first_invoice_date']:
                        company['first_invoice_date'] = invoice_date
                    if not company['last_invoice_date'] or invoice_date > company['last_invoice_date']:
                        company['last_invoice_date'] = invoice_date
                
                # Extract additional details from raw data
                if invoice_data.get('payment_terms'):
                    company['payment_terms'].add(str(invoice_data.get('payment_terms')))
                if invoice_data.get('currency'):
                    company['currencies'].add(invoice_data.get('currency'))
        
        # Process both years
        process_invoices(invoices_2024, 2024)
        process_invoices(invoices_2025, 2025)
        
        # Finalize company data
        companies_list = []
        for company in companies_data.values():
            company['average_invoice_value'] = round(company['total_revenue'] / company['invoice_count'], 2) if company['invoice_count'] > 0 else 0
            company['payment_terms'] = list(company['payment_terms'])
            company['currencies'] = list(company['currencies'])
            company['total_revenue'] = round(company['total_revenue'], 2)
            
            # Calculate year-specific averages
            for year in ['2024', '2025']:
                year_data = company['years_data'][year]
                year_data['average_invoice_value'] = round(year_data['total_revenue'] / year_data['invoice_count'], 2) if year_data['invoice_count'] > 0 else 0
                year_data['total_revenue'] = round(year_data['total_revenue'], 2)
                # Sort year invoices by date (newest first)
                year_data['invoices'].sort(key=lambda x: x['date'] or '1900-01-01', reverse=True)
            
            # Create combined invoices list for display
            all_invoices = company['years_data']['2024']['invoices'] + company['years_data']['2025']['invoices']
            all_invoices.sort(key=lambda x: x['date'] or '1900-01-01', reverse=True)
            company['invoices'] = all_invoices
            
            companies_list.append(company)
        
        # Sort companies by total revenue (highest first)
        companies_list.sort(key=lambda x: x['total_revenue'], reverse=True)
        
        total_invoices_calculated = sum(c['invoice_count'] for c in companies_list)
        print(f"DEBUG Combined: Companies processed: {len(companies_list)}, Total invoices: {total_invoices_calculated}")
        
        return jsonify({
            'companies': companies_list,
            'total_companies': len(companies_list),
            'total_revenue': sum(c['total_revenue'] for c in companies_list),
            'total_invoices': total_invoices_calculated,
            'year_breakdown': {
                '2024': {
                    'companies': len([c for c in companies_list if c['years_data']['2024']['invoice_count'] > 0]),
                    'invoices': sum(c['years_data']['2024']['invoice_count'] for c in companies_list),
                    'revenue': sum(c['years_data']['2024']['total_revenue'] for c in companies_list)
                },
                '2025': {
                    'companies': len([c for c in companies_list if c['years_data']['2025']['invoice_count'] > 0]),
                    'invoices': sum(c['years_data']['2025']['invoice_count'] for c in companies_list),
                    'revenue': sum(c['years_data']['2025']['total_revenue'] for c in companies_list)
                }
            }
        })
        
    except Exception as e:
        print(f"Error getting combined companies analysis: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/invoice-details/<year>/<int:invoice_id>', methods=['GET'])
def api_invoice_details(year, invoice_id):
    """Get detailed invoice information including line items."""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500
        
        # Get invoice from the appropriate year table
        table_name = f'sales_{year}'
        print(f"DEBUG: Looking for invoice with ID {invoice_id} in table {table_name}")
        
        # Try to find by database ID first
        invoice_result = supabase_client.table(table_name).select('*').eq('id', invoice_id).execute()
        
        if not invoice_result.data:
            # Try to find by invoice_id field as fallback
            invoice_result = supabase_client.table(table_name).select('*').eq('invoice_id', invoice_id).execute()
            print(f"DEBUG: Fallback search by invoice_id field")
        
        if not invoice_result.data:
            print(f"DEBUG: Invoice {invoice_id} not found in {table_name}")
            return jsonify({'error': f'Invoice {invoice_id} not found in {year} data'}), 404
        
        invoice = invoice_result.data[0]
        invoice_data = invoice.get('invoice_data', {})
        
        return jsonify({
            'invoice_id': invoice_id,
            'year': year,
            'invoice_data': invoice_data,
            'extracted_fields': {
                'company_name': invoice.get('company_name'),
                'invoice_number': invoice.get('invoice_number'),
                'invoice_date': invoice.get('invoice_date'),
                'due_date': invoice.get('due_date'),
                'total_amount': invoice.get('total_amount'),
                'balance': invoice.get('balance'),
                'is_paid': invoice.get('is_paid')
            }
        })
        
    except Exception as e:
        print(f"Error getting invoice details: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/populate-companies-enhanced', methods=['POST'])
def api_populate_companies_enhanced():
    """Populate companies table with enhanced data from DOUANO API.
    Admin only - requires DUANO authentication.
    """
    if not is_admin():
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500
        
        # First, get all unique company IDs from invoices
        print("Getting unique company IDs from invoice data...")
        
        def get_company_ids_from_year(year):
            company_ids = set()
            batch_size = 1000
            offset = 0
            
            while True:
                try:
                    batch_result = supabase_client.table(f'sales_{year}').select('company_id, company_name').range(offset, offset + batch_size - 1).execute()
                    
                    if not batch_result.data:
                        break
                    
                    for record in batch_result.data:
                        if record.get('company_id'):
                            company_ids.add(record.get('company_id'))
                    
                    if len(batch_result.data) < batch_size:
                        break
                        
                    offset += batch_size
                    
                    if offset > 50000:
                        break
                except Exception as e:
                    print(f"Error fetching {year} company IDs at offset {offset}: {e}")
                    break
            
            return company_ids
        
        # Get company IDs from all years (2024, 2025, 2026)
        company_ids_2024 = get_company_ids_from_year('2024')
        company_ids_2025 = get_company_ids_from_year('2025')
        company_ids_2026 = get_company_ids_from_year('2026')
        all_company_ids = company_ids_2024.union(company_ids_2025).union(company_ids_2026)

        print(f"Found {len(all_company_ids)} unique companies across all years (2024: {len(company_ids_2024)}, 2025: {len(company_ids_2025)}, 2026: {len(company_ids_2026)})")
        print(f"🚀 Processing all companies with smart rate limiting...")
        
        # Fetch complete company data from DOUANO API
        companies_data = {}
        api_success_count = 0
        api_error_count = 0
        
        for i, company_id in enumerate(all_company_ids):
            try:
                print(f"Fetching company data for ID {company_id}... ({i+1}/{len(all_company_ids)})")
                
                # Add rate limiting - wait between requests
                if i > 0 and i % 10 == 0:  # Every 10 requests, wait longer
                    print(f"Rate limiting: waiting 2 seconds after {i} requests...")
                    time.sleep(2)
                elif i > 0:  # Wait between each request
                    time.sleep(0.1)
                
                # Get company details from DOUANO API with retry logic
                max_retries = 3
                retry_count = 0
                company_response = None
                error = None
                
                while retry_count < max_retries:
                    company_response, error = make_api_request(f'/api/public/v1/core/companies/{company_id}')
                    
                    if error and "429" in str(error):  # Rate limit error
                        retry_count += 1
                        wait_time = min(5 * retry_count, 30)  # Exponential backoff, max 30 seconds
                        print(f"Rate limited, waiting {wait_time}s before retry {retry_count}/{max_retries}...")
                        time.sleep(wait_time)
                        continue
                    else:
                        break  # Success or non-rate-limit error
                
                if error or not company_response:
                    print(f"❌ Failed to fetch company {company_id} after {max_retries} retries: {error}")
                    api_error_count += 1
                    continue
                
                company_data = company_response.get('result', {})
                if not company_data:
                    print(f"❌ No data for company {company_id}")
                    api_error_count += 1
                    continue
                
                # Extract comprehensive company information
                companies_data[company_id] = {
                    'company_id': company_id,
                    'name': company_data.get('name'),
                    'public_name': company_data.get('public_name'),
                    'company_tag': company_data.get('tag'),
                    'vat_number': company_data.get('vat_number'),
                    
                    # Classification
                    'is_customer': company_data.get('is_customer', False),
                    'is_supplier': company_data.get('is_supplier', False),
                    
                    # Status and pricing
                    'company_status_id': company_data.get('company_status', {}).get('id') if company_data.get('company_status') else None,
                    'company_status_name': company_data.get('company_status', {}).get('name') if company_data.get('company_status') else None,
                    'sales_price_class_id': company_data.get('sales_price_class', {}).get('id') if company_data.get('sales_price_class') else None,
                    'sales_price_class_name': company_data.get('sales_price_class', {}).get('name') if company_data.get('sales_price_class') else None,
                    
                    # Communication
                    'document_delivery_type': company_data.get('document_delivery_type'),
                    'email_addresses': company_data.get('email_addresses'),
                    'default_document_notes': company_data.get('default_document_notes', []),
                    
                    # Structured data
                    'company_categories': company_data.get('company_categories', []),
                    'addresses': company_data.get('addresses', []),
                    'bank_accounts': company_data.get('bank_accounts', []),
                    'extension_values': company_data.get('extension_values', []),
                    
                    # Raw data
                    'raw_company_data': company_data,
                    'data_sources': ['douano_api', 'invoices'],
                    
                    # Initialize financial data (will be calculated from invoices)
                    'total_revenue_2024': 0,
                    'total_revenue_2025': 0,
                    'invoice_count_2024': 0,
                    'invoice_count_2025': 0,
                    'first_invoice_date': None,
                    'last_invoice_date': None,
                    'payment_terms': set(),
                    'currencies_used': set()
                }
                
                api_success_count += 1
                print(f"✅ Successfully fetched company {company_id}: {company_data.get('name')}")
                
            except Exception as e:
                print(f"❌ Error fetching company {company_id}: {e}")
                api_error_count += 1
                continue
        
        print(f"API fetch completed: {api_success_count} success, {api_error_count} errors")
        
        # Now calculate financial data from invoices
        print("Calculating financial data from invoices...")
        
        def calculate_financial_data(year):
            batch_size = 1000
            offset = 0
            
            while True:
                try:
                    batch_result = supabase_client.table(f'sales_{year}').select('*').range(offset, offset + batch_size - 1).execute()
                    
                    if not batch_result.data:
                        break
                    
                    for invoice in batch_result.data:
                        company_id = invoice.get('company_id')
                        if not company_id or company_id not in companies_data:
                            continue

                        company = companies_data[company_id]
                        # Calculate revenue from line items (ex-VAT)
                        invoice_data = invoice.get('invoice_data') or {}
                        line_items = invoice_data.get('invoice_line_items') or []
                        line_revenue = sum(float(item.get('revenue') or 0) for item in line_items)
                        invoice_amount = line_revenue if line_revenue > 0 else float(invoice.get('total_amount') or 0)
                        invoice_date = invoice.get('invoice_date')

                        # Update year-specific totals
                        if year == 2024:
                            company['total_revenue_2024'] += invoice_amount
                            company['invoice_count_2024'] += 1
                        else:
                            company['total_revenue_2025'] += invoice_amount
                            company['invoice_count_2025'] += 1
                        
                        # Update dates
                        if invoice_date:
                            if not company['first_invoice_date'] or invoice_date < company['first_invoice_date']:
                                company['first_invoice_date'] = invoice_date
                            if not company['last_invoice_date'] or invoice_date > company['last_invoice_date']:
                                company['last_invoice_date'] = invoice_date
                        
                        # Collect metadata from raw invoice data
                        invoice_data = invoice.get('invoice_data', {})
                        if invoice_data.get('payment_terms'):
                            company['payment_terms'].add(str(invoice_data.get('payment_terms')))
                        if invoice_data.get('currency'):
                            company['currencies_used'].add(invoice_data.get('currency'))
                    
                    if len(batch_result.data) < batch_size:
                        break
                        
                    offset += batch_size
                    
                    if offset > 50000:
                        break
                        
                except Exception as e:
                    print(f"Error calculating financial data for {year} at offset {offset}: {e}")
                    break
        
        # Calculate for both years
        calculate_financial_data(2024)
        calculate_financial_data(2025)
        
        # Save companies to database
        print("Saving companies to database...")
        saved_count = 0
        updated_count = 0
        error_count = 0
        
        for company in companies_data.values():
            try:
                # Calculate totals
                company['total_revenue_all_time'] = company['total_revenue_2024'] + company['total_revenue_2025']
                company['invoice_count_all_time'] = company['invoice_count_2024'] + company['invoice_count_2025']
                company['average_invoice_value'] = round(company['total_revenue_all_time'] / company['invoice_count_all_time'], 2) if company['invoice_count_all_time'] > 0 else 0
                company['customer_since'] = company['first_invoice_date']
                company['last_activity_date'] = company['last_invoice_date']
                
                # Convert sets to arrays
                company['payment_terms'] = list(company['payment_terms'])
                company['currencies_used'] = list(company['currencies_used'])
                
                # Prepare record for database - try enhanced fields, fall back to basic if columns don't exist
                record = {
                    'company_id': company['company_id'],
                    'name': company['name'],
                    'public_name': company['public_name'],
                    'vat_number': company['vat_number'],
                    'total_revenue_2024': round(company['total_revenue_2024'], 2),
                    'total_revenue_2025': round(company['total_revenue_2025'], 2),
                    'total_revenue_all_time': round(company['total_revenue_all_time'], 2),
                    'invoice_count_2024': company['invoice_count_2024'],
                    'invoice_count_2025': company['invoice_count_2025'],
                    'invoice_count_all_time': company['invoice_count_all_time'],
                    'average_invoice_value': company['average_invoice_value'],
                    'first_invoice_date': company['first_invoice_date'],
                    'last_invoice_date': company['last_invoice_date'],
                    'customer_since': company['customer_since'],
                    'last_activity_date': company['last_activity_date'],
                    'payment_terms': company['payment_terms'],
                    'currencies_used': company['currencies_used'],
                    'raw_company_data': company['raw_company_data'],
                    'data_sources': company['data_sources'],
                    'last_sync_at': datetime.now().isoformat()
                }
                
                # Try to add enhanced fields if they exist in the schema
                try:
                    enhanced_fields = {
                        'company_tag': company['company_tag'],
                        'is_customer': company['is_customer'],
                        'is_supplier': company['is_supplier'],
                        'company_status_id': company['company_status_id'],
                        'company_status_name': company['company_status_name'],
                        'sales_price_class_id': company['sales_price_class_id'],
                        'sales_price_class_name': company['sales_price_class_name'],
                        'document_delivery_type': company['document_delivery_type'],
                        'email_addresses': company['email_addresses'],
                        'default_document_notes': company['default_document_notes'],
                        'company_categories': company['company_categories'],
                        'addresses': company['addresses'],
                        'bank_accounts': company['bank_accounts'],
                        'extension_values': company['extension_values']
                    }
                    record.update(enhanced_fields)
                except Exception as e:
                    print(f"Note: Using basic schema for company {company['company_id']} - enhanced fields not available: {e}")
                    pass
                
                # Check if company exists
                existing = supabase_client.table('companies').select('id').eq('company_id', company['company_id']).execute()
                
                if existing.data:
                    # Update existing company
                    record['updated_at'] = datetime.now().isoformat()
                    supabase_client.table('companies').update(record).eq('company_id', company['company_id']).execute()
                    updated_count += 1
                    print(f"✅ Updated company {company['company_id']}: {company['name']}")
                else:
                    # Insert new company
                    supabase_client.table('companies').insert(record).execute()
                    saved_count += 1
                    print(f"✅ Saved new company {company['company_id']}: {company['name']}")
                
            except Exception as e:
                print(f"❌ Error saving company {company.get('company_id')}: {e}")
                error_count += 1
                continue
        
        return jsonify({
            'success': True,
            'message': f'Successfully processed {len(companies_data)} companies with enhanced data',
            'total_processed': len(companies_data),
            'saved': saved_count,
            'updated': updated_count,
            'errors': error_count,
            'api_fetch_stats': {
                'success': api_success_count,
                'errors': api_error_count
            }
        })
        
    except Exception as e:
        print(f"❌ Error in enhanced companies population: {e}")
        return jsonify({'error': str(e)}), 500


# Global variable to track background sync status
_sync_status = {'running': False, 'synced': 0, 'total': 0, 'errors': 0, 'message': ''}

def _background_sync_all_missing():
    """Background thread function to sync all missing companies."""
    global _sync_status

    try:
        _sync_status = {'running': True, 'synced': 0, 'total': 0, 'errors': 0, 'message': 'Starting...'}

        # Get company IDs from invoices
        def get_company_ids_from_year(year):
            company_ids = set()
            batch_size = 1000
            offset = 0
            while True:
                try:
                    batch_result = supabase_client.table(f'sales_{year}').select('company_id').range(offset, offset + batch_size - 1).execute()
                    if not batch_result.data:
                        break
                    for record in batch_result.data:
                        if record.get('company_id'):
                            company_ids.add(record.get('company_id'))
                    if len(batch_result.data) < batch_size:
                        break
                    offset += batch_size
                    if offset > 50000:
                        break
                except Exception as e:
                    print(f"Error fetching {year} company IDs: {e}")
                    break
            return company_ids

        invoice_company_ids = set()
        for year in ['2024', '2025', '2026']:
            invoice_company_ids.update(get_company_ids_from_year(year))

        # Get ALL existing company IDs with pagination
        existing_company_ids = set()
        offset = 0
        while True:
            existing_result = supabase_client.table('companies').select('company_id').range(offset, offset + 999).execute()
            if not existing_result.data:
                break
            for c in existing_result.data:
                if c.get('company_id'):
                    existing_company_ids.add(c['company_id'])
            if len(existing_result.data) < 1000:
                break
            offset += 1000

        missing_company_ids = list(invoice_company_ids - existing_company_ids)
        _sync_status['total'] = len(missing_company_ids)

        print(f"🚀 [Background] Starting sync of {len(missing_company_ids)} missing companies...")

        for i, company_id in enumerate(missing_company_ids):
            try:
                if i > 0 and i % 10 == 0:
                    time.sleep(0.3)  # Rate limiting

                company_response, error = make_api_request(f'/api/public/v1/core/companies/{company_id}')

                if error or not company_response:
                    _sync_status['errors'] += 1
                    print(f"❌ [Background] Failed to fetch company {company_id}: {error}")
                    continue

                company_data = company_response.get('result', {})
                if not company_data:
                    _sync_status['errors'] += 1
                    continue

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

                supabase_client.table('companies').upsert(record, on_conflict='company_id').execute()
                _sync_status['synced'] += 1
                print(f"✅ [Background] ({_sync_status['synced']}/{_sync_status['total']}) Synced {company_id}: {company_data.get('name')}")

            except Exception as e:
                _sync_status['errors'] += 1
                print(f"❌ [Background] Error syncing {company_id}: {e}")

        _sync_status['message'] = f"Completed! Synced {_sync_status['synced']} companies with {_sync_status['errors']} errors."
        _sync_status['running'] = False
        print(f"🎉 [Background] Sync complete: {_sync_status['synced']} synced, {_sync_status['errors']} errors")

    except Exception as e:
        _sync_status['message'] = f"Error: {str(e)}"
        _sync_status['running'] = False
        print(f"❌ [Background] Sync failed: {e}")


@app.route('/api/sync-missing-companies-background', methods=['POST'])
def api_sync_missing_companies_background():
    """Start syncing all missing companies in the background."""
    global _sync_status

    if not is_admin():
        return jsonify({'error': 'Admin access required'}), 403

    if _sync_status.get('running'):
        return jsonify({
            'success': False,
            'message': 'Sync already running',
            'status': _sync_status
        })

    # Start background thread
    import threading
    thread = threading.Thread(target=_background_sync_all_missing)
    thread.daemon = True
    thread.start()

    return jsonify({
        'success': True,
        'message': 'Background sync started. Check /api/sync-status for progress.',
        'status': _sync_status
    })


@app.route('/api/sync-status', methods=['GET'])
def api_sync_status():
    """Get the current status of background sync."""
    return jsonify(_sync_status)


@app.route('/api/sync-missing-companies', methods=['POST'])
def api_sync_missing_companies():
    """Sync only companies that are in invoices but missing from the companies table.
    This is faster than a full sync because it only processes missing companies.
    Admin only - requires DUANO authentication.
    Accepts optional 'batch_size' parameter (default 50) to prevent worker timeout.
    """
    if not is_admin():
        return jsonify({'error': 'Admin access required'}), 403

    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500

        # Get batch size from request (default 50 to avoid timeout)
        data = request.get_json(silent=True) or {}
        batch_size_limit = data.get('batch_size', 50)

        print(f"🔍 Finding companies missing from companies table (batch size: {batch_size_limit})...")

        # Step 1: Get all unique company IDs from invoices (all years)
        def get_company_ids_from_year(year):
            company_ids = set()
            batch_size = 1000
            offset = 0

            while True:
                try:
                    batch_result = supabase_client.table(f'sales_{year}').select('company_id, company_name').range(offset, offset + batch_size - 1).execute()

                    if not batch_result.data:
                        break

                    for record in batch_result.data:
                        if record.get('company_id'):
                            company_ids.add(record.get('company_id'))

                    if len(batch_result.data) < batch_size:
                        break

                    offset += batch_size

                    if offset > 50000:
                        break
                except Exception as e:
                    print(f"Error fetching {year} company IDs at offset {offset}: {e}")
                    break

            return company_ids

        # Get company IDs from all years
        invoice_company_ids = set()
        for year in ['2024', '2025', '2026']:
            year_ids = get_company_ids_from_year(year)
            print(f"  {year}: {len(year_ids)} unique companies")
            invoice_company_ids.update(year_ids)

        print(f"Total unique companies in invoices: {len(invoice_company_ids)}")

        # Step 2: Get ALL company IDs already in companies table (with pagination)
        existing_company_ids = set()
        offset = 0
        batch_size = 1000
        while True:
            existing_result = supabase_client.table('companies').select('company_id').range(offset, offset + batch_size - 1).execute()
            if not existing_result.data:
                break
            for c in existing_result.data:
                if c.get('company_id'):
                    existing_company_ids.add(c['company_id'])
            if len(existing_result.data) < batch_size:
                break
            offset += batch_size
        print(f"Companies already in database: {len(existing_company_ids)}")

        # Step 3: Find missing companies
        missing_company_ids = invoice_company_ids - existing_company_ids
        print(f"🎯 Missing companies to sync: {len(missing_company_ids)}")

        if not missing_company_ids:
            return jsonify({
                'success': True,
                'message': 'No missing companies found - all companies are already synced!',
                'total_in_invoices': len(invoice_company_ids),
                'total_in_database': len(existing_company_ids),
                'missing_count': 0,
                'synced': 0,
                'errors': 0
            })

        # Step 4: Fetch missing companies from DOUANO API (limited by batch_size)
        missing_list = list(missing_company_ids)[:batch_size_limit]
        total_missing = len(missing_company_ids)
        print(f"🚀 Fetching {len(missing_list)} of {total_missing} missing companies from DOUANO API...")

        synced_count = 0
        error_count = 0
        failed_companies = []

        for i, company_id in enumerate(missing_list):
            try:
                print(f"Fetching company {company_id}... ({i+1}/{len(missing_list)})")

                # Minimal rate limiting (API is fast)
                if i > 0 and i % 25 == 0:
                    time.sleep(0.5)

                # Fetch from DOUANO API with retry logic
                max_retries = 3
                company_response = None
                error = None

                for retry in range(max_retries):
                    company_response, error = make_api_request(f'/api/public/v1/core/companies/{company_id}')

                    if error and "429" in str(error):
                        wait_time = min(5 * (retry + 1), 30)
                        print(f"Rate limited, waiting {wait_time}s before retry {retry+1}/{max_retries}...")
                        time.sleep(wait_time)
                        continue
                    else:
                        break

                if error or not company_response:
                    print(f"❌ Failed to fetch company {company_id}: {error}")
                    error_count += 1
                    failed_companies.append({'id': company_id, 'error': str(error)[:100]})
                    continue

                company_data = company_response.get('result', {})
                if not company_data:
                    print(f"❌ No data for company {company_id}")
                    error_count += 1
                    failed_companies.append({'id': company_id, 'error': 'No data returned'})
                    continue

                # Build record for database
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

                # Upsert into database (insert or update if exists)
                supabase_client.table('companies').upsert(record, on_conflict='company_id').execute()
                synced_count += 1
                print(f"✅ Synced company {company_id}: {company_data.get('name')} (categories: {company_data.get('company_categories', [])})")

            except Exception as e:
                print(f"❌ Error syncing company {company_id}: {e}")
                error_count += 1
                failed_companies.append({'id': company_id, 'error': str(e)[:100]})
                continue

        remaining = total_missing - synced_count
        return jsonify({
            'success': True,
            'message': f'Synced {synced_count} of {total_missing} missing companies. {remaining} remaining - run again to continue.',
            'total_in_invoices': len(invoice_company_ids),
            'total_in_database': len(existing_company_ids),
            'missing_count': total_missing,
            'synced': synced_count,
            'remaining': remaining,
            'errors': error_count,
            'failed_companies': failed_companies[:20]  # Return first 20 failures for debugging
        })

    except Exception as e:
        print(f"❌ Error syncing missing companies: {e}")
        return jsonify({'error': str(e)}), 500


# Global status for full Duano sync
_full_sync_status = {'running': False, 'synced': 0, 'total': 0, 'errors': 0, 'message': '', 'page': 0}

def _background_sync_all_duano_companies(access_token):
    """Background thread to sync ALL companies from Duano CRM API."""
    global _full_sync_status

    try:
        _full_sync_status = {'running': True, 'synced': 0, 'total': 0, 'errors': 0, 'message': 'Starting full Duano sync...', 'page': 0}

        print("🚀 [Full Sync] Starting sync of ALL companies from Duano CRM API...")

        # Headers for direct API calls (no Flask context needed)
        headers = {
            'Authorization': f"Bearer {access_token}",
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        page = 1
        per_page = 50  # CRM endpoint works better with smaller pages
        all_synced = 0
        all_errors = 0

        while True:
            _full_sync_status['page'] = page
            _full_sync_status['message'] = f'Fetching page {page}...'

            print(f"📄 [Full Sync] Fetching page {page}...")

            # Use CRM companies endpoint - returns full company data in list
            try:
                url = f"{DOUANO_CONFIG['base_url']}/api/public/v1/crm/crm-companies"
                api_response = requests.get(url, headers=headers, params={'per_page': per_page, 'page': page}, timeout=60)
                if api_response.status_code != 200:
                    print(f"❌ [Full Sync] API error on page {page}: {api_response.status_code} - {api_response.text[:200]}")
                    _full_sync_status['errors'] += 1
                    # Don't break on single page error, try next page
                    page += 1
                    time.sleep(1)
                    continue
                response = api_response.json()
            except Exception as e:
                print(f"❌ [Full Sync] Error fetching page {page}: {e}")
                _full_sync_status['errors'] += 1
                # Don't break, try next page
                page += 1
                time.sleep(1)
                continue

            # API returns paginated result with 'data' array containing full company objects
            result = response.get('result', {})
            companies = result.get('data', [])

            # Check pagination info
            current_page = result.get('current_page', page)
            last_page = result.get('last_page', 1)
            total_count = result.get('total', 0)

            print(f"📦 [Full Sync] Page {current_page}/{last_page} - Got {len(companies)} companies (Total: {total_count})")

            if not companies:
                if current_page >= last_page:
                    print(f"✅ [Full Sync] No more companies, sync complete!")
                    break
                else:
                    # Empty page but not at end, try next
                    page += 1
                    continue

            _full_sync_status['total'] = total_count

            # Process companies directly from list (CRM endpoint returns full data)
            for company_data in companies:
                try:
                    company_id = company_data.get('id')
                    if not company_id:
                        continue

                    # Extract address from addresses array
                    addresses = company_data.get('addresses', [])
                    primary_address = addresses[0] if addresses else {}

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
                        'email': company_data.get('email_addresses'),
                        'phone_number': primary_address.get('phone_number'),
                        'website': company_data.get('website'),
                        'address_line1': primary_address.get('address_line_1'),
                        'address_line2': primary_address.get('address_line_2'),
                        'city': primary_address.get('city'),
                        'post_code': primary_address.get('post_code'),
                        'country_id': primary_address.get('country', {}).get('id') if primary_address.get('country') else None,
                        'country_name': primary_address.get('country', {}).get('name') if primary_address.get('country') else None,
                        'country_code': primary_address.get('country', {}).get('country_code') if primary_address.get('country') else None,
                        'default_document_notes': company_data.get('default_document_notes', []),
                        'company_categories': company_data.get('company_categories', []),
                        'addresses': addresses,
                        'bank_accounts': company_data.get('bank_accounts', []),
                        'extension_values': company_data.get('extension_values', []),
                        'raw_company_data': company_data,
                        'data_sources': ['douano_crm_api'],
                        'last_sync_at': datetime.now().isoformat()
                    }

                    supabase_client.table('companies').upsert(record, on_conflict='company_id').execute()
                    all_synced += 1
                    _full_sync_status['synced'] = all_synced

                except Exception as e:
                    all_errors += 1
                    _full_sync_status['errors'] = all_errors
                    print(f"❌ [Full Sync] Error syncing company {company_data.get('id', 'unknown')}: {e}")

            print(f"✅ [Full Sync] Page {page} complete. Total synced: {all_synced}")

            # Check if we've reached the last page
            if current_page >= last_page:
                print(f"✅ [Full Sync] Reached last page ({last_page}), sync complete!")
                break

            # Rate limiting between pages
            time.sleep(0.3)
            page += 1

            # Safety limit - increased to 500 pages (25,000 companies max)
            if page > 500:
                print("⚠️ [Full Sync] Reached page limit (500), stopping")
                break

        _full_sync_status['message'] = f'Complete! Synced {all_synced} companies with {all_errors} errors.'
        _full_sync_status['running'] = False
        print(f"🎉 [Full Sync] Complete: {all_synced} synced, {all_errors} errors")

    except Exception as e:
        _full_sync_status['message'] = f'Error: {str(e)}'
        _full_sync_status['running'] = False
        print(f"❌ [Full Sync] Failed: {e}")


@app.route('/api/sync-all-duano-companies', methods=['POST'])
def api_sync_all_duano_companies():
    """Sync ALL companies from Duano API (not just ones with invoices).
    This restores companies that were deleted but exist in Duano.
    Runs in background to avoid timeout.
    """
    global _full_sync_status

    if not is_admin():
        return jsonify({'error': 'Admin access required'}), 403

    if _full_sync_status.get('running'):
        return jsonify({
            'success': False,
            'message': 'Full sync already running',
            'status': _full_sync_status
        })

    # Capture access token before starting thread (thread can't access Flask session)
    access_token = session.get('access_token')
    if not access_token:
        return jsonify({'error': 'Not authenticated - please log in again'}), 401

    # Start background thread with access token
    import threading
    thread = threading.Thread(target=_background_sync_all_duano_companies, args=(access_token,))
    thread.daemon = True
    thread.start()

    return jsonify({
        'success': True,
        'message': 'Full Duano sync started in background. Check /api/full-sync-status for progress.',
        'status': _full_sync_status
    })


@app.route('/api/full-sync-status', methods=['GET'])
def api_full_sync_status():
    """Get the status of the full Duano company sync."""
    return jsonify(_full_sync_status)


# Global status for invoice-based company sync
_invoice_sync_status = {'running': False, 'synced': 0, 'created': 0, 'updated': 0, 'total': 0, 'errors': 0, 'message': ''}

def _background_sync_companies_from_invoices():
    """Background thread to sync companies from invoice data in sales tables."""
    global _invoice_sync_status

    try:
        _invoice_sync_status = {
            'running': True, 'synced': 0, 'created': 0, 'updated': 0,
            'total': 0, 'errors': 0, 'message': 'Starting company sync from invoices...'
        }

        print("🚀 [Invoice Sync] Starting sync of companies from invoice data...")

        if not supabase_client:
            _invoice_sync_status['message'] = 'Error: Supabase not configured'
            _invoice_sync_status['running'] = False
            return

        # Collect unique companies from all sales tables
        all_companies = {}  # company_id -> company_data
        PAGE_SIZE = 500  # Fetch in smaller batches

        for year in ['2024', '2025', '2026']:
            table_name = f'sales_{year}'
            _invoice_sync_status['message'] = f'Reading {table_name}...'
            print(f"📄 [Invoice Sync] Reading {table_name}...")

            try:
                # Use pagination to fetch all invoices
                offset = 0
                total_invoices = 0

                while True:
                    # Fetch batch of invoices with company data
                    result = supabase_client.table(table_name).select(
                        'company_id, company_name, invoice_data'
                    ).range(offset, offset + PAGE_SIZE - 1).execute()

                    if not result.data:
                        break

                    batch_count = len(result.data)
                    total_invoices += batch_count

                    for row in result.data:
                        company_id = row.get('company_id')
                        if not company_id:
                            continue

                        # Extract company data from invoice_data jsonb
                        invoice_data = row.get('invoice_data', {})
                        company_from_invoice = invoice_data.get('company', {}) if invoice_data else {}

                        # Merge with existing data (later years override earlier)
                        if company_id not in all_companies:
                            all_companies[company_id] = {
                                'company_id': company_id,
                                'name': row.get('company_name'),
                                'invoice_company_data': company_from_invoice
                            }
                        else:
                            # Update with newer data if available
                            if company_from_invoice:
                                all_companies[company_id]['invoice_company_data'] = company_from_invoice
                            if row.get('company_name'):
                                all_companies[company_id]['name'] = row.get('company_name')

                    _invoice_sync_status['message'] = f'Reading {table_name}... ({total_invoices} invoices)'
                    print(f"📦 [Invoice Sync] Read {total_invoices} invoices from {table_name} ({len(all_companies)} unique companies)")

                    # Check if we got less than PAGE_SIZE - means we're at the end
                    if batch_count < PAGE_SIZE:
                        break

                    offset += PAGE_SIZE

                print(f"📦 [Invoice Sync] Total: {total_invoices} invoices in {table_name}")

            except Exception as e:
                print(f"❌ [Invoice Sync] Error reading {table_name}: {e}")
                _invoice_sync_status['errors'] += 1
                import traceback
                traceback.print_exc()

        print(f"📊 [Invoice Sync] Total unique companies from invoices: {len(all_companies)}")
        _invoice_sync_status['total'] = len(all_companies)
        _invoice_sync_status['message'] = f'Processing {len(all_companies)} unique companies...'

        # Get existing company IDs from database (with pagination)
        existing_ids = set()
        offset = 0
        while True:
            existing_result = supabase_client.table('companies').select('company_id').range(offset, offset + PAGE_SIZE - 1).execute()
            if not existing_result.data:
                break
            for row in existing_result.data:
                existing_ids.add(row['company_id'])
            if len(existing_result.data) < PAGE_SIZE:
                break
            offset += PAGE_SIZE
        print(f"📋 [Invoice Sync] Existing companies in database: {len(existing_ids)}")

        # Process each unique company
        created_count = 0
        updated_count = 0
        error_count = 0

        for company_id, company_info in all_companies.items():
            try:
                invoice_company = company_info.get('invoice_company_data', {})

                # Build record from invoice company data
                record = {
                    'company_id': company_id,
                    'name': invoice_company.get('name') or company_info.get('name'),
                    'public_name': invoice_company.get('public_name'),
                    'vat_number': invoice_company.get('vat_number'),
                    'is_customer': invoice_company.get('is_customer', True),
                    'is_supplier': invoice_company.get('is_supplier', False),
                    'data_sources': ['invoice_data'],
                    'last_sync_at': datetime.now().isoformat()
                }

                # Extract address if available
                addresses = invoice_company.get('addresses', [])
                if addresses and len(addresses) > 0:
                    addr = addresses[0]
                    record['address_line1'] = addr.get('address_line_1')
                    record['address_line2'] = addr.get('address_line_2')
                    record['city'] = addr.get('city')
                    record['post_code'] = addr.get('post_code')
                    record['phone_number'] = addr.get('phone_number')
                    if addr.get('country'):
                        record['country_id'] = addr['country'].get('id')
                        record['country_name'] = addr['country'].get('name')
                        record['country_code'] = addr['country'].get('country_code')
                    record['addresses'] = addresses

                # Extract other fields
                if invoice_company.get('company_status'):
                    record['company_status_id'] = invoice_company['company_status'].get('id')
                    record['company_status_name'] = invoice_company['company_status'].get('name')

                if invoice_company.get('company_categories'):
                    record['company_categories'] = invoice_company['company_categories']

                record['email_addresses'] = invoice_company.get('email_addresses')
                record['raw_company_data'] = invoice_company if invoice_company else None

                # Check if this is a new company or update
                is_new = company_id not in existing_ids

                # Upsert to database
                supabase_client.table('companies').upsert(record, on_conflict='company_id').execute()

                if is_new:
                    created_count += 1
                    existing_ids.add(company_id)  # Track newly created
                else:
                    updated_count += 1

                _invoice_sync_status['synced'] = created_count + updated_count
                _invoice_sync_status['created'] = created_count
                _invoice_sync_status['updated'] = updated_count

                # Progress update every 50 companies
                if (created_count + updated_count) % 50 == 0:
                    _invoice_sync_status['message'] = f'Processed {created_count + updated_count}/{len(all_companies)} companies ({created_count} new, {updated_count} updated)'
                    print(f"📊 [Invoice Sync] Progress: {created_count + updated_count}/{len(all_companies)}")

            except Exception as e:
                error_count += 1
                _invoice_sync_status['errors'] = error_count
                print(f"❌ [Invoice Sync] Error syncing company {company_id}: {e}")

        _invoice_sync_status['message'] = f'Complete! {created_count} new companies created, {updated_count} updated, {error_count} errors.'
        _invoice_sync_status['running'] = False
        print(f"🎉 [Invoice Sync] Complete: {created_count} created, {updated_count} updated, {error_count} errors")

    except Exception as e:
        _invoice_sync_status['message'] = f'Error: {str(e)}'
        _invoice_sync_status['running'] = False
        print(f"❌ [Invoice Sync] Failed: {e}")
        import traceback
        traceback.print_exc()


@app.route('/api/sync-companies-from-invoices', methods=['POST'])
def api_sync_companies_from_invoices():
    """Sync companies by extracting unique company data from sales invoice tables.
    This restores companies that exist in invoice data but are missing from companies table.
    Runs in background to avoid timeout.
    """
    global _invoice_sync_status

    if not is_admin():
        return jsonify({'error': 'Admin access required'}), 403

    if _invoice_sync_status.get('running'):
        return jsonify({
            'success': False,
            'message': 'Invoice company sync already running',
            'status': _invoice_sync_status
        })

    # Start background thread
    import threading
    thread = threading.Thread(target=_background_sync_companies_from_invoices)
    thread.daemon = True
    thread.start()

    return jsonify({
        'success': True,
        'message': 'Company sync from invoices started in background. Check /api/invoice-company-sync-status for progress.',
        'status': _invoice_sync_status
    })


@app.route('/api/invoice-company-sync-status', methods=['GET'])
def api_invoice_company_sync_status():
    """Get the status of the invoice-based company sync."""
    return jsonify(_invoice_sync_status)


@app.route('/api/update-empty-categories', methods=['POST'])
def api_update_empty_categories():
    """Update companies that have empty categories in the database.
    Fetches current categories from Duano API.
    Admin only - requires DUANO authentication.
    """
    if not is_admin():
        return jsonify({'error': 'Admin access required'}), 403

    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500

        print("🔍 Finding companies with empty categories...")

        # Find companies with empty or null company_categories
        result = supabase_client.table('companies').select(
            'company_id, name, company_categories'
        ).execute()

        companies_to_update = []
        for company in result.data:
            cats = company.get('company_categories')
            # Check for empty, null, or empty array
            if not cats or cats == [] or cats == 'null':
                companies_to_update.append(company)

        print(f"🎯 Companies with empty categories: {len(companies_to_update)}")

        if not companies_to_update:
            return jsonify({
                'success': True,
                'message': 'No companies with empty categories found!',
                'updated': 0,
                'errors': 0
            })

        # Update categories from Duano API
        print(f"🚀 Updating {len(companies_to_update)} companies from DOUANO API...")

        updated_count = 0
        error_count = 0
        failed_companies = []

        for i, company in enumerate(companies_to_update):
            company_id = company['company_id']

            try:
                # Minimal rate limiting
                if i > 0 and i % 25 == 0:
                    time.sleep(0.5)

                # Fetch from DOUANO API
                company_response, error = make_api_request(f'/api/public/v1/core/companies/{company_id}')

                if error or not company_response:
                    print(f"❌ Failed to fetch company {company_id}: {error}")
                    error_count += 1
                    failed_companies.append({'id': company_id, 'name': company['name'], 'error': str(error)[:100]})
                    continue

                company_data = company_response.get('result', {})
                if not company_data:
                    error_count += 1
                    failed_companies.append({'id': company_id, 'name': company['name'], 'error': 'No data'})
                    continue

                # Get categories from API response
                new_categories = company_data.get('company_categories', [])

                # Update the database
                update_data = {
                    'company_categories': new_categories,
                    'raw_company_data': company_data,
                    'updated_at': datetime.now().isoformat()
                }

                supabase_client.table('companies').update(update_data).eq('company_id', company_id).execute()

                cat_names = [c.get('name', c) for c in new_categories] if new_categories else []
                print(f"✅ Updated {company['name']}: {cat_names}")
                updated_count += 1

            except Exception as e:
                print(f"❌ Error updating company {company_id}: {e}")
                error_count += 1
                failed_companies.append({'id': company_id, 'name': company['name'], 'error': str(e)[:100]})

        return jsonify({
            'success': True,
            'message': f'Updated {updated_count} companies with categories',
            'total_empty': len(companies_to_update),
            'updated': updated_count,
            'errors': error_count,
            'failed_companies': failed_companies[:20]
        })

    except Exception as e:
        print(f"❌ Error updating empty categories: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/refresh-company-addresses', methods=['POST'])
def api_refresh_company_addresses():
    """Refresh addresses for all companies from Duano API.
    This fetches the full addresses array for each company.
    Admin only - requires DUANO authentication.
    """
    if not is_admin():
        return jsonify({'error': 'Admin access required'}), 403

    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500

        # Get batch parameters (for handling large datasets)
        # Small batch size to respect Duano API rate limits (each company = 2 API calls)
        batch_start = int(request.args.get('start', 0))
        batch_size = int(request.args.get('batch_size', 10))

        print(f"🔍 Fetching companies from database (offset {batch_start}, limit {batch_size})...")

        # Get companies from database
        result = supabase_client.table('companies').select(
            'company_id, name, addresses'
        ).range(batch_start, batch_start + batch_size - 1).execute()

        companies = result.data
        print(f"📊 Found {len(companies)} companies in this batch")

        if not companies:
            return jsonify({
                'success': True,
                'message': 'No more companies to process',
                'updated': 0,
                'errors': 0,
                'complete': True
            })

        # Update addresses from Duano API
        print(f"🚀 Refreshing addresses for {len(companies)} companies from DOUANO API...")

        updated_count = 0
        error_count = 0
        skipped_count = 0
        failed_companies = []

        # Check if we should skip already-updated companies
        skip_existing = request.args.get('skip_existing', 'true').lower() == 'true'

        for i, company in enumerate(companies):
            company_id = company['company_id']

            try:
                # Skip companies that already have addresses
                existing_addresses = company.get('addresses')
                if skip_existing and existing_addresses and len(existing_addresses) > 0:
                    print(f"  ⏭️ Skipping {company['name']} - already has {len(existing_addresses)} addresses")
                    skipped_count += 1
                    continue

                # Rate limiting - add delay between EACH request to avoid 429
                if i > 0:
                    time.sleep(0.5)  # 500ms between each company

                # Fetch company data from DOUANO API with retry for 429
                company_response, error = None, None
                for retry in range(3):
                    company_response, error = make_api_request(f'/api/public/v1/core/companies/{company_id}')
                    if error and '429' in str(error):
                        wait_time = (retry + 1) * 2  # 2s, 4s, 6s
                        print(f"  ⏳ Rate limited, waiting {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    break

                if error or not company_response:
                    print(f"❌ Failed to fetch company {company_id}: {error}")
                    error_count += 1
                    failed_companies.append({'id': company_id, 'name': company['name'], 'error': str(error)[:100]})
                    continue

                company_data = company_response.get('result', {})
                if not company_data:
                    error_count += 1
                    failed_companies.append({'id': company_id, 'name': company['name'], 'error': 'No data'})
                    continue

                # Small delay before addresses request
                time.sleep(0.3)

                # Fetch addresses from dedicated addresses endpoint with retry for 429
                addresses_response, addr_error = None, None
                for retry in range(3):
                    addresses_response, addr_error = make_api_request(
                        '/api/public/v1/core/addresses',
                        params={'filter_by_company': company_id, 'per_page': 100}
                    )
                    if addr_error and '429' in str(addr_error):
                        wait_time = (retry + 1) * 2
                        print(f"  ⏳ Rate limited on addresses, waiting {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    break

                # Get addresses from dedicated endpoint first, fall back to company response
                new_addresses = []
                if addresses_response and not addr_error:
                    addr_data = addresses_response.get('result', {})
                    if isinstance(addr_data, dict) and 'data' in addr_data:
                        new_addresses = addr_data.get('data', [])
                    elif isinstance(addr_data, list):
                        new_addresses = addr_data
                    print(f"  📍 Fetched {len(new_addresses)} addresses from addresses endpoint for {company['name']}")

                # If no addresses from dedicated endpoint, try company response
                if not new_addresses:
                    new_addresses = company_data.get('addresses', [])

                # Update the database with addresses and full raw data
                update_data = {
                    'addresses': new_addresses,
                    'raw_company_data': company_data,
                    'updated_at': datetime.now().isoformat()
                }

                # Also update other fields that might have been missed
                if company_data.get('company_categories'):
                    update_data['company_categories'] = company_data.get('company_categories')

                supabase_client.table('companies').update(update_data).eq('company_id', company_id).execute()

                addr_count = len(new_addresses) if new_addresses else 0
                print(f"✅ Updated {company['name']}: {addr_count} addresses")
                updated_count += 1

            except Exception as e:
                print(f"❌ Error updating company {company_id}: {e}")
                error_count += 1
                failed_companies.append({'id': company_id, 'name': company['name'], 'error': str(e)[:100]})

        # Check if there are more companies to process
        next_batch_start = batch_start + batch_size
        total_check = supabase_client.table('companies').select('company_id', count='exact').execute()
        total_companies = total_check.count if hasattr(total_check, 'count') else len(total_check.data)
        is_complete = next_batch_start >= total_companies

        return jsonify({
            'success': True,
            'message': f'Updated {updated_count} companies with addresses',
            'batch_start': batch_start,
            'batch_size': len(companies),
            'updated': updated_count,
            'errors': error_count,
            'skipped': skipped_count,
            'failed_companies': failed_companies[:10],
            'next_batch_start': next_batch_start if not is_complete else None,
            'complete': is_complete,
            'total_companies': total_companies
        })

    except Exception as e:
        print(f"❌ Error refreshing company addresses: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/refresh-invoice-addresses', methods=['POST'])
def api_refresh_invoice_addresses():
    """Refresh delivery addresses for invoices from Duano API.
    Fetches full address details for each invoice's address.id.
    Admin only - requires DUANO authentication.
    """
    if not is_admin():
        return jsonify({'error': 'Admin access required'}), 403

    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500

        # Get parameters
        year = request.args.get('year', '2025')
        batch_start = int(request.args.get('start', 0))
        batch_size = int(request.args.get('batch_size', 50))

        if year not in ['2024', '2025', '2026']:
            return jsonify({'error': 'Invalid year. Use 2024, 2025, or 2026'}), 400

        table_name = f'sales_{year}'
        print(f"🔍 Fetching invoices from {table_name} (offset {batch_start}, limit {batch_size})...")

        # Get invoices from database
        result = supabase_client.table(table_name).select(
            'id, invoice_id, invoice_number, invoice_data'
        ).range(batch_start, batch_start + batch_size - 1).execute()

        invoices = result.data
        print(f"📊 Found {len(invoices)} invoices in this batch")

        if not invoices:
            return jsonify({
                'success': True,
                'message': 'No more invoices to process',
                'updated': 0,
                'errors': 0,
                'complete': True
            })

        # Build address lookup - collect unique address IDs first
        address_ids = set()
        for invoice in invoices:
            inv_data = invoice.get('invoice_data', {})
            if isinstance(inv_data, str):
                try:
                    import json
                    inv_data = json.loads(inv_data)
                except:
                    continue

            # Check for address.id in invoice data
            address = inv_data.get('address')
            if address and isinstance(address, dict) and address.get('id'):
                address_ids.add(address['id'])

        print(f"📍 Found {len(address_ids)} unique address IDs to fetch")

        # Fetch address details from Duano API
        address_lookup = {}
        for i, address_id in enumerate(address_ids):
            try:
                # Rate limiting
                if i > 0 and i % 20 == 0:
                    time.sleep(0.3)

                addr_response, addr_error = make_api_request(f'/api/public/v1/core/addresses/{address_id}')

                if addr_response and not addr_error:
                    addr_data = addr_response.get('result', {})
                    if addr_data:
                        address_lookup[address_id] = addr_data
                        print(f"  ✅ Fetched address {address_id}: {addr_data.get('name', addr_data.get('city', 'Unknown'))}")

            except Exception as e:
                print(f"  ❌ Error fetching address {address_id}: {e}")

        print(f"📍 Successfully fetched {len(address_lookup)} address details")

        # Update invoices with address details
        updated_count = 0
        error_count = 0
        skipped_count = 0

        for invoice in invoices:
            try:
                inv_data = invoice.get('invoice_data', {})
                if isinstance(inv_data, str):
                    try:
                        import json
                        inv_data = json.loads(inv_data)
                    except:
                        skipped_count += 1
                        continue

                address = inv_data.get('address')
                if not address or not isinstance(address, dict) or not address.get('id'):
                    skipped_count += 1
                    continue

                address_id = address['id']
                if address_id not in address_lookup:
                    skipped_count += 1
                    continue

                # Enrich the address with full details
                full_address = address_lookup[address_id]
                inv_data['address']['full_details'] = full_address
                inv_data['delivery_address'] = {
                    'id': address_id,
                    'name': full_address.get('name', ''),
                    'address_line1': full_address.get('address_line1', ''),
                    'address_line2': full_address.get('address_line2', ''),
                    'city': full_address.get('city', ''),
                    'post_code': full_address.get('post_code', ''),
                    'country': full_address.get('country', {}),
                    'address_type': full_address.get('address_type', {})
                }

                # Update the invoice in database
                supabase_client.table(table_name).update({
                    'invoice_data': inv_data
                }).eq('id', invoice['id']).execute()

                updated_count += 1

            except Exception as e:
                print(f"❌ Error updating invoice {invoice.get('invoice_id')}: {e}")
                error_count += 1

        # Check if there are more invoices to process
        next_batch_start = batch_start + batch_size
        total_check = supabase_client.table(table_name).select('id', count='exact').execute()
        total_invoices = total_check.count if hasattr(total_check, 'count') else len(total_check.data)
        is_complete = next_batch_start >= total_invoices

        return jsonify({
            'success': True,
            'message': f'Updated {updated_count} invoices with delivery addresses',
            'year': year,
            'batch_start': batch_start,
            'batch_size': len(invoices),
            'addresses_fetched': len(address_lookup),
            'updated': updated_count,
            'skipped': skipped_count,
            'errors': error_count,
            'next_batch_start': next_batch_start if not is_complete else None,
            'complete': is_complete,
            'total_invoices': total_invoices
        })

    except Exception as e:
        print(f"❌ Error refreshing invoice addresses: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/populate-companies', methods=['POST'])
def api_populate_companies():
    """Populate companies table from invoice data across all years.
    Admin only.
    """
    if not is_admin():
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500
        
        # Get data from both years
        def fetch_year_data(year):
            all_invoices = []
            batch_size = 1000
            offset = 0
            
            while True:
                try:
                    batch_result = supabase_client.table(f'sales_{year}').select('*').range(offset, offset + batch_size - 1).execute()
                    
                    if not batch_result.data:
                        break
                        
                    all_invoices.extend(batch_result.data)
                    
                    if len(batch_result.data) < batch_size:
                        break
                        
                    offset += batch_size
                    
                    if offset > 50000:
                        break
                except Exception as e:
                    print(f"Error fetching {year} data at offset {offset}: {e}")
                    break
            
            return all_invoices
        
        # Fetch invoice data from both years
        print("Fetching invoice data from both years...")
        invoices_2024 = fetch_year_data('2024')
        invoices_2025 = fetch_year_data('2025')
        
        print(f"Found {len(invoices_2024)} invoices from 2024, {len(invoices_2025)} invoices from 2025")
        
        # Process company data
        companies_data = {}
        
        def process_invoices(invoices, year):
            for invoice in invoices:
                invoice_data = invoice.get('invoice_data', {})
                company_info = invoice_data.get('company', {})
                
                # Get company ID
                company_id = None
                if company_info and company_info.get('id'):
                    company_id = company_info.get('id')
                elif invoice.get('company_id'):
                    company_id = invoice.get('company_id')
                    if not company_info:
                        company_info = {
                            'id': company_id,
                            'name': invoice.get('company_name') or 'Unknown Company'
                        }
                else:
                    continue
                
                # Initialize or update company data
                if company_id not in companies_data:
                    # Get country information
                    country_info = company_info.get('country', {}) if isinstance(company_info.get('country'), dict) else {}
                    
                    companies_data[company_id] = {
                        'company_id': company_id,
                        'name': company_info.get('name') or company_info.get('public_name') or invoice.get('company_name') or 'Unknown Company',
                        'public_name': company_info.get('public_name'),
                        'vat_number': company_info.get('vat_number'),
                        'email': company_info.get('email'),
                        'phone_number': company_info.get('phone_number'),
                        'website': company_info.get('website'),
                        
                        # Address
                        'address_line1': company_info.get('address_line1'),
                        'address_line2': company_info.get('address_line2'),
                        'city': company_info.get('city'),
                        'post_code': company_info.get('post_code'),
                        'country_id': country_info.get('id'),
                        'country_name': country_info.get('name'),
                        'country_code': country_info.get('country_code'),
                        'is_eu_country': country_info.get('is_eu_ic_country'),
                        
                        # Contact person
                        'contact_person_name': company_info.get('contact_person', {}).get('name') if company_info.get('contact_person') else None,
                        'contact_person_email': company_info.get('contact_person', {}).get('email') if company_info.get('contact_person') else None,
                        'contact_person_phone': company_info.get('contact_person', {}).get('phone') if company_info.get('contact_person') else None,
                        
                        # Business info
                        'industry': company_info.get('industry'),
                        'company_size': company_info.get('company_size'),
                        'business_type': company_info.get('business_type'),
                        'registration_number': company_info.get('registration_number'),
                        
                        # Financial data
                        'total_revenue_2024': 0,
                        'total_revenue_2025': 0,
                        'invoice_count_2024': 0,
                        'invoice_count_2025': 0,
                        'first_invoice_date': None,
                        'last_invoice_date': None,
                        'customer_since': None,
                        
                        # Metadata
                        'payment_terms': set(),
                        'currencies_used': set(),
                        'has_attachments': False,
                        'raw_company_data': company_info,
                        'data_sources': ['invoices']
                    }
                
                # Update financial data - calculate revenue from line items (ex-VAT)
                company = companies_data[company_id]
                invoice_data_obj = invoice.get('invoice_data') or {}
                line_items = invoice_data_obj.get('invoice_line_items') or []
                line_revenue = sum(float(item.get('revenue') or 0) for item in line_items)
                invoice_amount = line_revenue if line_revenue > 0 else float(invoice.get('total_amount') or 0)
                invoice_date = invoice.get('invoice_date')

                # Update year-specific totals
                if year == 2024:
                    company['total_revenue_2024'] += invoice_amount
                    company['invoice_count_2024'] += 1
                else:
                    company['total_revenue_2025'] += invoice_amount
                    company['invoice_count_2025'] += 1
                
                # Update dates
                if invoice_date:
                    if not company['first_invoice_date'] or invoice_date < company['first_invoice_date']:
                        company['first_invoice_date'] = invoice_date
                        company['customer_since'] = invoice_date
                    if not company['last_invoice_date'] or invoice_date > company['last_invoice_date']:
                        company['last_invoice_date'] = invoice_date
                        company['last_activity_date'] = invoice_date
                
                # Collect metadata
                if invoice_data.get('payment_terms'):
                    company['payment_terms'].add(str(invoice_data.get('payment_terms')))
                if invoice_data.get('currency'):
                    company['currencies_used'].add(invoice_data.get('currency'))
                if invoice_data.get('attachments'):
                    company['has_attachments'] = True
        
        # Process both years
        process_invoices(invoices_2024, 2024)
        process_invoices(invoices_2025, 2025)
        
        # Finalize and save companies
        saved_count = 0
        updated_count = 0
        error_count = 0
        
        for company in companies_data.values():
            try:
                # Calculate totals
                company['total_revenue_all_time'] = company['total_revenue_2024'] + company['total_revenue_2025']
                company['invoice_count_all_time'] = company['invoice_count_2024'] + company['invoice_count_2025']
                company['average_invoice_value'] = round(company['total_revenue_all_time'] / company['invoice_count_all_time'], 2) if company['invoice_count_all_time'] > 0 else 0
                
                # Convert sets to arrays
                company['payment_terms'] = list(company['payment_terms'])
                company['currencies_used'] = list(company['currencies_used'])
                
                # Prepare record for database
                record = {
                    'company_id': company['company_id'],
                    'name': company['name'],
                    'public_name': company['public_name'],
                    'vat_number': company['vat_number'],
                    'email': company['email'],
                    'phone_number': company['phone_number'],
                    'website': company['website'],
                    'address_line1': company['address_line1'],
                    'address_line2': company['address_line2'],
                    'city': company['city'],
                    'post_code': company['post_code'],
                    'country_id': company['country_id'],
                    'country_name': company['country_name'],
                    'country_code': company['country_code'],
                    'is_eu_country': company['is_eu_country'],
                    'contact_person_name': company['contact_person_name'],
                    'contact_person_email': company['contact_person_email'],
                    'contact_person_phone': company['contact_person_phone'],
                    'industry': company['industry'],
                    'company_size': company['company_size'],
                    'business_type': company['business_type'],
                    'registration_number': company['registration_number'],
                    'total_revenue_2024': company['total_revenue_2024'],
                    'total_revenue_2025': company['total_revenue_2025'],
                    'total_revenue_all_time': company['total_revenue_all_time'],
                    'invoice_count_2024': company['invoice_count_2024'],
                    'invoice_count_2025': company['invoice_count_2025'],
                    'invoice_count_all_time': company['invoice_count_all_time'],
                    'average_invoice_value': company['average_invoice_value'],
                    'first_invoice_date': company['first_invoice_date'],
                    'last_invoice_date': company['last_invoice_date'],
                    'customer_since': company['customer_since'],
                    'last_activity_date': company.get('last_activity_date'),
                    'payment_terms': company['payment_terms'],
                    'currencies_used': company['currencies_used'],
                    'has_attachments': company['has_attachments'],
                    'raw_company_data': company['raw_company_data'],
                    'data_sources': company['data_sources'],
                    'last_sync_at': datetime.now().isoformat()
                }
                
                # Check if company exists
                existing = supabase_client.table('companies').select('id').eq('company_id', company['company_id']).execute()
                
                if existing.data:
                    # Update existing company
                    record['updated_at'] = datetime.now().isoformat()
                    supabase_client.table('companies').update(record).eq('company_id', company['company_id']).execute()
                    updated_count += 1
                else:
                    # Insert new company
                    supabase_client.table('companies').insert(record).execute()
                    saved_count += 1
                
            except Exception as e:
                print(f"❌ Error saving company {company.get('company_id')}: {e}")
                error_count += 1
                continue
        
        return jsonify({
            'success': True,
            'message': f'Successfully processed {len(companies_data)} companies',
            'total_processed': len(companies_data),
            'saved': saved_count,
            'updated': updated_count,
            'errors': error_count,
            'data_sources': {
                '2024_invoices': len(invoices_2024),
                '2025_invoices': len(invoices_2025)
            }
        })
        
    except Exception as e:
        print(f"❌ Error in companies population: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/companies-stats', methods=['GET'])
def api_companies_stats():
    """Get statistics about companies in the database."""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500
        
        # Get companies data
        companies_result = supabase_client.table('companies').select('*').range(0, 9999).execute()
        
        if not companies_result.data:
            return jsonify({
                'total_companies': 0,
                'total_revenue': 0,
                'total_invoices': 0,
                'companies_with_2024_data': 0,
                'companies_with_2025_data': 0,
                'companies_with_both_years': 0
            })
        
        companies = companies_result.data
        
        stats = {
            'total_companies': len(companies),
            'total_revenue': sum(float(c.get('total_revenue_all_time') or 0) for c in companies),
            'total_invoices': sum(int(c.get('invoice_count_all_time') or 0) for c in companies),
            'companies_with_2024_data': len([c for c in companies if c.get('invoice_count_2024', 0) > 0]),
            'companies_with_2025_data': len([c for c in companies if c.get('invoice_count_2025', 0) > 0]),
            'companies_with_both_years': len([c for c in companies if c.get('invoice_count_2024', 0) > 0 and c.get('invoice_count_2025', 0) > 0]),
            'total_revenue_2024': sum(float(c.get('total_revenue_2024') or 0) for c in companies),
            'total_revenue_2025': sum(float(c.get('total_revenue_2025') or 0) for c in companies),
            'countries_represented': len(set(c.get('country_name') for c in companies if c.get('country_name'))),
            'companies_with_vat': len([c for c in companies if c.get('vat_number')]),
            'companies_with_email': len([c for c in companies if c.get('email')]),
            'companies_with_website': len([c for c in companies if c.get('website')])
        }
        
        return jsonify(stats)
        
    except Exception as e:
        print(f"Error getting companies stats: {e}")
        return jsonify({'error': str(e)}), 500


# ===========================
# WhatsApp Integration Routes
# ===========================

@app.route('/api/whatsapp/webhook', methods=['POST'])
def whatsapp_webhook():
    """
    Twilio WhatsApp webhook endpoint
    Receives incoming WhatsApp messages
    """
    try:
        if WhatsAppService is None:
            return jsonify({'error': 'WhatsApp service not available'}), 503
        
        # Get message data from Twilio
        message_data = request.form.to_dict()
        
        # Initialize service
        whatsapp_service = WhatsAppService()
        
        # Process the message
        result = whatsapp_service.process_incoming_message(message_data)
        
        # Return TwiML response
        from twilio.twiml.messaging_response import MessagingResponse
        response = MessagingResponse()
        
        if result.get('success'):
            # Optionally send an auto-reply
            # response.message("Thanks for your message! We'll get back to you soon.")
            pass
        
        return str(response), 200, {'Content-Type': 'application/xml'}
        
    except Exception as e:
        print(f"Error in WhatsApp webhook: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/whatsapp/inbox')
def whatsapp_inbox_api():
    """
    Get WhatsApp inbox messages
    """
    try:
        if WhatsAppService is None:
            return jsonify({'error': 'WhatsApp service not available'}), 503
        
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        whatsapp_service = WhatsAppService()
        messages = whatsapp_service.get_inbox_messages(limit=limit, offset=offset)
        
        return jsonify({
            'success': True,
            'messages': messages,
            'count': len(messages)
        })
        
    except Exception as e:
        print(f"Error fetching inbox: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/whatsapp/conversation/<phone_number>')
def whatsapp_conversation_api(phone_number):
    """
    Get conversation history for a specific phone number
    """
    try:
        if WhatsAppService is None:
            return jsonify({'error': 'WhatsApp service not available'}), 503
        
        whatsapp_service = WhatsAppService()
        messages = whatsapp_service.get_conversation_history(phone_number)
        
        return jsonify({
            'success': True,
            'phone_number': phone_number,
            'messages': messages,
            'count': len(messages)
        })
        
    except Exception as e:
        print(f"Error fetching conversation: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/whatsapp/mark-read', methods=['POST'])
def whatsapp_mark_read():
    """
    Mark messages from a phone number as read
    """
    try:
        if WhatsAppService is None:
            return jsonify({'error': 'WhatsApp service not available'}), 503
        
        data = request.get_json()
        phone_number = data.get('phone_number')
        
        if not phone_number:
            return jsonify({'error': 'phone_number is required'}), 400
        
        whatsapp_service = WhatsAppService()
        whatsapp_service.mark_as_read(phone_number)
        
        return jsonify({
            'success': True,
            'message': 'Messages marked as read'
        })
        
    except Exception as e:
        print(f"Error marking as read: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/whatsapp/send', methods=['POST'])
def whatsapp_send():
    """
    Send a WhatsApp message
    """
    try:
        if WhatsAppService is None:
            return jsonify({'error': 'WhatsApp service not available'}), 503
        
        data = request.get_json()
        to_number = data.get('to_number')
        message = data.get('message')
        
        if not to_number or not message:
            return jsonify({'error': 'to_number and message are required'}), 400
        
        whatsapp_service = WhatsAppService()
        success = whatsapp_service.send_message(to_number, message)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Message sent successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to send message'
            }), 500
        
    except Exception as e:
        print(f"Error sending message: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/whatsapp/analytics')
def whatsapp_analytics_api():
    """
    Get WhatsApp analytics
    """
    try:
        if WhatsAppService is None:
            return jsonify({'error': 'WhatsApp service not available'}), 503
        
        whatsapp_service = WhatsAppService()
        analytics = whatsapp_service.get_analytics()
        
        return jsonify({
            'success': True,
            'analytics': analytics
        })
        
    except Exception as e:
        print(f"Error fetching analytics: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/whatsapp/message/<message_id>', methods=['DELETE'])
def whatsapp_delete_message(message_id):
    """
    Delete a WhatsApp message
    """
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not available'}), 503
        
        # Delete the message
        result = supabase_client.table('whatsapp_messages').delete().eq('id', message_id).execute()
        
        return jsonify({
            'success': True,
            'message': 'Message deleted successfully'
        })
        
    except Exception as e:
        print(f"Error deleting message: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/whatsapp-inbox')
def whatsapp_inbox_page():
    """
    WhatsApp inbox page
    """
    return render_template('whatsapp_inbox.html')


@app.route('/api/company-notes/<company_id>', methods=['GET', 'POST'])
def api_company_notes(company_id):
    """
    Get or update company notes, status, and assigned salesperson.
    POST can be:
    - JSON: update company metadata (notes, salesperson, status)
    - FormData: create a new note with optional image attachments
    """
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500

        if request.method == 'GET':
            # Get company notes and status
            result = supabase_client.table('companies').select(
                'notes, assigned_salesperson, customer_status'
            ).eq('company_id', int(company_id)).execute()

            if result.data and len(result.data) > 0:
                return jsonify({
                    'success': True,
                    'notes': result.data[0].get('notes', ''),
                    'assigned_salesperson': result.data[0].get('assigned_salesperson', ''),
                    'customer_status': result.data[0].get('customer_status', 'active')
                })
            return jsonify({'success': True, 'notes': '', 'assigned_salesperson': '', 'customer_status': 'active'})

        # POST - Check content type to determine which operation
        content_type = request.content_type or ''

        if 'multipart/form-data' in content_type:
            # FormData request - Create a new note with optional attachments
            import uuid as uuid_module
            note_text = request.form.get('note_text', '')

            # Create the note in company_notes table
            note_result = supabase_client.table('company_notes').insert({
                'company_id': int(company_id),
                'note_text': note_text,
                'created_by': session.get('user_email', 'unknown')
            }).execute()

            if not note_result.data:
                return jsonify({'error': 'Failed to create note'}), 500

            note_id = note_result.data[0]['id']
            attachments = []

            # Handle file uploads
            files = request.files.getlist('files')
            for file in files:
                if file and file.filename:
                    # Validate file type
                    allowed_types = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
                    if file.content_type not in allowed_types:
                        continue

                    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'jpg'
                    unique_filename = f"{uuid_module.uuid4()}.{ext}"
                    storage_path = f"{company_id}/{unique_filename}"

                    file_content = file.read()
                    file_size = len(file_content)

                    # Upload to storage
                    supabase_client.storage.from_('company-attachments').upload(
                        storage_path,
                        file_content,
                        {'content-type': file.content_type}
                    )

                    # Save attachment metadata with note_id
                    att_result = supabase_client.table('company_attachments').insert({
                        'company_id': int(company_id),
                        'note_id': note_id,
                        'file_name': file.filename,
                        'file_type': file.content_type,
                        'file_size': file_size,
                        'storage_path': storage_path,
                        'created_by': session.get('user_email', 'unknown')
                    }).execute()

                    # Generate signed URL
                    signed_url = None
                    try:
                        url_result = supabase_client.storage.from_('company-attachments').create_signed_url(
                            storage_path, 3600
                        )
                        signed_url = url_result.get('signedURL') or url_result.get('signed_url')
                    except Exception:
                        pass

                    attachments.append({
                        'id': att_result.data[0]['id'] if att_result.data else None,
                        'file_name': file.filename,
                        'url': signed_url
                    })

            return jsonify({
                'success': True,
                'note': {
                    'id': note_id,
                    'note_text': note_text,
                    'created_at': note_result.data[0].get('created_at'),
                    'attachments': attachments
                }
            })

        else:
            # JSON request - Update company metadata
            data = request.get_json()
            notes = data.get('notes', '')
            salesperson = data.get('assigned_salesperson', '')
            customer_status = data.get('customer_status', 'active')

            # Update in Supabase
            result = supabase_client.table('companies').update({
                'notes': notes,
                'assigned_salesperson': salesperson,
                'customer_status': customer_status,
                'updated_at': datetime.now().isoformat()
            }).eq('company_id', int(company_id)).execute()

            return jsonify({
                'success': True,
                'message': 'Company details updated successfully'
            })

    except Exception as e:
        print(f"Error with company notes: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/company-flavour-prices/<company_id>', methods=['GET', 'POST'])
def api_company_flavour_prices(company_id):
    """
    Get or update flavour prices for a company
    Stores per-flavour retail prices as JSONB: {"Elderflower": "2.50", "Ginger Lemon": "3.00"}
    """
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500

        if request.method == 'GET':
            # Get flavour prices
            result = supabase_client.table('companies').select(
                'flavour_prices'
            ).eq('company_id', int(company_id)).execute()

            if result.data and len(result.data) > 0:
                return jsonify({
                    'success': True,
                    'prices': result.data[0].get('flavour_prices', {}) or {}
                })
            return jsonify({'success': True, 'prices': {}})

        # POST - Update flavour prices
        data = request.get_json()
        prices = data.get('prices', {})

        # Update in Supabase
        result = supabase_client.table('companies').update({
            'flavour_prices': prices,
            'updated_at': datetime.now().isoformat()
        }).eq('company_id', int(company_id)).execute()

        return jsonify({
            'success': True,
            'message': 'Flavour prices saved successfully'
        })

    except Exception as e:
        print(f"Error with flavour prices: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/company-attachments/<company_id>', methods=['GET'])
def list_company_attachments(company_id):
    """
    List all attachments/photos for a company
    """
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500

        result = supabase_client.table('company_attachments').select(
            'id, file_name, file_type, file_size, storage_path, description, created_at'
        ).eq('company_id', int(company_id)).order('created_at', desc=True).execute()

        attachments = []
        for attachment in (result.data or []):
            # Generate signed URL for the image (valid for 1 hour)
            storage_path = attachment.get('storage_path', '')
            signed_url = None
            if storage_path:
                try:
                    url_result = supabase_client.storage.from_('company-attachments').create_signed_url(
                        storage_path, 3600  # 1 hour expiry
                    )
                    signed_url = url_result.get('signedURL') or url_result.get('signed_url')
                except Exception as url_error:
                    print(f"Error creating signed URL: {url_error}")

            attachments.append({
                'id': attachment['id'],
                'file_name': attachment['file_name'],
                'file_type': attachment.get('file_type'),
                'file_size': attachment.get('file_size'),
                'description': attachment.get('description'),
                'created_at': attachment.get('created_at'),
                'url': signed_url
            })

        return jsonify({
            'success': True,
            'attachments': attachments
        })

    except Exception as e:
        print(f"Error listing attachments: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/company-attachments/<company_id>/upload', methods=['POST'])
def upload_company_attachment(company_id):
    """
    Upload an image attachment for a company
    """
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500

        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if not file.filename:
            return jsonify({'error': 'No file selected'}), 400

        # Validate file type
        allowed_types = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
        if file.content_type not in allowed_types:
            return jsonify({'error': 'Invalid file type. Only images allowed.'}), 400

        # Generate unique filename
        import uuid
        ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'jpg'
        unique_filename = f"{uuid.uuid4()}.{ext}"
        storage_path = f"{company_id}/{unique_filename}"

        # Read file content
        file_content = file.read()
        file_size = len(file_content)

        # Upload to Supabase Storage
        upload_result = supabase_client.storage.from_('company-attachments').upload(
            storage_path,
            file_content,
            {'content-type': file.content_type}
        )

        # Save metadata to database
        result = supabase_client.table('company_attachments').insert({
            'company_id': int(company_id),
            'file_name': file.filename,
            'file_type': file.content_type,
            'file_size': file_size,
            'storage_path': storage_path,
            'description': request.form.get('description', ''),
            'created_by': session.get('user_email', 'unknown')
        }).execute()

        # Generate signed URL for the uploaded image
        signed_url = None
        try:
            url_result = supabase_client.storage.from_('company-attachments').create_signed_url(
                storage_path, 3600
            )
            signed_url = url_result.get('signedURL') or url_result.get('signed_url')
        except Exception as url_error:
            print(f"Error creating signed URL: {url_error}")

        return jsonify({
            'success': True,
            'message': 'Image uploaded successfully',
            'attachment': {
                'id': result.data[0]['id'] if result.data else None,
                'file_name': file.filename,
                'url': signed_url
            }
        })

    except Exception as e:
        print(f"Error uploading attachment: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/company-attachments/<int:attachment_id>', methods=['DELETE'])
def delete_company_attachment(attachment_id):
    """
    Delete an attachment
    """
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500

        # Get attachment info first
        result = supabase_client.table('company_attachments').select(
            'storage_path'
        ).eq('id', attachment_id).execute()

        if not result.data:
            return jsonify({'error': 'Attachment not found'}), 404

        storage_path = result.data[0].get('storage_path')

        # Delete from storage
        if storage_path:
            try:
                supabase_client.storage.from_('company-attachments').remove([storage_path])
            except Exception as storage_error:
                print(f"Error deleting from storage: {storage_error}")

        # Delete from database
        supabase_client.table('company_attachments').delete().eq('id', attachment_id).execute()

        return jsonify({
            'success': True,
            'message': 'Attachment deleted successfully'
        })

    except Exception as e:
        print(f"Error deleting attachment: {str(e)}")
        return jsonify({'error': str(e)}), 500


# ==================== COMPANY NOTES ENDPOINTS ====================

@app.route('/api/company-note-blocks/<company_id>', methods=['GET'])
def list_company_notes(company_id):
    """
    List all notes for a company with their attached images
    """
    try:
        print(f"📝 Loading notes for company_id: {company_id}")
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500

        # Get all notes for the company
        notes_result = supabase_client.table('company_notes').select(
            'id, note_text, created_by, created_at, updated_at'
        ).eq('company_id', int(company_id)).order('created_at', desc=True).execute()
        print(f"📝 Found {len(notes_result.data or [])} notes for company {company_id}")

        notes = []
        for note in (notes_result.data or []):
            # Get attachments linked to this note
            attachments_result = supabase_client.table('company_attachments').select(
                'id, file_name, file_type, storage_path, created_at'
            ).eq('note_id', note['id']).execute()

            attachments = []
            for attachment in (attachments_result.data or []):
                storage_path = attachment.get('storage_path', '')
                signed_url = None
                if storage_path:
                    try:
                        url_result = supabase_client.storage.from_('company-attachments').create_signed_url(
                            storage_path, 3600
                        )
                        signed_url = url_result.get('signedURL') or url_result.get('signed_url')
                    except Exception as url_error:
                        print(f"Error creating signed URL: {url_error}")

                attachments.append({
                    'id': attachment['id'],
                    'file_name': attachment['file_name'],
                    'file_type': attachment.get('file_type'),
                    'url': signed_url
                })

            notes.append({
                'id': note['id'],
                'note_text': note.get('note_text', ''),
                'created_by': note.get('created_by'),
                'created_at': note.get('created_at'),
                'updated_at': note.get('updated_at'),
                'attachments': attachments
            })

        return jsonify({
            'success': True,
            'notes': notes
        })

    except Exception as e:
        print(f"Error listing notes: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/company-notes/<int:note_id>', methods=['PUT'])
def update_company_note(note_id):
    """
    Update a note's text
    """
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500

        data = request.get_json()
        note_text = data.get('note_text', '')

        result = supabase_client.table('company_notes').update({
            'note_text': note_text,
            'updated_at': datetime.now().isoformat()
        }).eq('id', note_id).execute()

        return jsonify({
            'success': True,
            'message': 'Note updated successfully'
        })

    except Exception as e:
        print(f"Error updating note: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/company-notes/<int:note_id>', methods=['DELETE'])
def delete_company_note(note_id):
    """
    Delete a note and its attachments
    """
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500

        # Get attachments linked to this note to delete from storage
        attachments = supabase_client.table('company_attachments').select(
            'storage_path'
        ).eq('note_id', note_id).execute()

        # Delete from storage
        for attachment in (attachments.data or []):
            storage_path = attachment.get('storage_path')
            if storage_path:
                try:
                    supabase_client.storage.from_('company-attachments').remove([storage_path])
                except Exception as storage_error:
                    print(f"Error deleting from storage: {storage_error}")

        # Delete note (attachments will cascade delete due to FK)
        supabase_client.table('company_notes').delete().eq('id', note_id).execute()

        return jsonify({
            'success': True,
            'message': 'Note deleted successfully'
        })

    except Exception as e:
        print(f"Error deleting note: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/company-notes/<int:note_id>/attachment', methods=['POST'])
def add_attachment_to_note(note_id):
    """
    Add an image to an existing note
    """
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500

        # Get the note to find company_id
        note_result = supabase_client.table('company_notes').select('company_id').eq('id', note_id).execute()
        if not note_result.data:
            return jsonify({'error': 'Note not found'}), 404

        company_id = note_result.data[0]['company_id']

        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if not file.filename:
            return jsonify({'error': 'No file selected'}), 400

        # Validate file type
        allowed_types = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
        if file.content_type not in allowed_types:
            return jsonify({'error': 'Invalid file type. Only images allowed.'}), 400

        import uuid
        ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'jpg'
        unique_filename = f"{uuid.uuid4()}.{ext}"
        storage_path = f"{company_id}/{unique_filename}"

        file_content = file.read()
        file_size = len(file_content)

        # Upload to storage
        supabase_client.storage.from_('company-attachments').upload(
            storage_path,
            file_content,
            {'content-type': file.content_type}
        )

        # Save attachment metadata with note_id
        result = supabase_client.table('company_attachments').insert({
            'company_id': company_id,
            'note_id': note_id,
            'file_name': file.filename,
            'file_type': file.content_type,
            'file_size': file_size,
            'storage_path': storage_path,
            'created_by': session.get('user_email', 'unknown')
        }).execute()

        # Generate signed URL
        signed_url = None
        try:
            url_result = supabase_client.storage.from_('company-attachments').create_signed_url(
                storage_path, 3600
            )
            signed_url = url_result.get('signedURL') or url_result.get('signed_url')
        except Exception:
            pass

        return jsonify({
            'success': True,
            'attachment': {
                'id': result.data[0]['id'] if result.data else None,
                'file_name': file.filename,
                'url': signed_url
            }
        })

    except Exception as e:
        print(f"Error adding attachment: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/company-details/<company_id>', methods=['POST'])
def api_update_company_details(company_id):
    """
    Update company contact details
    """
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500
        
        data = request.get_json()
        
        update_data = {
            'updated_at': datetime.now().isoformat()
        }
        
        if 'contact_person' in data:
            update_data['contact_person_name'] = data['contact_person']
        if 'email' in data:
            update_data['email'] = data['email']
        if 'phone' in data:
            update_data['phone_number'] = data['phone']
        if 'website' in data:
            update_data['website'] = data['website']
            
        # Update in Supabase
        result = supabase_client.table('companies').update(update_data).eq('company_id', int(company_id)).execute()
        
        return jsonify({
            'success': True,
            'message': 'Company contact details updated successfully'
        })
        
    except Exception as e:
        print(f"Error updating company details: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/company-trips/<company_id>', methods=['GET'])
def api_company_trips(company_id):
    """
    Get all trips that include this company
    """
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500

        # trip_stops.company_id is VARCHAR, so search as string
        # Try string version first (most likely)
        company_id_str = str(company_id)
        stops_result = supabase_client.table('trip_stops').select(
            'trip_id, stop_order'
        ).eq('company_id', company_id_str).execute()

        # Debug logging
        print(f"Searching for company_id: {company_id_str}, found: {len(stops_result.data or [])} stops")

        if not stops_result.data:
            return jsonify({'success': True, 'trips': []})
        
        # Get unique trip IDs
        trip_ids = list(set(stop['trip_id'] for stop in stops_result.data))
        
        # Fetch trip details with all stops count
        trips_result = supabase_client.table('trips').select('*').in_('id', trip_ids).order('trip_date', desc=True).execute()
        
        trips = []
        for trip in trips_result.data or []:
            # Get stops count for this trip
            trip_stops = supabase_client.table('trip_stops').select('id').eq('trip_id', trip['id']).execute()
            stops_count = len(trip_stops.data) if trip_stops.data else 0
            
            trips.append({
                'id': trip['id'],
                'name': trip.get('name', 'Unnamed Trip'),
                'date': trip.get('trip_date'),
                'status': trip.get('status', 'planned'),
                'distance_km': round(trip.get('total_distance_km', 0) or 0, 1),
                'stops_count': stops_count,
                'start_location': trip.get('start_location'),
                'end_location': trip.get('end_location')
            })
        
        return jsonify({'success': True, 'trips': trips})
        
    except Exception as e:
        print(f"Error getting company trips: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/prospect-notes/<prospect_id>', methods=['POST'])
def api_update_prospect_notes(prospect_id):
    """
    Update prospect notes and assigned salesperson
    """
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500
        
        data = request.get_json()
        notes = data.get('notes', '')
        salesperson = data.get('assigned_salesperson', '')
        
        # Update in Supabase
        result = supabase_client.table('prospects').update({
            'notes': notes,
            'assigned_salesperson': salesperson,
            'updated_at': datetime.now().isoformat()
        }).eq('id', prospect_id).execute()
        
        return jsonify({
            'success': True,
            'message': 'Notes and salesperson updated successfully'
        })
        
    except Exception as e:
        print(f"Error updating prospect notes: {str(e)}")
        return jsonify({'error': str(e)}), 500


# ========================================
# PROSPECT NOTES WITH IMAGES
# ========================================

@app.route('/api/prospect-note-blocks/<prospect_id>', methods=['GET'])
def get_prospect_notes(prospect_id):
    """Get all note blocks for a prospect with their attachments"""
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500

        # Get notes
        notes_result = supabase_client.table('prospect_notes').select('*').eq(
            'prospect_id', prospect_id
        ).order('created_at', desc=True).execute()

        notes = notes_result.data or []

        # Get attachments for all notes
        if notes:
            note_ids = [n['id'] for n in notes]
            attachments_result = supabase_client.table('prospect_attachments').select('*').in_(
                'note_id', note_ids
            ).execute()

            attachments = attachments_result.data or []

            # Generate signed URLs for attachments
            for att in attachments:
                try:
                    url_result = supabase_client.storage.from_('prospect-attachments').create_signed_url(
                        att['storage_path'], 3600
                    )
                    att['url'] = url_result.get('signedURL') or url_result.get('signed_url')
                except Exception:
                    att['url'] = None

            # Group attachments by note_id
            att_by_note = {}
            for att in attachments:
                note_id = att['note_id']
                if note_id not in att_by_note:
                    att_by_note[note_id] = []
                att_by_note[note_id].append(att)

            # Attach to notes
            for note in notes:
                note['attachments'] = att_by_note.get(note['id'], [])
        else:
            for note in notes:
                note['attachments'] = []

        return jsonify({'success': True, 'notes': notes})

    except Exception as e:
        print(f"Error getting prospect notes: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/prospect-note-blocks/<prospect_id>', methods=['POST'])
def create_prospect_note(prospect_id):
    """Create a new note for a prospect with optional image uploads"""
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500

        note_text = request.form.get('note_text', '')

        # Create the note
        note_result = supabase_client.table('prospect_notes').insert({
            'prospect_id': prospect_id,
            'note_text': note_text,
            'created_by': session.get('user_email', 'unknown')
        }).execute()

        if not note_result.data:
            return jsonify({'error': 'Failed to create note'}), 500

        note_id = note_result.data[0]['id']
        attachments = []

        # Handle file uploads
        files = request.files.getlist('files')
        import uuid
        for file in files:
            if file and file.filename:
                # Validate file type
                allowed_types = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
                if file.content_type not in allowed_types:
                    continue

                ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'jpg'
                unique_filename = f"{uuid.uuid4()}.{ext}"
                storage_path = f"{prospect_id}/{unique_filename}"

                file_content = file.read()
                file_size = len(file_content)

                # Upload to storage
                supabase_client.storage.from_('prospect-attachments').upload(
                    storage_path,
                    file_content,
                    {'content-type': file.content_type}
                )

                # Save attachment metadata
                att_result = supabase_client.table('prospect_attachments').insert({
                    'prospect_id': prospect_id,
                    'note_id': note_id,
                    'file_name': file.filename,
                    'file_type': file.content_type,
                    'file_size': file_size,
                    'storage_path': storage_path,
                    'created_by': session.get('user_email', 'unknown')
                }).execute()

                # Generate signed URL
                signed_url = None
                try:
                    url_result = supabase_client.storage.from_('prospect-attachments').create_signed_url(
                        storage_path, 3600
                    )
                    signed_url = url_result.get('signedURL') or url_result.get('signed_url')
                except Exception:
                    pass

                attachments.append({
                    'id': att_result.data[0]['id'] if att_result.data else None,
                    'file_name': file.filename,
                    'url': signed_url
                })

        return jsonify({
            'success': True,
            'note': {
                'id': note_id,
                'note_text': note_text,
                'created_at': note_result.data[0].get('created_at'),
                'attachments': attachments
            }
        })

    except Exception as e:
        print(f"Error creating prospect note: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/prospect-note-blocks/<int:note_id>', methods=['DELETE'])
def delete_prospect_note(note_id):
    """Delete a prospect note and its attachments"""
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500

        # Get attachments first to delete from storage
        attachments_result = supabase_client.table('prospect_attachments').select('*').eq(
            'note_id', note_id
        ).execute()

        # Delete files from storage
        for att in (attachments_result.data or []):
            try:
                supabase_client.storage.from_('prospect-attachments').remove([att['storage_path']])
            except Exception:
                pass

        # Delete note (attachments cascade)
        supabase_client.table('prospect_notes').delete().eq('id', note_id).execute()

        return jsonify({'success': True})

    except Exception as e:
        print(f"Error deleting prospect note: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/prospect-note-blocks/<int:note_id>/attachment', methods=['POST'])
def add_prospect_note_attachment(note_id):
    """Add an image to an existing prospect note"""
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500

        # Get note to find prospect_id
        note_result = supabase_client.table('prospect_notes').select('prospect_id').eq(
            'id', note_id
        ).execute()

        if not note_result.data:
            return jsonify({'error': 'Note not found'}), 404

        prospect_id = note_result.data[0]['prospect_id']

        file = request.files.get('file')
        if not file or not file.filename:
            return jsonify({'error': 'No file provided'}), 400

        # Validate file type
        allowed_types = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
        if file.content_type not in allowed_types:
            return jsonify({'error': 'Invalid file type'}), 400

        import uuid
        ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'jpg'
        unique_filename = f"{uuid.uuid4()}.{ext}"
        storage_path = f"{prospect_id}/{unique_filename}"

        file_content = file.read()
        file_size = len(file_content)

        # Upload to storage
        supabase_client.storage.from_('prospect-attachments').upload(
            storage_path,
            file_content,
            {'content-type': file.content_type}
        )

        # Save attachment metadata
        att_result = supabase_client.table('prospect_attachments').insert({
            'prospect_id': prospect_id,
            'note_id': note_id,
            'file_name': file.filename,
            'file_type': file.content_type,
            'file_size': file_size,
            'storage_path': storage_path,
            'created_by': session.get('user_email', 'unknown')
        }).execute()

        # Generate signed URL
        signed_url = None
        try:
            url_result = supabase_client.storage.from_('prospect-attachments').create_signed_url(
                storage_path, 3600
            )
            signed_url = url_result.get('signedURL') or url_result.get('signed_url')
        except Exception:
            pass

        return jsonify({
            'success': True,
            'attachment': {
                'id': att_result.data[0]['id'] if att_result.data else None,
                'file_name': file.filename,
                'url': signed_url
            }
        })

    except Exception as e:
        print(f"Error adding attachment: {str(e)}")
        return jsonify({'error': str(e)}), 500


# ========================================
# TRIPS MANAGEMENT ENDPOINTS
# ========================================

@app.route('/trips')
def trips_page():
    """Render trips management page"""
    if not is_logged_in():
        return redirect(url_for('index'))

    return render_template('trips.html', google_maps_api_key=GOOGLE_MAPS_API_KEY)


@app.route('/trips/<trip_id>')
def trip_detail_page(trip_id):
    """Render trip detail page"""
    if not is_logged_in():
        return redirect(url_for('index'))

    return render_template('trip_detail.html', trip_id=trip_id, google_maps_api_key=GOOGLE_MAPS_API_KEY)


@app.route('/api/trips', methods=['GET'])
def get_trips():
    """Get all trips"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        if not supabase_client:
            return jsonify({'error': 'Database not available'}), 500
        
        # Get query parameters for filtering
        status = request.args.get('status')
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        
        # Build query
        query = supabase_client.table('trips').select('*')
        
        if status:
            query = query.eq('status', status)
        if from_date:
            query = query.gte('trip_date', from_date)
        if to_date:
            query = query.lte('trip_date', to_date)
        
        # Execute query
        response = query.order('trip_date', desc=True).execute()
        
        return jsonify({
            'success': True,
            'trips': response.data
        })
        
    except Exception as e:
        print(f"Error fetching trips: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/trips/<trip_id>', methods=['GET'])
def get_trip(trip_id):
    """Get a single trip with all its stops"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        if not supabase_client:
            return jsonify({'error': 'Database not available'}), 500

        # Get trip details
        trip_response = supabase_client.table('trips').select('*').eq('id', trip_id).execute()

        if not trip_response.data:
            return jsonify({'error': 'Trip not found'}), 404

        trip = trip_response.data[0]

        # Get trip stops
        stops_response = supabase_client.table('trip_stops').select('*').eq('trip_id', trip_id).order('stop_order').execute()

        stops = stops_response.data or []

        # Enrich stops with company public_name
        for stop in stops:
            if stop.get('company_id'):
                try:
                    # company_id in trip_stops is VARCHAR, companies.company_id is INTEGER
                    company_id_int = int(stop['company_id'])
                    company_response = supabase_client.table('companies').select(
                        'company_id, name, public_name'
                    ).eq('company_id', company_id_int).execute()

                    if company_response.data:
                        company = company_response.data[0]
                        # Use public_name if available, otherwise keep company_name
                        stop['display_name'] = company.get('public_name') or company.get('name') or stop.get('company_name')
                        stop['company_id_int'] = company_id_int
                    else:
                        stop['display_name'] = stop.get('company_name')
                except (ValueError, TypeError):
                    stop['display_name'] = stop.get('company_name')
            else:
                stop['display_name'] = stop.get('company_name')

        trip['stops'] = stops

        return jsonify({
            'success': True,
            'trip': trip
        })

    except Exception as e:
        print(f"Error fetching trip: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/trips', methods=['POST'])
def create_trip():
    """Create a new trip with optimized route"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        if not supabase_client:
            return jsonify({'error': 'Database not available'}), 500
        
        data = request.json
        
        # Validate required fields
        required_fields = ['name', 'trip_date', 'start_location', 'start_time', 'destinations']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        start_location = data['start_location']
        end_location = data.get('end_location')  # Optional end location
        destinations = data['destinations']
        
        if not destinations or len(destinations) == 0:
            return jsonify({'error': 'At least one destination is required'}), 400
        
        # Try to optimize route with timeout protection
        if optimize_trip_route:
            try:
                # Use simple optimizer without Google Maps API calls (faster, no memory issues)
                # Don't pass google_maps_api_key to avoid external API calls on Render
                optimization_result = optimize_trip_route(
                    start_location=start_location,
                    destinations=destinations,
                    google_maps_api_key=None  # Use Haversine distance only
                )
                
                if optimization_result.get('success'):
                    ordered_stops = optimization_result['ordered_stops']
                    total_distance_km = optimization_result.get('total_distance_km', 0)
                    estimated_duration_minutes = optimization_result.get('estimated_duration_minutes', len(destinations) * 30)
                    print(f"✅ Route optimized: {total_distance_km}km, {estimated_duration_minutes}min")
                else:
                    # Optimization failed, use simple order
                    print(f"⚠️ Optimization failed: {optimization_result.get('error')}")
                    ordered_stops = destinations
                    total_distance_km = 0
                    estimated_duration_minutes = len(destinations) * 30
            except Exception as opt_error:
                print(f"⚠️ Route optimization error: {opt_error}, using simple order")
                import traceback
                traceback.print_exc()
                ordered_stops = destinations
                total_distance_km = 0
                estimated_duration_minutes = len(destinations) * 30
        else:
            # No optimizer available, use simple order
            print("⚠️ No route optimizer available, using simple order")
            ordered_stops = destinations
            total_distance_km = 0
            estimated_duration_minutes = len(destinations) * 30
        
        # Create trip record
        trip_data = {
            'name': data['name'],
            'trip_date': data['trip_date'],
            'start_location': start_location.get('address', start_location.get('name', 'Start')),
            'start_time': data['start_time'],
            'start_lat': start_location['lat'],
            'start_lng': start_location['lng'],
            'status': 'planned',
            'total_distance_km': total_distance_km,
            'estimated_duration_minutes': estimated_duration_minutes,
            'notes': data.get('notes', '')
        }
        
        # Add end location if provided
        if end_location:
            trip_data['end_location'] = end_location.get('address', end_location.get('name', 'End'))
            trip_data['end_lat'] = end_location.get('lat')
            trip_data['end_lng'] = end_location.get('lng')
        
        trip_response = supabase_client.table('trips').insert(trip_data).execute()
        
        if not trip_response.data:
            return jsonify({'error': 'Failed to create trip in database'}), 500
        
        trip_id = trip_response.data[0]['id']
        
        # Create trip stops in order
        stops_data = []
        for idx, stop in enumerate(ordered_stops):
            # Get company_id - handle both 'id' and 'company_id' fields
            company_id_value = stop.get('company_id') or stop.get('id')
            # Try to convert to int if possible
            try:
                company_id_value = int(company_id_value) if company_id_value else None
            except (ValueError, TypeError):
                company_id_value = str(company_id_value) if company_id_value else None
            
            stop_data = {
                'trip_id': trip_id,
                'company_id': company_id_value,
                'company_name': stop.get('name', 'Unknown'),
                'address': stop.get('address', ''),
                'latitude': stop.get('lat') or stop.get('latitude'),
                'longitude': stop.get('lng') or stop.get('longitude'),
                'stop_order': idx + 1,
                'duration_minutes': 30  # Default duration
            }
            stops_data.append(stop_data)
        
        # Insert all stops in batches to avoid timeout
        if stops_data:
            # Insert in smaller batches for reliability
            batch_size = 10
            for i in range(0, len(stops_data), batch_size):
                batch = stops_data[i:i + batch_size]
                supabase_client.table('trip_stops').insert(batch).execute()
        
        # Return minimal response to avoid timeout - client will fetch full details
        return jsonify({
            'success': True,
            'trip': {
                'id': trip_id,
                'name': data['name'],
                'trip_date': data['trip_date'],
                'start_location': trip_data.get('start_location'),
                'total_distance_km': total_distance_km,
                'estimated_duration_minutes': estimated_duration_minutes,
                'stops_count': len(stops_data)
            },
            'message': 'Trip created successfully' + (' with optimized route' if optimize_trip_route else '')
        })
        
    except Exception as e:
        print(f"Error creating trip: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/geocode-companies', methods=['POST'])
def geocode_all_companies():
    """Geocode all companies that don't have coordinates yet"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        if not supabase_client:
            return jsonify({'error': 'Database not available'}), 500
        
        # Import the geocoding logic
        try:
            from geocode_companies import get_company_address, geocode_address_mapbox
        except ImportError as e:
            print(f"Geocoding import error: {e}")
            return jsonify({'error': f'Geocoding module not available: {str(e)}'}), 500
        
        # Get request parameters
        data = request.json or {}
        limit = data.get('limit', 100)  # Default to 100 companies at a time
        force = data.get('force', False)
        
        # Fetch companies without coordinates
        query = supabase_client.table('companies').select('*')
        
        if not force:
            # Only companies without geocoded_at timestamp
            query = query.is_('geocoded_at', 'null')
        
        if limit:
            query = query.limit(limit)
        
        result = query.execute()
        companies = result.data
        
        if not companies:
            return jsonify({
                'success': True,
                'message': 'No companies need geocoding',
                'geocoded': 0,
                'failed': 0,
                'skipped': 0
            })
        
        # Mapbox API key
        mapbox_key = "pk.eyJ1IjoiaGVuZHJpa3l1Z2VuIiwiYSI6ImNtY24zZnB4YTAwNTYybnMzNGVpemZxdGEifQ.HIpLMTGycSiEsf7ytxaSJg"
        
        # Process each company
        success_count = 0
        failed_count = 0
        skipped_count = 0
        
        for company in companies:
            address = get_company_address(company)
            
            if not address:
                skipped_count += 1
                continue
            
            # Geocode using Mapbox
            geocode_result = geocode_address_mapbox(address, 'BE')
            
            if geocode_result:
                lat, lng, quality = geocode_result
                
                # Update database directly with supabase_client
                try:
                    supabase_client.table('companies').update({
                        'latitude': lat,
                        'longitude': lng,
                        'geocoded_address': address,
                        'geocoding_quality': quality,
                        'geocoded_at': datetime.utcnow().isoformat(),
                        'geocoding_provider': 'mapbox'
                    }).eq('id', company['id']).execute()
                    success_count += 1
                except Exception as update_error:
                    print(f"Error updating coordinates: {update_error}")
                    failed_count += 1
            else:
                failed_count += 1
            
            # Small delay to respect rate limits
            time.sleep(0.1)
        
        return jsonify({
            'success': True,
            'geocoded': success_count,
            'failed': failed_count,
            'skipped': skipped_count,
            'total_processed': len(companies),
            'message': f'Geocoded {success_count} companies successfully'
        })
        
    except Exception as e:
        print(f"Error geocoding companies: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/geocode-delivery-addresses', methods=['POST'])
def geocode_delivery_addresses():
    """Geocode all delivery addresses in the addresses JSONB column.
    This adds lat/lng to each address object for map features.
    """
    if not is_admin():
        return jsonify({'error': 'Admin access required'}), 403

    try:
        if not supabase_client:
            return jsonify({'error': 'Database not available'}), 500

        # Import geocoding function
        try:
            from geocode_companies import geocode_address_mapbox
        except ImportError as e:
            return jsonify({'error': f'Geocoding module not available: {str(e)}'}), 500

        # Get batch parameters
        batch_start = int(request.args.get('start', 0))
        batch_size = int(request.args.get('batch_size', 10))
        skip_geocoded = request.args.get('skip_geocoded', 'true').lower() == 'true'

        print(f"🗺️ Geocoding delivery addresses (offset {batch_start}, limit {batch_size})...")

        # Fetch companies with addresses
        result = supabase_client.table('companies').select(
            'id, company_id, name, addresses'
        ).not_.is_('addresses', 'null').range(batch_start, batch_start + batch_size - 1).execute()

        companies = result.data
        print(f"📊 Found {len(companies)} companies with addresses in this batch")

        if not companies:
            return jsonify({
                'success': True,
                'message': 'No more companies to process',
                'geocoded': 0,
                'skipped': 0,
                'errors': 0,
                'complete': True
            })

        geocoded_count = 0
        skipped_count = 0
        error_count = 0
        addresses_processed = 0

        for company in companies:
            addresses = company.get('addresses', [])
            if not addresses or not isinstance(addresses, list):
                continue

            updated = False
            for addr in addresses:
                if not isinstance(addr, dict):
                    continue

                # Skip if already geocoded
                if skip_geocoded and addr.get('latitude') and addr.get('longitude'):
                    skipped_count += 1
                    continue

                # Build address string
                parts = [
                    addr.get('address_line1') or addr.get('street'),
                    addr.get('city'),
                    addr.get('post_code'),
                    addr.get('country', {}).get('name') if isinstance(addr.get('country'), dict) else addr.get('country')
                ]
                address_str = ', '.join([str(p) for p in parts if p])

                if not address_str or len(address_str) < 10:
                    skipped_count += 1
                    continue

                # Rate limiting
                time.sleep(0.15)  # ~6 requests per second

                # Geocode
                try:
                    result = geocode_address_mapbox(address_str, 'BE')
                    if result:
                        lat, lng, quality = result
                        addr['latitude'] = lat
                        addr['longitude'] = lng
                        addr['geocoding_quality'] = quality
                        addr['geocoded_at'] = datetime.now().isoformat()
                        geocoded_count += 1
                        updated = True
                        print(f"  ✅ {addr.get('name', 'Address')}: {lat}, {lng}")
                    else:
                        error_count += 1
                        print(f"  ❌ Failed to geocode: {address_str[:50]}")
                except Exception as e:
                    error_count += 1
                    print(f"  ❌ Error geocoding: {e}")

                addresses_processed += 1

            # Update company with geocoded addresses
            if updated:
                try:
                    supabase_client.table('companies').update({
                        'addresses': addresses
                    }).eq('id', company['id']).execute()
                except Exception as e:
                    print(f"  ❌ Error saving addresses for {company['name']}: {e}")

        # Check if complete
        total_check = supabase_client.table('companies').select('id', count='exact').not_.is_('addresses', 'null').execute()
        total_companies = total_check.count if hasattr(total_check, 'count') else 0
        next_batch = batch_start + batch_size
        is_complete = next_batch >= total_companies

        return jsonify({
            'success': True,
            'message': f'Geocoded {geocoded_count} addresses',
            'batch_start': batch_start,
            'geocoded': geocoded_count,
            'skipped': skipped_count,
            'errors': error_count,
            'addresses_processed': addresses_processed,
            'next_batch_start': next_batch if not is_complete else None,
            'complete': is_complete,
            'total_companies_with_addresses': total_companies
        })

    except Exception as e:
        print(f"❌ Error geocoding delivery addresses: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/trips/<trip_id>', methods=['PUT'])
def update_trip(trip_id):
    """Update trip details"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        if not supabase_client:
            return jsonify({'error': 'Database not available'}), 500
        
        data = request.json
        
        # Update trip
        update_data = {}
        allowed_fields = ['name', 'trip_date', 'start_time', 'status', 'notes']
        
        for field in allowed_fields:
            if field in data:
                update_data[field] = data[field]
        
        if not update_data:
            return jsonify({'error': 'No valid fields to update'}), 400
        
        response = supabase_client.table('trips').update(update_data).eq('id', trip_id).execute()
        
        if not response.data:
            return jsonify({'error': 'Trip not found'}), 404
        
        return jsonify({
            'success': True,
            'trip': response.data[0],
            'message': 'Trip updated successfully'
        })
        
    except Exception as e:
        print(f"Error updating trip: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/trips/<trip_id>', methods=['DELETE'])
def delete_trip(trip_id):
    """Delete a trip (and all its stops via CASCADE)"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        if not supabase_client:
            return jsonify({'error': 'Database not available'}), 500
        
        response = supabase_client.table('trips').delete().eq('id', trip_id).execute()
        
        return jsonify({
            'success': True,
            'message': 'Trip deleted successfully'
        })
        
    except Exception as e:
        print(f"Error deleting trip: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/trips/<trip_id>/stops/<stop_id>', methods=['DELETE'])
def delete_trip_stop(trip_id, stop_id):
    """Delete a stop from a trip and reorder remaining stops"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        if not supabase_client:
            return jsonify({'error': 'Database not available'}), 500
        
        # Get the stop to be deleted
        stop_response = supabase_client.table('trip_stops').select('*').eq('id', stop_id).execute()
        
        if not stop_response.data:
            return jsonify({'error': 'Stop not found'}), 404
        
        deleted_order = stop_response.data[0]['stop_order']
        
        # Delete the stop
        supabase_client.table('trip_stops').delete().eq('id', stop_id).execute()
        
        # Reorder remaining stops
        remaining_stops = supabase_client.table('trip_stops').select('*').eq('trip_id', trip_id).order('stop_order').execute()
        
        for idx, stop in enumerate(remaining_stops.data):
            new_order = idx + 1
            if stop['stop_order'] != new_order:
                supabase_client.table('trip_stops').update({'stop_order': new_order}).eq('id', stop['id']).execute()
        
        # Recalculate trip distance (simplified - just update the count)
        # In a production system, you'd want to recalculate the actual distance
        
        return jsonify({
            'success': True,
            'message': 'Stop deleted and route reordered'
        })
        
    except Exception as e:
        print(f"Error deleting trip stop: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/trips/<trip_id>/stops/<stop_id>/checklist', methods=['PUT'])
def update_stop_checklist(trip_id, stop_id):
    """Update checklist items for a trip stop"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        if not supabase_client:
            return jsonify({'error': 'Database not available'}), 500

        data = request.json
        checklist = data.get('checklist', [])

        # Verify stop exists and belongs to the trip
        stop_response = supabase_client.table('trip_stops').select('*').eq('id', stop_id).eq('trip_id', trip_id).execute()

        if not stop_response.data:
            return jsonify({'error': 'Stop not found'}), 404

        # Update the checklist (stored as JSONB)
        result = supabase_client.table('trip_stops').update({
            'checklist': checklist
        }).eq('id', stop_id).execute()

        if result.data:
            return jsonify({
                'success': True,
                'checklist': checklist
            })
        else:
            return jsonify({'error': 'Failed to update checklist'}), 500

    except Exception as e:
        print(f"Error updating stop checklist: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/trips/<trip_id>/reorder', methods=['POST'])
def reorder_trip_stops(trip_id):
    """Reorder stops in a trip (manual drag and drop)"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        if not supabase_client:
            return jsonify({'error': 'Database not available'}), 500
        
        data = request.json
        stops = data.get('stops', [])
        
        if not stops:
            return jsonify({'error': 'No stops provided'}), 400
        
        # Verify trip exists
        trip_response = supabase_client.table('trips').select('*').eq('id', trip_id).execute()
        
        if not trip_response.data:
            return jsonify({'error': 'Trip not found'}), 404
        
        # Update each stop's order
        for stop in stops:
            stop_id = stop.get('id')
            new_order = stop.get('order')
            
            if stop_id and new_order:
                supabase_client.table('trip_stops').update({
                    'stop_order': new_order
                }).eq('id', stop_id).execute()
        
        # Recalculate total distance based on new order
        stops_response = supabase_client.table('trip_stops').select('*').eq('trip_id', trip_id).order('stop_order').execute()
        
        if stops_response.data and len(stops_response.data) > 1:
            # Calculate new distance using Haversine formula
            total_distance = 0
            for i in range(len(stops_response.data) - 1):
                stop1 = stops_response.data[i]
                stop2 = stops_response.data[i + 1]
                
                if stop1.get('latitude') and stop1.get('longitude') and stop2.get('latitude') and stop2.get('longitude'):
                    from math import radians, sin, cos, sqrt, atan2
                    
                    lat1, lon1 = radians(float(stop1['latitude'])), radians(float(stop1['longitude']))
                    lat2, lon2 = radians(float(stop2['latitude'])), radians(float(stop2['longitude']))
                    
                    dlat = lat2 - lat1
                    dlon = lon2 - lon1
                    
                    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                    c = 2 * atan2(sqrt(a), sqrt(1-a))
                    
                    # Earth radius in km
                    total_distance += 6371 * c
            
            # Update trip with new distance
            supabase_client.table('trips').update({
                'total_distance_km': round(total_distance, 1)
            }).eq('id', trip_id).execute()
        
        return jsonify({
            'success': True,
            'message': 'Stops reordered successfully'
        })
        
    except Exception as e:
        print(f"Error reordering trip stops: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/trips/<trip_id>/optimize', methods=['POST'])
def reoptimize_trip(trip_id):
    """Re-optimize an existing trip's route"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        if not supabase_client:
            return jsonify({'error': 'Database not available'}), 500
        
        if not optimize_trip_route:
            return jsonify({'error': 'Route optimizer not available'}), 500
        
        # Get trip and stops
        trip_response = supabase_client.table('trips').select('*').eq('id', trip_id).execute()
        
        if not trip_response.data:
            return jsonify({'error': 'Trip not found'}), 404
        
        trip = trip_response.data[0]
        
        stops_response = supabase_client.table('trip_stops').select('*').eq('trip_id', trip_id).execute()
        stops = stops_response.data
        
        if not stops:
            return jsonify({'error': 'No stops to optimize'}), 400
        
        # Prepare data for optimization
        start_location = {
            'lat': float(trip['start_lat']),
            'lng': float(trip['start_lng']),
            'name': trip['start_location']
        }
        
        destinations = []
        for stop in stops:
            destinations.append({
                'lat': float(stop['latitude']),
                'lng': float(stop['longitude']),
                'name': stop['company_name'],
                'address': stop['address'],
                'company_id': stop['company_id']
            })
        
        # Optimize
        optimization_result = optimize_trip_route(
            start_location=start_location,
            destinations=destinations,
            google_maps_api_key=GOOGLE_MAPS_API_KEY
        )
        
        if not optimization_result.get('success'):
            return jsonify({
                'error': 'Failed to optimize route',
                'details': optimization_result.get('error')
            }), 400
        
        # Update trip with new distance and duration
        supabase_client.table('trips').update({
            'total_distance_km': optimization_result['total_distance_km'],
            'estimated_duration_minutes': optimization_result['estimated_duration_minutes']
        }).eq('id', trip_id).execute()
        
        # Update stop orders based on optimization
        for idx, optimized_stop in enumerate(optimization_result['ordered_stops']):
            # Find the matching stop by coordinates
            for stop in stops:
                if (abs(float(stop['latitude']) - optimized_stop['latitude']) < 0.0001 and
                    abs(float(stop['longitude']) - optimized_stop['longitude']) < 0.0001):
                    supabase_client.table('trip_stops').update({
                        'stop_order': idx + 1
                    }).eq('id', stop['id']).execute()
                    break
        
        return jsonify({
            'success': True,
            'message': 'Trip route re-optimized successfully',
            'total_distance_km': optimization_result['total_distance_km'],
            'estimated_duration_minutes': optimization_result['estimated_duration_minutes']
        })
        
    except Exception as e:
        print(f"Error re-optimizing trip: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# =====================================================
# ROUTE SCHEDULING ENDPOINTS
# =====================================================

@app.route('/api/trips/quick-create', methods=['POST'])
def quick_create_trip():
    """Create a quick trip with a single stop (Schedule Visit)"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        if not supabase_client:
            return jsonify({'error': 'Database not available'}), 500

        data = request.json
        location = data.get('location')

        if not location or not location.get('lat') or not location.get('lng'):
            return jsonify({'error': 'Valid location with coordinates required'}), 400

        trip_date = data.get('trip_date', datetime.now().strftime('%Y-%m-%d'))
        start_time = data.get('start_time', '09:00')

        # Create trip
        trip_data = {
            'name': data.get('name', f"Visit: {location.get('name', 'Location')}"),
            'trip_date': trip_date,
            'start_location': location.get('address', location.get('name', 'Start')),
            'start_time': start_time,
            'start_lat': location['lat'],
            'start_lng': location['lng'],
            'status': 'planned',
            'total_distance_km': 0,
            'estimated_duration_minutes': 30,
            'created_by': data.get('salesperson', session.get('user_email', '')),
            'notes': data.get('notes', '')
        }

        trip_response = supabase_client.table('trips').insert(trip_data).execute()

        if not trip_response.data:
            return jsonify({'error': 'Failed to create trip'}), 500

        trip_id = trip_response.data[0]['id']

        # Create single stop
        # company_id in trip_stops is VARCHAR, store as string
        company_id_val = location.get('company_id')
        if company_id_val:
            company_id_val = str(company_id_val)
        else:
            company_id_val = None

        stop_data = {
            'trip_id': trip_id,
            'company_id': company_id_val,
            'company_name': location.get('name', 'Unknown'),
            'address': location.get('address', ''),
            'latitude': location['lat'],
            'longitude': location['lng'],
            'stop_order': 1,
            'duration_minutes': 30,
            'notes': f"Google Place ID: {location.get('google_place_id')}" if location.get('google_place_id') else ''
        }

        supabase_client.table('trip_stops').insert(stop_data).execute()

        return jsonify({
            'success': True,
            'trip': trip_response.data[0],
            'message': 'Visit scheduled successfully'
        })

    except Exception as e:
        print(f"Error creating quick trip: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/trips/<trip_id>/add-stop', methods=['POST'])
def add_stop_to_trip(trip_id):
    """Add a new stop to an existing trip"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        if not supabase_client:
            return jsonify({'error': 'Database not available'}), 500

        data = request.json
        location = data.get('location')

        if not location or not location.get('lat') or not location.get('lng'):
            return jsonify({'error': 'Valid location with coordinates required'}), 400

        # Verify trip exists
        trip_response = supabase_client.table('trips').select('*').eq('id', trip_id).execute()
        if not trip_response.data:
            return jsonify({'error': 'Trip not found'}), 404

        # Get current max stop_order
        stops_response = supabase_client.table('trip_stops').select('stop_order').eq('trip_id', trip_id).order('stop_order', desc=True).limit(1).execute()
        max_order = stops_response.data[0]['stop_order'] if stops_response.data else 0

        # Create new stop
        # company_id in trip_stops is VARCHAR, store as string
        company_id_val = location.get('company_id')
        if company_id_val:
            company_id_val = str(company_id_val)
        else:
            company_id_val = None

        stop_data = {
            'trip_id': trip_id,
            'company_id': company_id_val,
            'company_name': location.get('name', 'Unknown'),
            'address': location.get('address', ''),
            'latitude': location['lat'],
            'longitude': location['lng'],
            'stop_order': max_order + 1,
            'duration_minutes': 30,
            'notes': f"Google Place ID: {location.get('google_place_id')}" if location.get('google_place_id') else ''
        }

        stop_response = supabase_client.table('trip_stops').insert(stop_data).execute()

        if not stop_response.data:
            return jsonify({'error': 'Failed to add stop'}), 500

        return jsonify({
            'success': True,
            'stop': stop_response.data[0],
            'message': f'Added as stop #{max_order + 1}'
        })

    except Exception as e:
        print(f"Error adding stop to trip: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/trips/for-location', methods=['GET'])
def get_trips_for_location():
    """Get all trips containing a specific location"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        if not supabase_client:
            return jsonify({'error': 'Database not available'}), 500

        company_id = request.args.get('company_id')
        lat = request.args.get('lat')
        lng = request.args.get('lng')

        stops_data = []

        if company_id:
            # Search by company_id (try both string and int)
            stops_result = supabase_client.table('trip_stops').select('id, trip_id, stop_order').eq('company_id', company_id).execute()
            stops_data = stops_result.data or []

            if not stops_data:
                try:
                    stops_result = supabase_client.table('trip_stops').select('id, trip_id, stop_order').eq('company_id', int(company_id)).execute()
                    stops_data = stops_result.data or []
                except:
                    pass

        elif lat and lng:
            # Search by coordinates with tolerance
            lat_f = float(lat)
            lng_f = float(lng)
            tolerance = 0.0001

            all_stops = supabase_client.table('trip_stops').select('id, trip_id, stop_order, latitude, longitude').execute()

            stops_data = [
                {'id': s['id'], 'trip_id': s['trip_id'], 'stop_order': s['stop_order']}
                for s in (all_stops.data or [])
                if s.get('latitude') and s.get('longitude') and
                   abs(float(s['latitude']) - lat_f) < tolerance and
                   abs(float(s['longitude']) - lng_f) < tolerance
            ]
        else:
            return jsonify({'error': 'Either company_id or lat/lng required'}), 400

        if not stops_data:
            return jsonify({'success': True, 'trips': []})

        # Get unique trip IDs and stop IDs
        trip_stops_map = {}
        for stop in stops_data:
            trip_stops_map[stop['trip_id']] = stop['id']

        trip_ids = list(trip_stops_map.keys())

        # Fetch trip details
        trips_result = supabase_client.table('trips').select('*').in_('id', trip_ids).order('trip_date', desc=True).execute()

        trips = []
        for trip in trips_result.data or []:
            trips.append({
                'id': trip['id'],
                'name': trip.get('name', 'Unnamed Trip'),
                'date': trip.get('trip_date'),
                'status': trip.get('status', 'planned'),
                'salesperson': trip.get('created_by', ''),
                'stop_id': trip_stops_map.get(trip['id'])
            })

        return jsonify({'success': True, 'trips': trips})

    except Exception as e:
        print(f"Error getting trips for location: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/trips/by-location', methods=['DELETE'])
def delete_trips_by_location():
    """Delete all scheduled visits for a location"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        if not supabase_client:
            return jsonify({'error': 'Database not available'}), 500

        company_id = request.args.get('company_id')
        lat = request.args.get('lat')
        lng = request.args.get('lng')

        stops_to_delete = []

        if company_id:
            stops_result = supabase_client.table('trip_stops').select('id, trip_id').eq('company_id', company_id).execute()
            stops_to_delete = stops_result.data or []

            if not stops_to_delete:
                try:
                    stops_result = supabase_client.table('trip_stops').select('id, trip_id').eq('company_id', int(company_id)).execute()
                    stops_to_delete = stops_result.data or []
                except:
                    pass

        elif lat and lng:
            lat_f = float(lat)
            lng_f = float(lng)
            tolerance = 0.0001

            all_stops = supabase_client.table('trip_stops').select('id, trip_id, latitude, longitude').execute()

            stops_to_delete = [
                {'id': s['id'], 'trip_id': s['trip_id']}
                for s in (all_stops.data or [])
                if s.get('latitude') and s.get('longitude') and
                   abs(float(s['latitude']) - lat_f) < tolerance and
                   abs(float(s['longitude']) - lng_f) < tolerance
            ]
        else:
            return jsonify({'error': 'Either company_id or lat/lng required'}), 400

        if not stops_to_delete:
            return jsonify({'success': True, 'deleted_count': 0, 'trips_affected': []})

        affected_trip_ids = list(set(s['trip_id'] for s in stops_to_delete))
        stop_ids = [s['id'] for s in stops_to_delete]

        # Delete the stops
        for stop_id in stop_ids:
            supabase_client.table('trip_stops').delete().eq('id', stop_id).execute()

        # Reorder remaining stops in affected trips
        for trip_id in affected_trip_ids:
            remaining = supabase_client.table('trip_stops').select('*').eq('trip_id', trip_id).order('stop_order').execute()
            for idx, stop in enumerate(remaining.data or []):
                if stop['stop_order'] != idx + 1:
                    supabase_client.table('trip_stops').update({'stop_order': idx + 1}).eq('id', stop['id']).execute()

        return jsonify({
            'success': True,
            'deleted_count': len(stop_ids),
            'trips_affected': affected_trip_ids
        })

    except Exception as e:
        print(f"Error deleting trips by location: {str(e)}")
        return jsonify({'error': str(e)}), 500


# =====================================================
# TRIP STOP NOTES ENDPOINTS
# =====================================================

@app.route('/api/trip-stop-notes/<int:stop_id>', methods=['GET'])
def get_trip_stop_notes(stop_id):
    """Get all notes for a trip stop with their attachments"""
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500

        # Get notes for this stop
        notes_result = supabase_client.table('trip_stop_notes').select('*').eq(
            'trip_stop_id', stop_id
        ).order('created_at', desc=True).execute()

        notes = notes_result.data or []

        # Get attachments for each note
        for note in notes:
            attachments_result = supabase_client.table('trip_stop_attachments').select('*').eq(
                'note_id', note['id']
            ).execute()

            attachments = attachments_result.data or []

            # Generate public URLs for each attachment
            for att in attachments:
                try:
                    url_response = supabase_client.storage.from_('trip-attachments').get_public_url(
                        att['storage_path']
                    )
                    att['url'] = url_response
                except Exception as e:
                    print(f"Error getting attachment URL: {e}")
                    att['url'] = None

            note['attachments'] = attachments

        return jsonify({'success': True, 'notes': notes})

    except Exception as e:
        print(f"Error getting trip stop notes: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/trip-stop-notes/<int:stop_id>', methods=['POST'])
def create_trip_stop_note(stop_id):
    """Create a new note for a trip stop with optional image uploads"""
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500

        note_text = request.form.get('note_text', '')

        # Create the note
        note_result = supabase_client.table('trip_stop_notes').insert({
            'trip_stop_id': stop_id,
            'note_text': note_text,
            'created_by': session.get('user_email', 'unknown')
        }).execute()

        if not note_result.data:
            return jsonify({'error': 'Failed to create note'}), 500

        note = note_result.data[0]
        note_id = note['id']

        # Handle image uploads
        uploaded_attachments = []
        files = request.files.getlist('images')

        for file in files:
            if file and file.filename:
                # Generate unique filename
                ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'jpg'
                unique_filename = f"stop_{stop_id}/{note_id}/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"

                # Read file content
                file_content = file.read()
                file_size = len(file_content)

                try:
                    # Upload to Supabase Storage
                    upload_response = supabase_client.storage.from_('trip-attachments').upload(
                        unique_filename,
                        file_content,
                        {'content-type': file.content_type or 'image/jpeg'}
                    )

                    # Create attachment record
                    attachment_data = {
                        'trip_stop_id': stop_id,
                        'note_id': note_id,
                        'file_name': file.filename,
                        'file_type': file.content_type or 'image/jpeg',
                        'file_size': file_size,
                        'storage_path': unique_filename,
                        'created_by': session.get('user_email', 'unknown')
                    }

                    att_result = supabase_client.table('trip_stop_attachments').insert(attachment_data).execute()

                    if att_result.data:
                        att = att_result.data[0]
                        # Get public URL
                        url_response = supabase_client.storage.from_('trip-attachments').get_public_url(unique_filename)
                        att['url'] = url_response
                        uploaded_attachments.append(att)

                except Exception as upload_error:
                    print(f"Error uploading file {file.filename}: {upload_error}")

        note['attachments'] = uploaded_attachments

        return jsonify({'success': True, 'note': note})

    except Exception as e:
        print(f"Error creating trip stop note: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/trip-stop-notes/<int:note_id>', methods=['DELETE'])
def delete_trip_stop_note(note_id):
    """Delete a trip stop note and its attachments"""
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500

        # Get attachments to delete from storage
        attachments = supabase_client.table('trip_stop_attachments').select('storage_path').eq(
            'note_id', note_id
        ).execute()

        # Delete files from storage
        for att in (attachments.data or []):
            try:
                supabase_client.storage.from_('trip-attachments').remove([att['storage_path']])
            except Exception:
                pass

        # Delete note (attachments cascade due to FK)
        supabase_client.table('trip_stop_notes').delete().eq('id', note_id).execute()

        return jsonify({'success': True})

    except Exception as e:
        print(f"Error deleting trip stop note: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/trip-stop-notes/<int:note_id>/attachment', methods=['POST'])
def add_trip_stop_note_attachment(note_id):
    """Add an image to an existing trip stop note"""
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500

        # Get note to find stop_id
        note_result = supabase_client.table('trip_stop_notes').select('trip_stop_id').eq(
            'id', note_id
        ).execute()

        if not note_result.data:
            return jsonify({'error': 'Note not found'}), 404

        stop_id = note_result.data[0]['trip_stop_id']

        file = request.files.get('file')
        if not file or not file.filename:
            return jsonify({'error': 'No file provided'}), 400

        # Generate unique filename
        unique_filename = f"stop_{stop_id}/{note_id}/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"

        # Read file content
        file_content = file.read()
        file_size = len(file_content)

        # Upload to Supabase Storage
        supabase_client.storage.from_('trip-attachments').upload(
            unique_filename,
            file_content,
            {'content-type': file.content_type or 'image/jpeg'}
        )

        # Create attachment record
        attachment_data = {
            'trip_stop_id': stop_id,
            'note_id': note_id,
            'file_name': file.filename,
            'file_type': file.content_type or 'image/jpeg',
            'file_size': file_size,
            'storage_path': unique_filename,
            'created_by': session.get('user_email', 'unknown')
        }

        att_result = supabase_client.table('trip_stop_attachments').insert(attachment_data).execute()

        if att_result.data:
            att = att_result.data[0]
            url_response = supabase_client.storage.from_('trip-attachments').get_public_url(unique_filename)
            att['url'] = url_response
            return jsonify({'success': True, 'attachment': att})

        return jsonify({'error': 'Failed to save attachment'}), 500

    except Exception as e:
        print(f"Error adding attachment: {str(e)}")
        return jsonify({'error': str(e)}), 500


# =====================================================
# AI CHAT ENDPOINT - RAG with Database Context
# =====================================================

# Database schema for AI context - ACCURATE JSONB STRUCTURE
DATABASE_SCHEMA = """
IMPORTANT: Most detailed data is in JSONB columns!

**companies** - Customer/company master data
Key columns:
- company_id (integer): Unique ID
- name (text): Company name
- city, country_name
- total_revenue_2024, total_revenue_2025, total_revenue_all_time (numeric)
- invoice_count_2024, invoice_count_2025, invoice_count_all_time (integer)
- first_invoice_date, last_invoice_date (date)
- assigned_salesperson (varchar)

JSONB column `raw_company_data` contains:
{
  "id": 23073,
  "tag": "000847",
  "name": "Company Name",
  "vat_number": "BE0874264958",
  "public_name": "Display Name",
  "invoice_address": {
    "city": "Waregem",
    "post_code": "8790",
    "address_line1": "Street 14",
    "country": {"id": 1, "name": "België"}
  },
  "company_categories": [
    {"id": 12, "name": "Chain"},
    {"id": 13, "name": "Convenience"}
  ],
  "sales_price_class": {"id": 51, "name": "Retail"},
  "company_status": {"id": 1, "name": "Actief"}
}

**sales_2024** / **sales_2025** - Invoice data
Key columns:
- invoice_id (integer)
- company_id (integer), company_name (text)
- invoice_number (text)
- invoice_date (date) - USE THIS FOR DATE FILTERING!
- total_amount (numeric) - Invoice total in EUR
- is_paid (boolean)

JSONB column `invoice_data` contains line items and details:
{
  "id": 198496,
  "date": "2025-11-24",
  "balance": 39026.72,
  "company": {"id": 1324, "name": "Delhaize"},
  "invoice_number": "202503244",
  "invoice_line_items": [
    {
      "product": {"id": 880, "name": "Box Yugen Ginger Lemon Bio Cans 24x32cl"},
      "quantity": 270,
      "price": 41.28,
      "revenue": 11045.30,
      "discount": 0.009,
      "liters": 2073.6,
      "payable_amount": 11708.02
    }
  ],
  "payable_amount_with_financial_discount": 39026.72
}

**Distributor Tables** (Biofresh/Delhaize/Geers/Inter Drinks/Terroirist + year)
- naam_klant: customer name
- stad: city
- product, smaak (flavor), verpakking (packaging)
- aantal: quantity sold
- maand: month, jaar: year
- verantwoordelijke: sales rep
"""

@app.route('/api/ai-chat', methods=['POST'])
def api_ai_chat():
    """
    AI Chat endpoint - Uses OpenAI with function calling to query sales data
    """
    if not openai_client:
        return jsonify({'success': False, 'error': 'OpenAI not configured'}), 500
    
    if not supabase_client:
        return jsonify({'success': False, 'error': 'Database not configured'}), 500
    
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        history = data.get('history', [])
        context = data.get('context', {})
        
        if not user_message:
            return jsonify({'success': False, 'error': 'No message provided'}), 400
        
        # Define available tools/functions
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "query_companies",
                    "description": "Query the companies table to get customer data, revenue, and invoice counts. Use first_invoice_date to find NEW customers.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "order_by": {
                                "type": "string",
                                "enum": ["total_revenue_all_time", "total_revenue_2025", "total_revenue_2024", "invoice_count_all_time", "name", "last_invoice_date", "first_invoice_date"],
                                "description": "Field to order results by"
                            },
                            "order_desc": {
                                "type": "boolean",
                                "description": "Whether to order descending (highest first)"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Number of results to return (max 50)"
                            },
                            "city_filter": {
                                "type": "string",
                                "description": "Filter by city name (partial match)"
                            },
                            "min_revenue": {
                                "type": "number",
                                "description": "Minimum total revenue filter"
                            },
                            "first_invoice_after": {
                                "type": "string",
                                "description": "Filter for NEW customers - first_invoice_date >= this date (YYYY-MM-DD)"
                            },
                            "first_invoice_before": {
                                "type": "string",
                                "description": "Filter for NEW customers - first_invoice_date < this date (YYYY-MM-DD)"
                            }
                        },
                        "required": ["order_by", "order_desc", "limit"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "query_invoices_by_date",
                    "description": "Query invoices filtered by date range. Use this for monthly/weekly revenue questions. Returns invoices with total_amount.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "year": {
                                "type": "string",
                                "enum": ["2024", "2025"],
                                "description": "Which year table to query"
                            },
                            "date_from": {
                                "type": "string",
                                "description": "Start date filter YYYY-MM-DD (e.g. 2025-11-01 for November)"
                            },
                            "date_to": {
                                "type": "string",
                                "description": "End date filter YYYY-MM-DD (e.g. 2025-11-30 for end of November)"
                            },
                            "company_name": {
                                "type": "string",
                                "description": "Filter by company name (optional)"
                            },
                            "order_by": {
                                "type": "string",
                                "enum": ["total_amount", "invoice_date", "company_name"],
                                "description": "Field to order by"
                            },
                            "order_desc": {
                                "type": "boolean",
                                "description": "Order descending"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Number of results (max 100)"
                            }
                        },
                        "required": ["year", "limit"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_revenue_by_period",
                    "description": "Calculate total revenue for a specific month. Uses same calculation as homepage (total_amount field).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "year": {
                                "type": "string",
                                "enum": ["2024", "2025"],
                                "description": "Which year"
                            },
                            "month": {
                                "type": "integer",
                                "description": "Month number 1-12 (e.g. 11 for November)"
                            },
                            "company_id": {
                                "type": "integer",
                                "description": "Optional: filter by specific company_id"
                            }
                        },
                        "required": ["year", "month"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_yearly_monthly_breakdown",
                    "description": "Get revenue breakdown for ALL months in a year. Use this for 'best month', 'monthly comparison', or 'year overview'. Returns same values as homepage.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "year": {
                                "type": "string",
                                "enum": ["2024", "2025"],
                                "description": "Which year to analyze"
                            }
                        },
                        "required": ["year"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_top_invoices",
                    "description": "Get the largest invoices by total_amount for a period",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "year": {
                                "type": "string",
                                "enum": ["2024", "2025"]
                            },
                            "month": {
                                "type": "integer",
                                "description": "Month number 1-12"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Number of top invoices to return"
                            }
                        },
                        "required": ["year", "limit"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "query_distributor_sales",
                    "description": "Query distributor/wholesaler sales data (Biofresh, Delhaize, Geers, Inter Drinks, Terroirist) - shows product sales to end customers",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "distributor": {
                                "type": "string",
                                "enum": ["Biofresh", "Delhaize", "Geers", "Inter Drinks", "Terroirist"],
                                "description": "Which distributor to query"
                            },
                            "year": {
                                "type": "string",
                                "enum": ["2022", "2023", "2024", "2025"],
                                "description": "Which year"
                            },
                            "product_filter": {
                                "type": "string",
                                "description": "Filter by product name"
                            },
                            "city_filter": {
                                "type": "string",
                                "description": "Filter by city (stad)"
                            },
                            "month_filter": {
                                "type": "string",
                                "description": "Filter by month name (e.g. 'november', 'oktober')"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Number of results (max 100)"
                            }
                        },
                        "required": ["distributor", "year", "limit"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_summary_stats",
                    "description": "Get summary statistics",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "stat_type": {
                                "type": "string",
                                "enum": ["total_companies", "total_revenue_2024", "total_revenue_2025", "total_invoices_2024", "total_invoices_2025", "top_cities", "top_products_2025"],
                                "description": "Type of statistic"
                            }
                        },
                        "required": ["stat_type"]
                    }
                }
            }
        ]
        
        # Build system prompt
        current_date = datetime.now()
        current_month = current_date.month
        current_year_num = current_date.year
        
        system_prompt = f"""You are a precise sales analytics assistant for YUGEN, a Belgian kombucha beverage company.
You MUST use the available tools to fetch real data before answering ANY question about numbers, revenue, customers, or invoices.

TODAY'S DATE: {current_date.strftime('%Y-%m-%d')} (December 2025)
Current month number: {current_month}

CRITICAL RULES:
1. NEVER make up numbers or estimates - ALWAYS call a tool first
2. If a tool returns data, use ONLY those exact numbers in your response
3. If a tool returns an error or empty data, say "I couldn't retrieve that data" - don't guess
4. When asked about "this month" in December 2025, use month=12. For November, use month=11

TOOL MAPPING:
- "What is our revenue for [month]?" → get_revenue_by_period(year="2025", month=X)
- "Best month" / "monthly breakdown" / "compare months" → get_yearly_monthly_breakdown(year="2025")
- "Top/biggest invoices/orders" → get_top_invoices(year="2025", month=X, limit=10)
- "New customers this month" → query_companies(first_invoice_after="2025-11-01", first_invoice_before="2025-12-01", order_by="first_invoice_date", limit=20)
- "Top customers by revenue" → query_companies(order_by="total_revenue_all_time", order_desc=true, limit=10)
- "Best selling products" → get_summary_stats(stat_type="top_products_2025")
- "Total revenue 2025" → get_summary_stats(stat_type="total_revenue_2025")
- "How many customers" → get_summary_stats(stat_type="total_companies")

Revenue values use the same calculation as the homepage dashboard (total_amount field from invoices).

RESPONSE FORMAT:
- Use Belgian number format: €1.234,56
- Be concise but include the actual data
- List results clearly when showing multiple items

Context: Viewing {context.get('currentYear', '2025')} data, {context.get('totalCompanies', 0)} companies in database
"""

        # Build messages for OpenAI
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add recent history (without function calls)
        for msg in history[-4:]:
            if msg.get('role') in ['user', 'assistant']:
                messages.append({"role": msg['role'], "content": msg['content'][:500]})  # Truncate long messages
        
        messages.append({"role": "user", "content": user_message})
        
        # First call - let the model decide if it needs tools
        response = openai_client.chat.completions.create(
            model="gpt-5.1",
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.5,
            max_completion_tokens=16000
        )
        
        response_message = response.choices[0].message
        sql_data = None
        
        # Check if model wants to call tools
        if response_message.tool_calls:
            # Execute the tool calls
            tool_results = []
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                print(f"AI calling tool: {function_name} with args: {function_args}")
                
                result = execute_ai_tool(function_name, function_args)
                tool_results.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "content": json.dumps(result, default=str)
                })
                
                # Store the data for the frontend
                if isinstance(result, list) and len(result) > 0:
                    sql_data = result
            
            # Add the assistant message and tool results
            messages.append(response_message)
            messages.extend(tool_results)
            
            # Get final response with data context
            final_response = openai_client.chat.completions.create(
                model="gpt-5.1",
                messages=messages,
                temperature=0.5,
                max_completion_tokens=16000
            )
            
            ai_response = final_response.choices[0].message.content
        else:
            ai_response = response_message.content
        
        return jsonify({
            'success': True,
            'response': ai_response,
            'data': sql_data
        })
        
    except Exception as e:
        print(f"AI Chat error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


def execute_ai_tool(function_name, args):
    """Execute an AI tool and return results"""
    try:
        if function_name == "query_companies":
            order_by = args.get('order_by', 'total_revenue_all_time')
            order_desc = args.get('order_desc', True)
            limit = min(args.get('limit', 10), 50)
            
            query = supabase_client.table('companies').select(
                'name, city, total_revenue_all_time, total_revenue_2024, total_revenue_2025, invoice_count_all_time, first_invoice_date, last_invoice_date, assigned_salesperson'
            )
            
            if args.get('city_filter'):
                query = query.ilike('city', f"%{args['city_filter']}%")
            
            if args.get('min_revenue'):
                query = query.gte('total_revenue_all_time', args['min_revenue'])
            
            # Filter for NEW customers by first_invoice_date
            if args.get('first_invoice_after'):
                query = query.gte('first_invoice_date', args['first_invoice_after'])
            
            if args.get('first_invoice_before'):
                query = query.lt('first_invoice_date', args['first_invoice_before'])
            
            result = query.order(order_by, desc=order_desc).limit(limit).execute()
            return result.data
        
        elif function_name == "query_invoices_by_date":
            year = args.get('year', '2025')
            limit = min(args.get('limit', 20), 100)
            table = f'sales_{year}'
            
            query = supabase_client.table(table).select(
                'invoice_number, company_name, invoice_date, total_amount, is_paid, invoice_data'
            )
            
            if args.get('date_from'):
                query = query.gte('invoice_date', args['date_from'])
            
            if args.get('date_to'):
                query = query.lte('invoice_date', args['date_to'])
            
            if args.get('company_name'):
                query = query.ilike('company_name', f"%{args['company_name']}%")
            
            result = query.limit(500).execute()
            
            # Process to get amounts from line items (ex-VAT)
            processed = []
            for r in result.data:
                invoice_data = r.get('invoice_data') or {}
                line_items = invoice_data.get('invoice_line_items') or []
                line_revenue = sum(float(item.get('revenue') or 0) for item in line_items)
                # Fall back to total_amount only if no line items
                amount = line_revenue if line_revenue > 0 else float(r.get('total_amount') or 0)

                processed.append({
                    'invoice_number': r.get('invoice_number'),
                    'company_name': r.get('company_name'),
                    'invoice_date': r.get('invoice_date'),
                    'total_amount': round(amount, 2),
                    'is_paid': r.get('is_paid')
                })
            
            # Sort based on requested field
            order_by = args.get('order_by', 'invoice_date')
            order_desc = args.get('order_desc', True)
            
            if order_by == 'total_amount':
                processed.sort(key=lambda x: x['total_amount'], reverse=order_desc)
            elif order_by == 'invoice_date':
                processed.sort(key=lambda x: x['invoice_date'] or '', reverse=order_desc)
            else:
                processed.sort(key=lambda x: x.get(order_by, ''), reverse=order_desc)
            
            return processed[:limit]
        
        elif function_name == "get_revenue_by_period":
            year = args.get('year', '2025')
            month = args.get('month')
            table = f'sales_{year}'
            
            # Build date range for the month
            date_from = f"{year}-{month:02d}-01"
            if month == 12:
                date_to = f"{int(year)+1}-01-01"
            else:
                date_to = f"{year}-{month+1:02d}-01"
            
            query = supabase_client.table(table).select('total_amount, company_name, invoice_date, invoice_data')
            query = query.gte('invoice_date', date_from).lt('invoice_date', date_to)
            
            if args.get('company_id'):
                query = query.eq('company_id', args['company_id'])
            
            result = query.execute()
            
            # Calculate revenue from line items (ex-VAT) - matches DUANO's "Omzet"
            total_revenue = 0

            for r in result.data:
                invoice_data = r.get('invoice_data') or {}
                line_items = invoice_data.get('invoice_line_items') or []
                line_revenue = sum(float(item.get('revenue') or 0) for item in line_items)
                # Fall back to total_amount only if no line items
                total_revenue += line_revenue if line_revenue > 0 else float(r.get('total_amount') or 0)
            
            invoice_count = len(result.data)
            
            month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June', 
                          'July', 'August', 'September', 'October', 'November', 'December']
            
            return [{
                "period": f"{month_names[month]} {year}",
                "total_revenue": round(total_revenue, 2),
                "invoice_count": invoice_count,
                "average_invoice": round(total_revenue / invoice_count, 2) if invoice_count > 0 else 0
            }]
        
        elif function_name == "get_yearly_monthly_breakdown":
            year = args.get('year', '2025')
            table = f'sales_{year}'
            
            month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June', 
                          'July', 'August', 'September', 'October', 'November', 'December']
            
            # Get all invoices for the year - same fields as homepage uses
            result = supabase_client.table(table).select('invoice_date, total_amount, invoice_data').execute()
            
            # Group by month - use SAME calculation as homepage
            monthly_data = {m: {'revenue': 0, 'count': 0} for m in range(1, 13)}
            
            for r in result.data:
                invoice_date = r.get('invoice_date')
                if not invoice_date:
                    continue
                
                # Extract month from date
                try:
                    month_num = int(invoice_date.split('-')[1])
                except:
                    continue
                
                # Calculate revenue from line items (ex-VAT) - matches DUANO's "Omzet"
                invoice_data = r.get('invoice_data') or {}
                line_items = invoice_data.get('invoice_line_items') or []
                line_revenue = sum(float(item.get('revenue') or 0) for item in line_items)
                # Fall back to total_amount only if no line items
                amount = line_revenue if line_revenue > 0 else float(r.get('total_amount') or 0)

                monthly_data[month_num]['revenue'] += amount
                monthly_data[month_num]['count'] += 1
            
            # Build result sorted by month
            breakdown = []
            total_year_revenue = 0
            best_month = None
            best_revenue = 0
            
            for m in range(1, 13):
                data = monthly_data[m]
                total_year_revenue += data['revenue']
                
                if data['revenue'] > best_revenue:
                    best_revenue = data['revenue']
                    best_month = month_names[m]
                
                breakdown.append({
                    "month": month_names[m],
                    "month_num": m,
                    "revenue": round(data['revenue'], 2),
                    "invoice_count": data['count']
                })
            
            return [{
                "year": year,
                "total_year_revenue": round(total_year_revenue, 2),
                "best_month": best_month,
                "best_month_revenue": round(best_revenue, 2),
                "monthly_breakdown": breakdown
            }]
        
        elif function_name == "get_top_invoices":
            year = args.get('year', '2025')
            month = args.get('month')
            limit = min(args.get('limit', 10), 50)
            table = f'sales_{year}'
            
            # Select including invoice_data to get amounts from JSONB if needed
            query = supabase_client.table(table).select(
                'invoice_number, company_name, invoice_date, total_amount, invoice_data'
            )
            
            if month:
                date_from = f"{year}-{month:02d}-01"
                if month == 12:
                    date_to = f"{int(year)+1}-01-01"
                else:
                    date_to = f"{year}-{month+1:02d}-01"
                query = query.gte('invoice_date', date_from).lt('invoice_date', date_to)
            
            # Get more results to sort properly (some might have null total_amount)
            result = query.limit(500).execute()
            
            # Process results - calculate revenue from line items (ex-VAT)
            processed = []
            for r in result.data:
                invoice_data = r.get('invoice_data') or {}
                line_items = invoice_data.get('invoice_line_items') or []
                line_revenue = sum(float(item.get('revenue') or 0) for item in line_items)
                # Fall back to total_amount only if no line items
                amount = line_revenue if line_revenue > 0 else float(r.get('total_amount') or 0)

                processed.append({
                    'invoice_number': r.get('invoice_number'),
                    'company_name': r.get('company_name'),
                    'invoice_date': r.get('invoice_date'),
                    'total_amount': round(amount, 2)
                })
            
            # Sort by amount descending and return top N
            processed.sort(key=lambda x: x['total_amount'], reverse=True)
            return processed[:limit]
        
        elif function_name == "query_distributor_sales":
            distributor = args.get('distributor')
            year = args.get('year')
            limit = min(args.get('limit', 20), 100)
            
            table_name = f'{distributor} {year}'
            
            query = supabase_client.table(table_name).select(
                'naam_klant, stad, product, smaak, aantal, maand, verantwoordelijke'
            )
            
            if args.get('product_filter'):
                query = query.ilike('product', f"%{args['product_filter']}%")
            
            if args.get('city_filter'):
                query = query.ilike('stad', f"%{args['city_filter']}%")
            
            if args.get('month_filter'):
                query = query.ilike('maand', f"%{args['month_filter']}%")
            
            result = query.limit(limit).execute()
            return result.data
        
        elif function_name == "get_summary_stats":
            stat_type = args.get('stat_type')
            
            if stat_type == "total_companies":
                result = supabase_client.table('companies').select('*', count='exact').execute()
                return [{"total_companies": result.count}]
            
            elif stat_type == "total_revenue_2024":
                result = supabase_client.table('companies').select('total_revenue_2024').execute()
                total = sum(float(r.get('total_revenue_2024') or 0) for r in result.data)
                return [{"total_revenue_2024": round(total, 2)}]
            
            elif stat_type == "total_revenue_2025":
                result = supabase_client.table('companies').select('total_revenue_2025').execute()
                total = sum(float(r.get('total_revenue_2025') or 0) for r in result.data)
                return [{"total_revenue_2025": round(total, 2)}]
            
            elif stat_type == "total_invoices_2024":
                result = supabase_client.table('sales_2024').select('*', count='exact').execute()
                return [{"total_invoices_2024": result.count}]
            
            elif stat_type == "total_invoices_2025":
                result = supabase_client.table('sales_2025').select('*', count='exact').execute()
                return [{"total_invoices_2025": result.count}]
            
            elif stat_type == "top_cities":
                result = supabase_client.table('companies').select('city, total_revenue_all_time').execute()
                city_revenue = {}
                for r in result.data:
                    city = r.get('city') or 'Unknown'
                    revenue = float(r.get('total_revenue_all_time') or 0)
                    city_revenue[city] = city_revenue.get(city, 0) + revenue
                
                top_cities = sorted(city_revenue.items(), key=lambda x: x[1], reverse=True)[:10]
                return [{"city": c, "revenue": round(r, 2)} for c, r in top_cities]
            
            elif stat_type == "top_products_2025":
                # Get invoices with invoice_data to extract products
                result = supabase_client.table('sales_2025').select('invoice_data').limit(500).execute()
                product_revenue = {}
                
                for r in result.data:
                    invoice_data = r.get('invoice_data', {})
                    if isinstance(invoice_data, dict):
                        line_items = invoice_data.get('invoice_line_items', [])
                        for item in line_items:
                            if isinstance(item, dict):
                                product = item.get('product', {})
                                product_name = product.get('name', 'Unknown') if isinstance(product, dict) else 'Unknown'
                                revenue = float(item.get('revenue', 0) or 0)
                                product_revenue[product_name] = product_revenue.get(product_name, 0) + revenue
                
                top_products = sorted(product_revenue.items(), key=lambda x: x[1], reverse=True)[:15]
                return [{"product": p, "revenue": round(r, 2)} for p, r in top_products]
        
        return []
        
    except Exception as e:
        print(f"Tool execution error: {e}")
        import traceback
        traceback.print_exc()
        return [{"error": str(e)}]


# =====================================================
# DEBUG ENDPOINTS
# =====================================================

@app.route('/api/test-sync', methods=['GET'])
def api_test_sync():
    """Test endpoint to verify API is working"""
    try:
        return jsonify({
            'success': True,
            'message': 'API is working',
            'token_valid': is_token_valid(),
            'supabase_configured': supabase_client is not None,
            'has_access_token': 'access_token' in session,
            'has_token_expires': 'token_expires_at' in session
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/fix-null-amounts', methods=['POST'])
def api_fix_null_amounts():
    """Fix invoices that have NULL total_amount by calculating from invoice_data"""
    if not is_admin():
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        # Get all invoices with NULL total_amount
        null_invoices = supabase_client.table('sales_2025').select(
            'id, invoice_id, invoice_data, company_name'
        ).is_('total_amount', 'null').limit(500).execute()
        
        if not null_invoices.data:
            return jsonify({'success': True, 'message': 'No NULL invoices found', 'fixed': 0})
        
        fixed_count = 0
        errors = []
        
        for inv in null_invoices.data:
            try:
                invoice_data = inv.get('invoice_data') or {}
                
                # Try to get amount from invoice_data
                amount = (
                    invoice_data.get('payable_amount_without_financial_discount') or
                    invoice_data.get('payable_amount_with_financial_discount') or
                    invoice_data.get('total_amount') or
                    invoice_data.get('balance') or
                    0
                )
                
                # If still 0, calculate from line items
                if amount == 0:
                    line_items = invoice_data.get('invoice_line_items', [])
                    if line_items:
                        amount = sum(float(item.get('payable_amount') or item.get('revenue') or 0) for item in line_items)
                
                if amount > 0:
                    # Update the invoice
                    supabase_client.table('sales_2025').update({
                        'total_amount': amount
                    }).eq('id', inv['id']).execute()
                    fixed_count += 1
                else:
                    errors.append(f"Invoice {inv.get('invoice_id')}: could not calculate amount")
                    
            except Exception as e:
                errors.append(f"Invoice {inv.get('invoice_id')}: {str(e)}")
        
        return jsonify({
            'success': True,
            'total_null': len(null_invoices.data),
            'fixed': fixed_count,
            'errors': errors[:10] if errors else []
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/diagnose-sync', methods=['GET'])
def api_diagnose_sync():
    """Diagnose why invoice counts/amounts don't match between DUANO and database"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        results = {'success': True}
        
        # 1. Get DUANO invoice count for 2025
        headers = {
            'Authorization': f"Bearer {session['access_token']}",
            'Content-Type': 'application/json'
        }
        
        # Get just page 1 to see total count
        params = {'per_page': 1, 'page': 1, 'filter_by_start_date': '2025-01-01', 'filter_by_end_date': '2025-12-31'}
        resp = requests.get(f"{DOUANO_CONFIG['base_url']}/api/public/v1/trade/sales-invoices", 
                           headers=headers, params=params, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            result_data = data.get('result', {})
            results['duano_total_invoices'] = result_data.get('total', 'unknown')
            results['duano_last_page'] = result_data.get('last_page', 'unknown')
            results['duano_per_page'] = result_data.get('per_page', 'unknown')
        else:
            results['duano_error'] = f'API returned {resp.status_code}'
        
        # 2. Get database invoice count for 2025
        db_count = supabase_client.table('sales_2025').select('id', count='exact').execute()
        results['database_invoice_count'] = db_count.count if hasattr(db_count, 'count') else len(db_count.data)
        
        # 3. Get database total amount
        db_amounts = supabase_client.table('sales_2025').select('total_amount').limit(5000).execute()
        if db_amounts.data:
            results['database_total_amount'] = round(sum(float(r.get('total_amount') or 0) for r in db_amounts.data), 2)
        
        # 4. Check for NULLs or zeros
        null_check = supabase_client.table('sales_2025').select('id').is_('total_amount', 'null').execute()
        results['invoices_with_null_amount'] = len(null_check.data)
        
        zero_check = supabase_client.table('sales_2025').select('id').eq('total_amount', 0).execute()
        results['invoices_with_zero_amount'] = len(zero_check.data)
        
        # 5. Get date range in database
        oldest = supabase_client.table('sales_2025').select('invoice_date').order('invoice_date', desc=False).limit(1).execute()
        newest = supabase_client.table('sales_2025').select('invoice_date').order('invoice_date', desc=True).limit(1).execute()
        
        if oldest.data:
            results['database_oldest_invoice'] = oldest.data[0].get('invoice_date')
        if newest.data:
            results['database_newest_invoice'] = newest.data[0].get('invoice_date')
        
        # 6. Compare
        if 'duano_total_invoices' in results and 'database_invoice_count' in results:
            duano_count = results['duano_total_invoices']
            if isinstance(duano_count, int):
                results['missing_invoices'] = duano_count - results['database_invoice_count']
        
        return jsonify(results)
        
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500


@app.route('/api/test-duano-speed', methods=['GET'])
def api_test_duano_speed():
    """Test how fast DUANO API responds"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated', 'success': False}), 401
    
    try:
        import time
        start_time = time.time()
        
        # Make a small test request (just 1 invoice)
        params = {
            'per_page': 1,
            'page': 1
        }
        
        data, error = make_api_request('/api/public/v1/trade/sales-invoices', params=params)
        
        elapsed = time.time() - start_time
        
        if error:
            return jsonify({
                'success': False,
                'error': error,
                'elapsed_seconds': elapsed
            }), 500
        
        return jsonify({
            'success': True,
            'message': f'DUANO API responded in {elapsed:.2f} seconds',
            'elapsed_seconds': elapsed,
            'data_received': bool(data)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =====================================================
# AUTOMATION BUILDER ENDPOINTS
# =====================================================

@app.route('/automations')
def automations_page():
    """Task Automations Builder page"""
    return render_template('automations.html')


@app.route('/api/automations', methods=['GET'])
def api_get_automations():
    """List all automation rules for the current user"""
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500

        # Get all automations (can filter by created_by if auth is implemented)
        result = supabase_client.table('automation_rules').select(
            '*'
        ).order('created_at', desc=True).execute()

        return jsonify({
            'success': True,
            'automations': result.data or []
        })

    except Exception as e:
        print(f"Error fetching automations: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/automations', methods=['POST'])
def api_create_automation():
    """Create a new automation rule"""
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500

        data = request.get_json()

        automation_data = {
            'name': data.get('name', 'Untitled Automation'),
            'description': data.get('description', ''),
            'created_by': data.get('created_by', session.get('user_email', 'unknown')),
            'is_global': data.get('is_global', False),
            'is_enabled': data.get('is_enabled', False),
            'is_draft': data.get('is_draft', True),
            'trigger_type': data.get('trigger_type'),
            'trigger_config': data.get('trigger_config', {}),
            'conditions': data.get('conditions', []),
            'actions': data.get('actions', [])
        }

        result = supabase_client.table('automation_rules').insert(automation_data).execute()

        if result.data:
            return jsonify({
                'success': True,
                'automation': result.data[0]
            })
        else:
            return jsonify({'error': 'Failed to create automation'}), 500

    except Exception as e:
        print(f"Error creating automation: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/automations/<automation_id>', methods=['GET'])
def api_get_automation(automation_id):
    """Get a specific automation rule"""
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500

        result = supabase_client.table('automation_rules').select(
            '*'
        ).eq('id', automation_id).execute()

        if result.data:
            return jsonify({
                'success': True,
                'automation': result.data[0]
            })
        else:
            return jsonify({'error': 'Automation not found'}), 404

    except Exception as e:
        print(f"Error fetching automation: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/automations/<automation_id>', methods=['PATCH'])
def api_update_automation(automation_id):
    """Update an automation rule"""
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500

        data = request.get_json()

        # Only update provided fields
        update_data = {'updated_at': datetime.now().isoformat()}

        allowed_fields = ['name', 'description', 'is_global', 'is_enabled', 'is_draft',
                          'trigger_type', 'trigger_config', 'conditions', 'actions']

        for field in allowed_fields:
            if field in data:
                update_data[field] = data[field]

        result = supabase_client.table('automation_rules').update(
            update_data
        ).eq('id', automation_id).execute()

        if result.data:
            return jsonify({
                'success': True,
                'automation': result.data[0]
            })
        else:
            return jsonify({'error': 'Automation not found'}), 404

    except Exception as e:
        print(f"Error updating automation: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/automations/<automation_id>', methods=['DELETE'])
def api_delete_automation(automation_id):
    """Delete an automation rule"""
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500

        result = supabase_client.table('automation_rules').delete().eq(
            'id', automation_id
        ).execute()

        return jsonify({'success': True, 'message': 'Automation deleted'})

    except Exception as e:
        print(f"Error deleting automation: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/automations/<automation_id>/toggle', methods=['POST'])
def api_toggle_automation(automation_id):
    """Enable or disable an automation"""
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500

        # Get current state
        result = supabase_client.table('automation_rules').select(
            'is_enabled'
        ).eq('id', automation_id).execute()

        if not result.data:
            return jsonify({'error': 'Automation not found'}), 404

        current_enabled = result.data[0].get('is_enabled', False)
        new_enabled = not current_enabled

        # Update state
        update_result = supabase_client.table('automation_rules').update({
            'is_enabled': new_enabled,
            'is_draft': False if new_enabled else result.data[0].get('is_draft', True),
            'updated_at': datetime.now().isoformat()
        }).eq('id', automation_id).execute()

        if update_result.data:
            return jsonify({
                'success': True,
                'is_enabled': new_enabled,
                'automation': update_result.data[0]
            })
        else:
            return jsonify({'error': 'Failed to toggle automation'}), 500

    except Exception as e:
        print(f"Error toggling automation: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/automations/<automation_id>/test', methods=['POST'])
def api_test_automation(automation_id):
    """Test an automation with a sample prospect (dry run)"""
    try:
        if not automation_engine:
            return jsonify({'error': 'Automation engine not available'}), 500

        data = request.get_json() or {}
        sample_prospect_id = data.get('prospect_id')

        result = automation_engine.test_automation(automation_id, sample_prospect_id)

        return jsonify(result)

    except Exception as e:
        print(f"Error testing automation: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/automations/<automation_id>/executions', methods=['GET'])
def api_get_automation_executions(automation_id):
    """Get execution history for an automation"""
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500

        limit = request.args.get('limit', 50, type=int)

        result = supabase_client.table('automation_executions').select(
            '*'
        ).eq('automation_rule_id', automation_id).order(
            'executed_at', desc=True
        ).limit(limit).execute()

        return jsonify({
            'success': True,
            'executions': result.data or []
        })

    except Exception as e:
        print(f"Error fetching executions: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/automations/templates', methods=['GET'])
def api_get_automation_templates():
    """Get pre-built automation templates"""
    return jsonify({
        'success': True,
        'templates': AUTOMATION_TEMPLATES
    })


@app.route('/api/automations/stats', methods=['GET'])
def api_get_automation_stats():
    """Get automation statistics"""
    try:
        if not supabase_client:
            return jsonify({'error': 'Supabase not configured'}), 500

        # Count active automations
        active_result = supabase_client.table('automation_rules').select(
            'id', count='exact'
        ).eq('is_enabled', True).execute()

        # Count total automations
        total_result = supabase_client.table('automation_rules').select(
            'id', count='exact'
        ).execute()

        # Count executions today
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        today_executions = supabase_client.table('automation_executions').select(
            'id', count='exact'
        ).gte('executed_at', today).execute()

        # Count successful executions today
        successful_today = supabase_client.table('automation_executions').select(
            'id', count='exact'
        ).gte('executed_at', today).eq('status', 'success').execute()

        return jsonify({
            'success': True,
            'stats': {
                'total_automations': total_result.count or 0,
                'active_automations': active_result.count or 0,
                'executions_today': today_executions.count or 0,
                'successful_today': successful_today.count or 0
            }
        })

    except Exception as e:
        print(f"Error fetching automation stats: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/automations/process-queue', methods=['POST'])
def api_process_automation_queue():
    """Manually trigger processing of time-based automation queue"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        if not automation_engine:
            return jsonify({'error': 'Automation engine not available'}), 500

        result = automation_engine.process_time_based_queue()

        return jsonify({
            'success': True,
            'result': result
        })

    except Exception as e:
        print(f"Error processing automation queue: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/automations/scheduler-status', methods=['GET'])
def api_automation_scheduler_status():
    """Get the status of the background automation scheduler"""
    if not is_logged_in():
        return jsonify({'error': 'Not authenticated'}), 401

    return jsonify({
        'running': automation_scheduler_running,
        'engine_available': automation_engine is not None,
        'message': 'Time-based automations are processed automatically every 15 minutes' if automation_scheduler_running else 'Scheduler not running'
    })


@app.route('/api/automations/available-triggers', methods=['GET'])
def api_get_available_triggers():
    """Get list of available trigger types and their configurations"""
    triggers = [
        {
            'type': 'status_change',
            'label': 'Status Change',
            'description': 'When a prospect moves to a specific funnel stage',
            'icon': 'fas fa-exchange-alt',
            'config_fields': [
                {'name': 'from_status', 'type': 'select', 'label': 'From Status', 'required': False},
                {'name': 'to_status', 'type': 'select', 'label': 'To Status', 'required': True}
            ]
        },
        {
            'type': 'time_based',
            'label': 'Time-Based',
            'description': 'X days after an event (last contact, created, etc.)',
            'icon': 'fas fa-clock',
            'config_fields': [
                {'name': 'days_offset', 'type': 'number', 'label': 'Days', 'required': True, 'default': 7},
                {'name': 'event', 'type': 'select', 'label': 'After Event', 'required': True,
                 'options': ['created_at', 'last_contact_date', 'status_changed_at']},
                {'name': 'status_filter', 'type': 'multiselect', 'label': 'For Prospects With Status', 'required': False}
            ]
        },
        {
            'type': 'field_change',
            'label': 'Field Change',
            'description': 'When a specific field is updated',
            'icon': 'fas fa-edit',
            'config_fields': [
                {'name': 'field', 'type': 'select', 'label': 'Field', 'required': True,
                 'options': ['assigned_salesperson', 'region', 'priority_level', 'tags', 'notes']},
                {'name': 'change_type', 'type': 'select', 'label': 'Change Type', 'required': True,
                 'options': ['set', 'changed', 'cleared']}
            ]
        }
    ]

    return jsonify({'success': True, 'triggers': triggers})


@app.route('/api/automations/available-actions', methods=['GET'])
def api_get_available_actions():
    """Get list of available action types"""
    actions = [
        {
            'type': 'create_task',
            'label': 'Create Task',
            'description': 'Create a follow-up task',
            'icon': 'fas fa-tasks',
            'config_fields': [
                {'name': 'title_template', 'type': 'text', 'label': 'Task Title', 'required': True,
                 'placeholder': 'Follow up with {{prospect_name}}'},
                {'name': 'description_template', 'type': 'textarea', 'label': 'Description', 'required': False},
                {'name': 'task_type', 'type': 'select', 'label': 'Task Type', 'required': True,
                 'options': ['call', 'email', 'meeting', 'follow_up', 'demo', 'proposal', 'research']},
                {'name': 'priority', 'type': 'select', 'label': 'Priority', 'required': True,
                 'options': [1, 2, 3, 4, 5], 'default': 3},
                {'name': 'due_date_offset_days', 'type': 'number', 'label': 'Due In (days)', 'required': True, 'default': 1},
                {'name': 'assigned_to', 'type': 'text', 'label': 'Assign To', 'required': False,
                 'placeholder': '{{current_user}}'}
            ]
        },
        {
            'type': 'update_prospect_status',
            'label': 'Update Status',
            'description': 'Change the prospect status',
            'icon': 'fas fa-exchange-alt',
            'config_fields': [
                {'name': 'new_status', 'type': 'select', 'label': 'New Status', 'required': True}
            ]
        }
    ]

    return jsonify({'success': True, 'actions': actions})


@app.route('/api/automations/available-statuses', methods=['GET'])
def api_get_available_statuses():
    """Get list of available prospect statuses"""
    statuses = [
        {'value': 'new_lead', 'label': 'New Lead'},
        {'value': 'first_contact', 'label': 'First Contact'},
        {'value': 'meeting_planned', 'label': 'Meeting Planned'},
        {'value': 'follow_up', 'label': 'Follow Up'},
        {'value': 'customer', 'label': 'Customer'},
        {'value': 'contact_later', 'label': 'Contact Later'},
        {'value': 'ex_customer', 'label': 'Ex Customer'},
        {'value': 'unqualified', 'label': 'Unqualified'}
    ]

    return jsonify({'success': True, 'statuses': statuses})


# =====================================================
# GLOBAL ERROR HANDLERS
# =====================================================

@app.errorhandler(500)
def handle_500_error(e):
    """Handle 500 errors and return JSON instead of HTML"""
    print(f"500 Error: {e}")
    import traceback
    traceback.print_exc()
    return jsonify({
        'error': 'Internal Server Error',
        'message': str(e),
        'success': False
    }), 500

@app.errorhandler(Exception)
def handle_exception(e):
    """Handle all unhandled exceptions and return JSON for API routes"""
    print(f"Unhandled exception: {e}")
    import traceback
    traceback.print_exc()
    
    # Check if this is an API request
    if request.path.startswith('/api/'):
        return jsonify({
            'error': 'An unexpected error occurred',
            'message': str(e),
            'success': False
        }), 500
    
    # For non-API routes, re-raise to use default error handling
    raise e


# ============================================================================
# CSV IMPORT ANALYSIS ENDPOINT
# ============================================================================

@app.route('/api/analyze-csv-import', methods=['GET'])
def analyze_csv_import():
    """Analyze the CRM CSV import file and find matches with existing companies."""
    # No auth required - one-time analysis tool

    try:
        import csv
        import re
        from collections import defaultdict

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

        def normalize_postal_code(address):
            """Extract postal code from address."""
            if not address:
                return ""
            match = re.search(r'\b(\d{4})\b', address)
            return match.group(1) if match else ""

        # Load CSV data
        csv_path = os.path.join(os.path.dirname(__file__), '2026-01-20_location_export.csv')
        csv_records = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                csv_records.append(row)

        # Load existing companies from database
        all_companies = []
        batch_size = 1000
        offset = 0

        while True:
            result = supabase_client.table('companies').select(
                'id, company_id, name, public_name, vat_number, post_code, city'
            ).range(offset, offset + batch_size - 1).execute()

            if not result.data:
                break
            all_companies.extend(result.data)
            if len(result.data) < batch_size:
                break
            offset += batch_size

        # Build lookup indexes
        db_names_index = defaultdict(list)
        db_postal_index = defaultdict(list)

        for company in all_companies:
            norm_name = normalize_name(company.get('name') or company.get('public_name'))
            if norm_name:
                db_names_index[norm_name].append(company)

            norm_public = normalize_name(company.get('public_name'))
            if norm_public and norm_public != norm_name:
                db_names_index[norm_public].append(company)

            postal = company.get('post_code')
            if postal:
                db_postal_index[str(postal)].append(company)

        # Find matches
        exact_matches = []
        fuzzy_matches = []
        no_matches = []

        for csv_record in csv_records:
            csv_name = csv_record.get('Name', '')
            csv_address = csv_record.get('Address', '')
            csv_postal = normalize_postal_code(csv_address)
            norm_csv_name = normalize_name(csv_name)

            match_found = False

            # Try exact name match
            if norm_csv_name in db_names_index:
                matches = db_names_index[norm_csv_name]
                if csv_postal:
                    postal_filtered = [m for m in matches if str(m.get('post_code', '')) == csv_postal]
                    if postal_filtered:
                        matches = postal_filtered

                if matches:
                    exact_matches.append({
                        'csv_name': csv_name,
                        'csv_address': csv_address,
                        'csv_status': csv_record.get('Lead Status', ''),
                        'db_name': matches[0].get('name') or matches[0].get('public_name'),
                        'db_id': matches[0].get('company_id') or matches[0].get('id')
                    })
                    match_found = True

            # Try fuzzy matching
            if not match_found and csv_postal and csv_postal in db_postal_index:
                for db_record in db_postal_index[csv_postal]:
                    db_name = normalize_name(db_record.get('name') or db_record.get('public_name', ''))
                    if db_name and norm_csv_name:
                        if db_name in norm_csv_name or norm_csv_name in db_name:
                            fuzzy_matches.append({
                                'csv_name': csv_name,
                                'csv_address': csv_address,
                                'csv_status': csv_record.get('Lead Status', ''),
                                'db_name': db_record.get('name') or db_record.get('public_name'),
                                'db_id': db_record.get('company_id') or db_record.get('id')
                            })
                            match_found = True
                            break

            if not match_found:
                no_matches.append({
                    'name': csv_name,
                    'address': csv_address,
                    'status': csv_record.get('Lead Status', ''),
                    'channel': csv_record.get('Channel', ''),
                    'owner': csv_record.get('Company Owner', ''),
                    'priority': csv_record.get('Priority', ''),
                    'sub_type': csv_record.get('Sub Type', '')
                })

        # Status distribution for new records
        status_counts = defaultdict(int)
        for record in no_matches:
            status = record.get('status', 'Unknown') or 'Unknown'
            status_counts[status] += 1

        return jsonify({
            'success': True,
            'summary': {
                'total_csv_records': len(csv_records),
                'total_db_companies': len(all_companies),
                'exact_matches': len(exact_matches),
                'fuzzy_matches': len(fuzzy_matches),
                'new_records': len(no_matches),
                'exact_match_pct': round(len(exact_matches) / len(csv_records) * 100, 1),
                'new_records_pct': round(len(no_matches) / len(csv_records) * 100, 1)
            },
            'new_records_by_status': dict(status_counts),
            'exact_matches_sample': exact_matches[:20],
            'fuzzy_matches_sample': fuzzy_matches[:20],
            'new_records_sample': no_matches[:30],
            'all_exact_matches': exact_matches,
            'all_fuzzy_matches': fuzzy_matches,
            'all_new_records': no_matches
        })

    except Exception as e:
        print(f"Error analyzing CSV import: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================================================
# CSV IMPORT ENDPOINT - Import CRM data into companies table
# ============================================================================

@app.route('/api/import-crm-data', methods=['POST'])
def import_crm_data():
    """Import CRM CSV data into the companies table.

    - Updates existing companies with CRM data (contacts, notes, etc.)
    - Inserts new companies (including Unqualified and Ex-customer)
    """
    # No auth required - one-time import tool

    try:
        import csv
        import re
        from collections import defaultdict
        import time as time_module

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

        def normalize_postal_code(address):
            """Extract postal code from address."""
            if not address:
                return ""
            match = re.search(r'\b(\d{4})\b', address)
            return match.group(1) if match else ""

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

        # Load CSV data
        csv_path = os.path.join(os.path.dirname(__file__), '2026-01-20_location_export.csv')
        csv_records = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                csv_records.append(row)

        # Load existing companies
        all_companies = []
        batch_size = 1000
        offset = 0

        while True:
            result = supabase_client.table('companies').select('*').range(offset, offset + batch_size - 1).execute()
            if not result.data:
                break
            all_companies.extend(result.data)
            if len(result.data) < batch_size:
                break
            offset += batch_size

        # Build lookup indexes
        db_names_index = defaultdict(list)

        for company in all_companies:
            norm_name = normalize_name(company.get('name') or company.get('public_name'))
            if norm_name:
                db_names_index[norm_name].append(company)
            norm_public = normalize_name(company.get('public_name'))
            if norm_public and norm_public != norm_name:
                db_names_index[norm_public].append(company)

        # Find matches
        exact_matches = []
        no_matches = []

        for csv_record in csv_records:
            csv_name = csv_record.get('Name', '')
            csv_address = csv_record.get('Address', '')
            csv_postal = normalize_postal_code(csv_address)
            norm_csv_name = normalize_name(csv_name)

            match_found = False

            if norm_csv_name in db_names_index:
                matches = db_names_index[norm_csv_name]
                if csv_postal:
                    postal_filtered = [m for m in matches if str(m.get('post_code', '')) == csv_postal]
                    if postal_filtered:
                        matches = postal_filtered
                if matches:
                    exact_matches.append({'csv_record': csv_record, 'db_record': matches[0]})
                    match_found = True

            if not match_found:
                no_matches.append(csv_record)

        # Perform import
        update_success = 0
        update_errors = []
        insert_success = 0
        insert_errors = []

        # Update existing companies
        for match in exact_matches:
            csv_record = match['csv_record']
            db_record = match['db_record']
            company_id = db_record.get('company_id') or db_record.get('id')

            csv_data = build_company_record_from_csv(csv_record, is_new=False)
            update_data = {}

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
            for field in ['contact_person_name', 'contact_person_email', 'contact_person_phone', 'assigned_salesperson']:
                if csv_data.get(field) and not db_record.get(field):
                    update_data[field] = csv_data[field]

            # Update coordinates only if missing
            if not db_record.get('latitude') and csv_data.get('latitude'):
                update_data['latitude'] = csv_data['latitude']
                update_data['longitude'] = csv_data.get('longitude')

            # Update address only if missing
            for field in ['address_line1', 'city', 'post_code']:
                if csv_data.get(field) and not db_record.get(field):
                    update_data[field] = csv_data[field]

            # Update suppliers
            if csv_data.get('suppliers'):
                existing_suppliers = db_record.get('suppliers', []) or []
                new_suppliers = csv_data['suppliers']
                combined = list(set(existing_suppliers + new_suppliers))
                if combined:
                    update_data['suppliers'] = combined

            # Mark as imported
            update_data['imported_from_crm'] = True
            update_data['crm_import_date'] = datetime.now().isoformat()

            existing_sources = db_record.get('data_sources', []) or []
            if 'crm_import' not in existing_sources:
                update_data['data_sources'] = existing_sources + ['crm_import']

            if update_data:
                try:
                    supabase_client.table('companies').update(update_data).eq('company_id', company_id).execute()
                    update_success += 1
                except Exception as e:
                    update_errors.append({'name': csv_record.get('Name', ''), 'error': str(e)})

        # Insert new companies
        for i, csv_record in enumerate(no_matches):
            record = build_company_record_from_csv(csv_record, is_new=True)
            # Generate unique negative company_id
            record['company_id'] = -int(time_module.time() * 1000 + i) % 1000000000

            try:
                supabase_client.table('companies').insert(record).execute()
                insert_success += 1
            except Exception as e:
                insert_errors.append({'name': csv_record.get('Name', ''), 'error': str(e)})

            # Rate limiting
            if (i + 1) % 50 == 0:
                time_module.sleep(0.3)

        return jsonify({
            'success': True,
            'summary': {
                'total_csv_records': len(csv_records),
                'existing_to_update': len(exact_matches),
                'new_to_insert': len(no_matches),
                'updates_successful': update_success,
                'updates_failed': len(update_errors),
                'inserts_successful': insert_success,
                'inserts_failed': len(insert_errors)
            },
            'update_errors': update_errors[:20],
            'insert_errors': insert_errors[:20]
        })

    except Exception as e:
        print(f"Error importing CRM data: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================================================
# CRM IMPORT & MERGE INTERFACE
# ============================================================================

@app.route('/crm-merge')
def crm_merge_page():
    """Page for reviewing and merging CRM imports."""
    if not is_logged_in():
        return redirect(url_for('login'))
    return render_template('crm_merge.html')


@app.route('/api/crm-import-safe', methods=['POST'])
def crm_import_safe():
    """
    Safe CRM import - imports ALL records as pending review.
    No auto-matching, no updates to existing companies.
    Accepts CSV file upload.
    """
    try:
        import csv
        import re
        import time as time_module
        import io

        # Check for file upload
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded. Please select a CSV file.'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not file.filename.endswith('.csv'):
            return jsonify({'error': 'Please upload a CSV file'}), 400

        def parse_address(address):
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
            if not coord_string or ',' not in coord_string:
                return None, None
            try:
                parts = coord_string.split(',')
                return float(parts[0].strip()), float(parts[1].strip())
            except:
                return None, None

        def parse_list(s):
            if not s or not s.strip():
                return []
            return [p.strip() for p in s.split(',') if p.strip()]

        # Read CSV from uploaded file
        csv_records = []
        stream = io.StringIO(file.stream.read().decode('utf-8'))
        reader = csv.DictReader(stream, delimiter=';')
        for row in reader:
            csv_records.append(row)

        # Import each record as a new pending company
        imported = 0
        errors = []

        for i, csv_record in enumerate(csv_records):
            address_parts = parse_address(csv_record.get('Address', ''))
            lat, lng = parse_coordinates(csv_record.get('Coordinates', ''))

            # Store all CRM data in a JSON field for reference
            crm_source = {
                'original_name': csv_record.get('Name', ''),
                'original_address': csv_record.get('Address', ''),
                'account_number': csv_record.get('Account Number', ''),
                'lead_status': csv_record.get('Lead Status', ''),
                'channel': csv_record.get('Channel', ''),
                'priority': csv_record.get('Priority', ''),
                'language': csv_record.get('Language', ''),
                'province': csv_record.get('Province / Region', ''),
                'sub_type': csv_record.get('Sub Type', ''),
                'business_type': csv_record.get('Type (Yugen Website)', ''),
                'company_owner': csv_record.get('Company Owner', ''),
                'parent_company': csv_record.get('Parent Company', ''),
                'suppliers': csv_record.get('Suppliers', ''),
                'notes': csv_record.get('Notes', ''),
                'activations': csv_record.get('Activations', ''),
                'products_proposed': csv_record.get('Proposed', ''),
                'products_sampled': csv_record.get('Sampled', ''),
                'products_listed': csv_record.get('Listed', ''),
                'products_won': csv_record.get('Win', ''),
                'contact_1_name': csv_record.get('Contact 1 Name', ''),
                'contact_1_role': csv_record.get('Contact 1 Role', ''),
                'contact_1_email': csv_record.get('Contact 1 Email', ''),
                'contact_1_phone': csv_record.get('Contact 1 Phone', ''),
                'contact_2_name': csv_record.get('Contact 2 Name', ''),
                'contact_2_role': csv_record.get('Contact 2 Role', ''),
                'contact_2_email': csv_record.get('Contact 2 Email', ''),
                'contact_2_phone': csv_record.get('Contact 2 Phone', ''),
                'contact_3_name': csv_record.get('Contact 3 Name', ''),
                'contact_3_role': csv_record.get('Contact 3 Role', ''),
                'contact_3_email': csv_record.get('Contact 3 Email', ''),
                'contact_3_phone': csv_record.get('Contact 3 Phone', ''),
            }

            # Generate unique negative company_id for CRM imports using timestamp + index
            import_timestamp = int(time_module.time())
            unique_id = -(import_timestamp * 10000 + i)

            record = {
                'company_id': unique_id,
                'name': csv_record.get('Name', ''),
                'public_name': csv_record.get('Name', ''),
                'address_line1': address_parts.get('address_line1', ''),
                'city': address_parts.get('city', ''),
                'post_code': address_parts.get('post_code', ''),
                'country_name': address_parts.get('country_name', '') or 'Belgium',
                'latitude': lat,
                'longitude': lng,
                'lead_status': csv_record.get('Lead Status', '') or None,
                'channel': csv_record.get('Channel', '') or None,
                'language': csv_record.get('Language', '') or None,
                'priority': csv_record.get('Priority', '') or None,
                'province': csv_record.get('Province / Region', '') or None,
                'sub_type': csv_record.get('Sub Type', '') or None,
                'assigned_salesperson': csv_record.get('Company Owner', '') or None,
                'crm_notes': csv_record.get('Notes', '') or None,
                'contact_person_name': csv_record.get('Contact 1 Name', '') or None,
                'contact_person_email': csv_record.get('Contact 1 Email', '') or None,
                'contact_person_phone': csv_record.get('Contact 1 Phone', '') or None,
                'crm_review_status': 'pending',
                'crm_source_data': crm_source,
                'imported_from_crm': True,
                'crm_import_date': datetime.now().isoformat()
            }

            # Remove None/empty values
            record = {k: v for k, v in record.items() if v is not None and v != ''}
            record['crm_review_status'] = 'pending'  # Always set this

            try:
                supabase_client.table('companies').insert(record).execute()
                imported += 1
            except Exception as e:
                errors.append({'name': csv_record.get('Name', ''), 'error': str(e)})

            if (i + 1) % 100 == 0:
                time_module.sleep(0.2)

        return jsonify({
            'success': True,
            'imported': imported,
            'total': len(csv_records),
            'errors': len(errors),
            'error_samples': errors[:10]
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/crm-pending', methods=['GET'])
def get_crm_pending():
    """Get all CRM imports pending review."""
    try:
        result = supabase_client.table('companies').select(
            'id, company_id, name, public_name, address_line1, city, post_code, '
            'lead_status, channel, priority, crm_notes, crm_source_data, latitude, longitude'
        ).eq('crm_review_status', 'pending').order('name').execute()

        return jsonify({
            'success': True,
            'pending': result.data if result.data else [],
            'count': len(result.data) if result.data else 0
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/crm-search-existing', methods=['GET'])
def crm_search_existing():
    """Search existing companies (non-CRM) for merge candidates."""
    try:
        query = request.args.get('q', '').strip()
        if not query or len(query) < 2:
            return jsonify({'results': []})

        select_fields = (
            'id, company_id, name, public_name, address_line1, city, post_code, '
            'email, phone_number, total_revenue_2024, total_revenue_2025, invoice_count_2024, invoice_count_2025'
        )

        # Search by name (case-insensitive)
        result = supabase_client.table('companies').select(select_fields).is_('crm_review_status', 'null').ilike('name', f'%{query}%').limit(20).execute()

        # Also search by public_name
        result2 = supabase_client.table('companies').select(select_fields).is_('crm_review_status', 'null').ilike('public_name', f'%{query}%').limit(20).execute()

        # Search by address
        result3 = supabase_client.table('companies').select(select_fields).is_('crm_review_status', 'null').ilike('address_line1', f'%{query}%').limit(20).execute()

        # Search by city
        result4 = supabase_client.table('companies').select(select_fields).is_('crm_review_status', 'null').ilike('city', f'%{query}%').limit(20).execute()

        # Combine and dedupe
        seen_ids = set()
        combined = []
        for c in (result.data or []) + (result2.data or []) + (result3.data or []) + (result4.data or []):
            if c['company_id'] not in seen_ids:
                seen_ids.add(c['company_id'])
                combined.append(c)

        return jsonify({'results': combined[:20]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/crm-merge', methods=['POST'])
def crm_merge_companies():
    """Merge a CRM import into an existing company."""
    try:
        data = request.get_json()
        crm_company_id = data.get('crm_company_id')  # The pending CRM import (negative ID)
        target_company_id = data.get('target_company_id')  # The existing company to merge into

        if not crm_company_id or not target_company_id:
            return jsonify({'error': 'Missing crm_company_id or target_company_id'}), 400

        # Get the CRM import data
        crm_result = supabase_client.table('companies').select('*').eq('company_id', crm_company_id).single().execute()
        if not crm_result.data:
            return jsonify({'error': 'CRM import not found'}), 404

        crm_data = crm_result.data
        crm_source = crm_data.get('crm_source_data', {})

        # Get the target company
        target_result = supabase_client.table('companies').select('*').eq('company_id', target_company_id).single().execute()
        if not target_result.data:
            return jsonify({'error': 'Target company not found'}), 404

        target_data = target_result.data

        # Build update for target company - only add CRM data, don't overwrite existing
        update_fields = {}

        # CRM fields to merge (only if target doesn't have them)
        crm_fields_map = {
            'lead_status': crm_data.get('lead_status'),
            'channel': crm_data.get('channel'),
            'language': crm_data.get('language'),
            'priority': crm_data.get('priority'),
            'province': crm_data.get('province'),
            'sub_type': crm_data.get('sub_type'),
            'business_type': crm_source.get('business_type'),
            'parent_company': crm_source.get('parent_company'),
            'crm_notes': crm_source.get('notes'),
            'activations': crm_source.get('activations'),
            'external_account_number': crm_source.get('account_number'),
        }

        for field, value in crm_fields_map.items():
            if value and not target_data.get(field):
                update_fields[field] = value

        # Products (parse and add as arrays)
        if crm_source.get('products_proposed'):
            update_fields['products_proposed'] = [p.strip() for p in crm_source['products_proposed'].split(',') if p.strip()]
        if crm_source.get('products_sampled'):
            update_fields['products_sampled'] = [p.strip() for p in crm_source['products_sampled'].split(',') if p.strip()]
        if crm_source.get('products_listed'):
            update_fields['products_listed'] = [p.strip() for p in crm_source['products_listed'].split(',') if p.strip()]
        if crm_source.get('products_won'):
            update_fields['products_won'] = [p.strip() for p in crm_source['products_won'].split(',') if p.strip()]

        # Suppliers
        if crm_source.get('suppliers'):
            update_fields['suppliers'] = [s.strip() for s in crm_source['suppliers'].split(',') if s.strip()]

        # Contact info (only if target doesn't have it)
        if crm_source.get('contact_1_name') and not target_data.get('contact_person_name'):
            update_fields['contact_person_name'] = crm_source['contact_1_name']
        if crm_source.get('contact_1_role'):
            update_fields['contact_person_role'] = crm_source['contact_1_role']
        if crm_source.get('contact_1_email') and not target_data.get('contact_person_email'):
            update_fields['contact_person_email'] = crm_source['contact_1_email']
        if crm_source.get('contact_1_phone') and not target_data.get('contact_person_phone'):
            update_fields['contact_person_phone'] = crm_source['contact_1_phone']

        # Additional contacts
        if crm_source.get('contact_2_name'):
            update_fields['contact_2_name'] = crm_source['contact_2_name']
            update_fields['contact_2_role'] = crm_source.get('contact_2_role')
            update_fields['contact_2_email'] = crm_source.get('contact_2_email')
            update_fields['contact_2_phone'] = crm_source.get('contact_2_phone')
        if crm_source.get('contact_3_name'):
            update_fields['contact_3_name'] = crm_source['contact_3_name']
            update_fields['contact_3_role'] = crm_source.get('contact_3_role')
            update_fields['contact_3_email'] = crm_source.get('contact_3_email')
            update_fields['contact_3_phone'] = crm_source.get('contact_3_phone')

        # Coordinates (only if target doesn't have them)
        if crm_data.get('latitude') and not target_data.get('latitude'):
            update_fields['latitude'] = crm_data['latitude']
            update_fields['longitude'] = crm_data.get('longitude')

        # Assigned salesperson (only if target doesn't have one)
        if crm_source.get('company_owner') and not target_data.get('assigned_salesperson'):
            update_fields['assigned_salesperson'] = crm_source['company_owner']

        # Mark as having CRM data
        update_fields['imported_from_crm'] = True
        update_fields['crm_import_date'] = datetime.now().isoformat()
        update_fields['crm_source_data'] = crm_source  # Keep original CRM data for reference

        # Update the target company
        if update_fields:
            supabase_client.table('companies').update(update_fields).eq('company_id', target_company_id).execute()

        # Mark the CRM import as merged and record which company it merged into
        supabase_client.table('companies').update({
            'crm_review_status': 'merged',
            'merged_into_company_id': target_company_id
        }).eq('company_id', crm_company_id).execute()

        return jsonify({
            'success': True,
            'message': f'Merged CRM data into {target_data.get("name")}',
            'fields_updated': list(update_fields.keys())
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/crm-keep-standalone', methods=['POST'])
def crm_keep_standalone():
    """Mark a CRM import as a standalone new company (no merge needed)."""
    try:
        data = request.get_json()
        crm_company_id = data.get('crm_company_id')

        if not crm_company_id:
            return jsonify({'error': 'Missing crm_company_id'}), 400

        # Update status to standalone
        supabase_client.table('companies').update({
            'crm_review_status': 'standalone'
        }).eq('company_id', crm_company_id).execute()

        return jsonify({'success': True, 'message': 'Marked as standalone company'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/crm-delete-pending', methods=['POST'])
def crm_delete_pending():
    """Delete a pending CRM import (skip it)."""
    try:
        data = request.get_json()
        crm_company_id = data.get('crm_company_id')

        if not crm_company_id:
            return jsonify({'error': 'Missing crm_company_id'}), 400

        supabase_client.table('companies').delete().eq('company_id', crm_company_id).execute()

        return jsonify({'success': True, 'message': 'Deleted CRM import'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/crm-stats', methods=['GET'])
def crm_stats():
    """Get CRM import statistics."""
    try:
        pending = supabase_client.table('companies').select('id', count='exact').eq('crm_review_status', 'pending').execute()
        merged = supabase_client.table('companies').select('id', count='exact').eq('crm_review_status', 'merged').execute()
        standalone = supabase_client.table('companies').select('id', count='exact').eq('crm_review_status', 'standalone').execute()

        return jsonify({
            'pending': pending.count or 0,
            'merged': merged.count or 0,
            'standalone': standalone.count or 0,
            'total_reviewed': (merged.count or 0) + (standalone.count or 0)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/check-db-state', methods=['GET'])
def check_db_state():
    """Check the current database state - companies with/without invoices."""
    try:
        # Get company IDs from invoices
        invoice_company_ids = set()
        for year in ['2024', '2025', '2026']:
            try:
                offset = 0
                while True:
                    result = supabase_client.table(f'sales_{year}').select('company_id').range(offset, offset + 999).execute()
                    if not result.data:
                        break
                    for r in result.data:
                        if r.get('company_id'):
                            invoice_company_ids.add(r['company_id'])
                    if len(result.data) < 1000:
                        break
                    offset += 1000
            except:
                pass

        # Get all companies
        all_companies = []
        offset = 0
        while True:
            result = supabase_client.table('companies').select('company_id, name, imported_from_crm').range(offset, offset + 999).execute()
            if not result.data:
                break
            all_companies.extend(result.data)
            if len(result.data) < 1000:
                break
            offset += 1000

        companies_with_invoices = [c for c in all_companies if c['company_id'] in invoice_company_ids]
        companies_without_invoices = [c for c in all_companies if c['company_id'] not in invoice_company_ids]
        crm_imported = [c for c in all_companies if c.get('imported_from_crm')]

        return jsonify({
            'total_companies': len(all_companies),
            'companies_with_invoices': len(companies_with_invoices),
            'companies_without_invoices': len(companies_without_invoices),
            'crm_imported_remaining': len(crm_imported),
            'sample_without_invoices': [{'name': c['name'], 'id': c['company_id']} for c in companies_without_invoices[:30]]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/delete-companies-without-invoices', methods=['POST'])
def delete_companies_without_invoices():
    """Delete all companies that have no invoices (CRM-only imports)."""
    try:
        # Get company IDs from invoices
        invoice_company_ids = set()
        for year in ['2024', '2025', '2026']:
            try:
                offset = 0
                while True:
                    result = supabase_client.table(f'sales_{year}').select('company_id').range(offset, offset + 999).execute()
                    if not result.data:
                        break
                    for r in result.data:
                        if r.get('company_id'):
                            invoice_company_ids.add(r['company_id'])
                    if len(result.data) < 1000:
                        break
                    offset += 1000
            except:
                pass

        # Get all companies
        all_companies = []
        offset = 0
        while True:
            result = supabase_client.table('companies').select('id, company_id, name').range(offset, offset + 999).execute()
            if not result.data:
                break
            all_companies.extend(result.data)
            if len(result.data) < 1000:
                break
            offset += 1000

        # Find companies without invoices
        companies_to_delete = [c for c in all_companies if c['company_id'] not in invoice_company_ids]

        # Delete them
        deleted = 0
        for c in companies_to_delete:
            try:
                supabase_client.table('companies').delete().eq('id', c['id']).execute()
                deleted += 1
            except:
                pass

        return jsonify({
            'success': True,
            'deleted': deleted,
            'total_without_invoices': len(companies_to_delete)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/rollback-crm-import', methods=['POST'])
def rollback_crm_import():
    """Rollback the bad CRM import - delete new companies and clear CRM fields from existing."""
    try:
        # Find all companies marked as CRM imported
        result = supabase_client.table('companies').select('id, company_id, name, imported_from_crm').eq('imported_from_crm', True).execute()
        affected = result.data if result.data else []

        # Separate into new inserts (negative IDs) vs updated existing (positive IDs)
        new_inserts = [c for c in affected if c['company_id'] < 0]
        updated_existing = [c for c in affected if c['company_id'] > 0]

        # Delete newly inserted companies
        delete_count = 0
        for company in new_inserts:
            try:
                supabase_client.table('companies').delete().eq('id', company['id']).execute()
                delete_count += 1
            except:
                pass

        # Clear CRM fields from existing companies
        clear_fields = {
            'lead_status': None, 'channel': None, 'language': None, 'priority': None,
            'province': None, 'sub_type': None, 'business_type': None, 'parent_company': None,
            'suppliers': None, 'crm_notes': None, 'activations': None, 'external_account_number': None,
            'products_proposed': None, 'products_sampled': None, 'products_listed': None, 'products_won': None,
            'contact_person_role': None, 'contact_2_name': None, 'contact_2_role': None,
            'contact_2_email': None, 'contact_2_phone': None, 'contact_3_name': None,
            'contact_3_role': None, 'contact_3_email': None, 'contact_3_phone': None,
            'imported_from_crm': False, 'crm_import_date': None
        }

        clear_count = 0
        for company in updated_existing:
            try:
                supabase_client.table('companies').update(clear_fields).eq('company_id', company['company_id']).execute()
                clear_count += 1
            except:
                pass

        return jsonify({
            'success': True,
            'deleted_new_companies': delete_count,
            'cleared_existing_companies': clear_count,
            'total_affected': len(affected)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/retry-failed-imports', methods=['POST'])
def retry_failed_imports():
    """Retry the 22 failed CRM imports after fixing language column."""
    try:
        import csv
        import re
        from collections import defaultdict
        import time as time_module

        FAILED_NAMES = [
            "Barket l Comptoir gourmand take-away", "BelMundo", "Café Walvis", "Caleo Café",
            "Claw", "Colruyt", "DoubleTree by Hilton Brussels City", "GIMIC Radio", "Goyo",
            "Green House", "Iyagi Korean Takeaway", "JeanBon Louise", "Life Bar", "Liu Lin",
            "Lucifer Lives", "Muski Comics Café", "Nomade Coffee Brussels", "Renard Bakery",
            "Terter", "The WAYNE Café", "ToiToiToi Coffee x Culture / Antwerpen", "Van de Velde Stadscafe"
        ]

        def normalize_name(name):
            if not name:
                return ""
            name = name.lower().strip()
            for suffix in [' bv', ' bvba', ' nv', ' sprl', ' sa', ' cvba', ' vzw', ' asbl']:
                name = name.replace(suffix, '')
            name = re.sub(r'[^a-z0-9\s]', '', name)
            name = re.sub(r'\s+', ' ', name).strip()
            return name

        def parse_address(address):
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
            if not coord_string or ',' not in coord_string:
                return None, None
            try:
                parts = coord_string.split(',')
                return float(parts[0].strip()), float(parts[1].strip())
            except (ValueError, IndexError):
                return None, None

        def parse_products(s):
            if not s or not s.strip():
                return []
            return [p.strip() for p in s.split(',') if p.strip()]

        def build_record(csv_record, is_new=True):
            address_parts = parse_address(csv_record.get('Address', ''))
            lat, lng = parse_coordinates(csv_record.get('Coordinates', ''))
            record = {
                'name': csv_record.get('Name', ''),
                'public_name': csv_record.get('Name', ''),
                'address_line1': address_parts.get('address_line1', ''),
                'city': address_parts.get('city', ''),
                'post_code': address_parts.get('post_code', ''),
                'country_name': address_parts.get('country_name', 'Belgium'),
                'latitude': lat, 'longitude': lng,
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
                'suppliers': parse_products(csv_record.get('Suppliers', '')),
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
                record['is_customer'] = csv_record.get('Lead Status', '') == 'Customer'
                record['is_supplier'] = False
            return {k: v for k, v in record.items() if v is not None and v != ''}

        # Load CSV
        csv_path = os.path.join(os.path.dirname(__file__), '2026-01-20_location_export.csv')
        csv_records = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                csv_records.append(row)

        failed_records = [r for r in csv_records if r.get('Name', '') in FAILED_NAMES]

        # Load existing companies
        all_companies = []
        offset = 0
        while True:
            result = supabase_client.table('companies').select('*').range(offset, offset + 999).execute()
            if not result.data:
                break
            all_companies.extend(result.data)
            if len(result.data) < 1000:
                break
            offset += 1000

        db_names_index = defaultdict(list)
        for company in all_companies:
            norm_name = normalize_name(company.get('name') or company.get('public_name'))
            if norm_name:
                db_names_index[norm_name].append(company)

        success_count = 0
        errors = []

        for csv_record in failed_records:
            name = csv_record.get('Name', '')
            norm_name = normalize_name(name)
            existing = db_names_index.get(norm_name, [])

            if existing:
                db_record = existing[0]
                company_id = db_record.get('company_id') or db_record.get('id')
                csv_data = build_record(csv_record, is_new=False)
                update_data = {}
                crm_fields = ['external_account_number', 'channel', 'language', 'lead_status', 'priority',
                              'province', 'sub_type', 'business_type', 'parent_company', 'crm_notes', 'activations',
                              'products_proposed', 'products_sampled', 'products_listed', 'products_won',
                              'contact_person_role', 'contact_2_name', 'contact_2_role', 'contact_2_email',
                              'contact_2_phone', 'contact_3_name', 'contact_3_role', 'contact_3_email', 'contact_3_phone']
                for field in crm_fields:
                    if field in csv_data and csv_data[field]:
                        update_data[field] = csv_data[field]
                for field in ['contact_person_name', 'contact_person_email', 'contact_person_phone', 'assigned_salesperson']:
                    if csv_data.get(field) and not db_record.get(field):
                        update_data[field] = csv_data[field]
                if not db_record.get('latitude') and csv_data.get('latitude'):
                    update_data['latitude'] = csv_data['latitude']
                    update_data['longitude'] = csv_data.get('longitude')
                update_data['imported_from_crm'] = True
                update_data['crm_import_date'] = datetime.now().isoformat()
                try:
                    supabase_client.table('companies').update(update_data).eq('company_id', company_id).execute()
                    success_count += 1
                except Exception as e:
                    errors.append({'name': name, 'error': str(e)})
            else:
                record = build_record(csv_record, is_new=True)
                record['company_id'] = -int(time_module.time() * 1000) % 1000000000
                try:
                    supabase_client.table('companies').insert(record).execute()
                    success_count += 1
                except Exception as e:
                    errors.append({'name': name, 'error': str(e)})
            time_module.sleep(0.1)

        return jsonify({
            'success': True,
            'total_to_retry': len(failed_records),
            'successful': success_count,
            'failed': len(errors),
            'errors': errors
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)
