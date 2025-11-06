"""
DUANO API Client
A comprehensive Python interface for interacting with DUANO's API using OAuth2 authentication
"""

import os
import time
import logging
import base64
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import urlencode, parse_qs, urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class DuanoAPIError(Exception):
    """Base exception for DUANO API errors"""
    pass


class AuthenticationError(DuanoAPIError):
    """Raised when authentication fails"""
    pass


class RateLimitError(DuanoAPIError):
    """Raised when rate limit is exceeded"""
    pass


class ValidationError(DuanoAPIError):
    """Raised when request validation fails"""
    pass


@dataclass
class APIResponse:
    """Standardized API response wrapper"""
    success: bool
    data: Any
    message: str = ""
    status_code: int = 200
    headers: Dict[str, str] = None


@dataclass
class OAuthToken:
    """OAuth2 token data"""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    refresh_token: Optional[str] = None
    scope: Optional[str] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    @property
    def expires_at(self) -> datetime:
        """When the token expires"""
        return self.created_at + timedelta(seconds=self.expires_in)
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired (with 5 minute buffer)"""
        return datetime.now() >= (self.expires_at - timedelta(minutes=5))
    
    @property
    def authorization_header(self) -> str:
        """Get authorization header value"""
        return f"{self.token_type} {self.access_token}"


class DuanoClient:
    """
    Main client for interacting with DUANO API using OAuth2 authentication
    
    Handles OAuth2 authentication, request management, and provides access to all
    DUANO data including sales, orders, clients, and products.
    """
    
    def __init__(
        self,
        client_id: str = None,
        client_secret: str = None,
        base_url: str = None,
        redirect_uri: str = None,
        timeout: int = 30,
        max_retries: int = 3,
        debug: bool = False
    ):
        # Load from environment if not provided
        self.client_id = client_id or os.getenv('DUANO_CLIENT_ID', '3')
        self.client_secret = client_secret or os.getenv('DUANO_CLIENT_SECRET', 'KBPJZ11EwPjAmEUKFWDoXGQaDdMRPFES2P6VCxEC')
        self.base_url = base_url or os.getenv('DUANO_API_BASE_URL', 'https://yugen.douano.com')
        self.redirect_uri = redirect_uri or os.getenv('DUANO_REDIRECT_URI', 'http://localhost:5002/oauth/callback')
        self.timeout = timeout
        self.max_retries = max_retries
        self.debug = debug
        
        if not self.client_id or not self.client_secret:
            raise AuthenticationError("Client ID and secret are required")
        
        # OAuth2 endpoints (confirmed from DOUANO documentation)
        self.auth_url = f"{self.base_url}/authorize"
        self.token_url = f"{self.base_url}/oauth/token"
        
        # Token storage
        self.current_token: Optional[OAuthToken] = None
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Setup session with retry strategy
        self.session = self._setup_session()
        
        # Initialize modules based on actual DUANO API
        self.crm = CRMModule(self)
        self.accountancy = AccountancyModule(self)
        self.sales = SalesModule(self)
        self.products = ProductsModule(self)
        self.delivery_orders = DeliveryOrdersModule(self)
        self.pricing = PricingModule(self)
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger('duano_client')
        if self.debug:
            logger.setLevel(logging.DEBUG)
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger
    
    def _setup_session(self) -> requests.Session:
        """Setup requests session with retry strategy"""
        session = requests.Session()
        
        # Setup retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],  # Updated parameter name
            backoff_factor=1
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers (authorization will be added per request)
        session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'DUANO-Python-Client/1.0'
        })
        
        return session
    
    def get_authorization_url(self, scope: str = None, state: str = None) -> str:
        """
        Get OAuth2 authorization URL for user consent
        
        Args:
            scope: OAuth2 scope (optional)
            state: State parameter for CSRF protection (optional)
            
        Returns:
            Authorization URL for user to visit
        """
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
        }
        
        if scope:
            params['scope'] = scope
        if state:
            params['state'] = state
            
        return f"{self.auth_url}?{urlencode(params)}"
    
    def exchange_code_for_token(self, authorization_code: str) -> OAuthToken:
        """
        Exchange authorization code for access token
        
        Args:
            authorization_code: Authorization code from callback
            
        Returns:
            OAuthToken with access token
        """
        data = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': authorization_code,
            'redirect_uri': self.redirect_uri,
        }
        
        try:
            response = requests.post(
                self.token_url,
                data=data,
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                raise AuthenticationError(f"Token exchange failed: {response.status_code} - {response.text}")
            
            token_data = response.json()
            
            # Create token object
            self.current_token = OAuthToken(
                access_token=token_data['access_token'],
                token_type=token_data.get('token_type', 'Bearer'),
                expires_in=token_data.get('expires_in', 3600),
                refresh_token=token_data.get('refresh_token'),
                scope=token_data.get('scope')
            )
            
            if self.debug:
                self.logger.debug("Successfully obtained access token")
            
            return self.current_token
            
        except requests.exceptions.RequestException as e:
            raise AuthenticationError(f"Token exchange request failed: {str(e)}")
    
    def refresh_access_token(self) -> OAuthToken:
        """
        Refresh access token using refresh token
        
        Returns:
            New OAuthToken
        """
        if not self.current_token or not self.current_token.refresh_token:
            raise AuthenticationError("No refresh token available")
        
        data = {
            'grant_type': 'refresh_token',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': self.current_token.refresh_token,
        }
        
        try:
            response = requests.post(
                self.token_url,
                data=data,
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                raise AuthenticationError(f"Token refresh failed: {response.status_code} - {response.text}")
            
            token_data = response.json()
            
            # Update current token
            self.current_token = OAuthToken(
                access_token=token_data['access_token'],
                token_type=token_data.get('token_type', 'Bearer'),
                expires_in=token_data.get('expires_in', 3600),
                refresh_token=token_data.get('refresh_token', self.current_token.refresh_token),
                scope=token_data.get('scope')
            )
            
            if self.debug:
                self.logger.debug("Successfully refreshed access token")
            
            return self.current_token
            
        except requests.exceptions.RequestException as e:
            raise AuthenticationError(f"Token refresh request failed: {str(e)}")
    
    def client_credentials_flow(self, scope: str = None) -> OAuthToken:
        """
        Perform client credentials OAuth2 flow (for server-to-server authentication)
        
        Args:
            scope: OAuth2 scope (optional)
            
        Returns:
            OAuthToken with access token
        """
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        }
        
        if scope:
            data['scope'] = scope
        
        try:
            response = requests.post(
                self.token_url,
                data=data,
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                raise AuthenticationError(f"Client credentials flow failed: {response.status_code} - {response.text}")
            
            token_data = response.json()
            
            # Create token object
            self.current_token = OAuthToken(
                access_token=token_data['access_token'],
                token_type=token_data.get('token_type', 'Bearer'),
                expires_in=token_data.get('expires_in', 3600),
                refresh_token=token_data.get('refresh_token'),
                scope=token_data.get('scope')
            )
            
            if self.debug:
                self.logger.debug("Successfully obtained access token via client credentials")
            
            return self.current_token
            
        except requests.exceptions.RequestException as e:
            raise AuthenticationError(f"Client credentials request failed: {str(e)}")
    
    def _ensure_valid_token(self):
        """Ensure we have a valid access token, refreshing if necessary"""
        if not self.current_token:
            # Try client credentials flow first (for server-to-server)
            try:
                self.client_credentials_flow()
                return
            except AuthenticationError:
                raise AuthenticationError("No access token available and client credentials flow failed. Please authenticate first.")
        
        if self.current_token.is_expired:
            if self.current_token.refresh_token:
                try:
                    self.refresh_access_token()
                except AuthenticationError:
                    raise AuthenticationError("Token expired and refresh failed. Please re-authenticate.")
            else:
                raise AuthenticationError("Token expired and no refresh token available. Please re-authenticate.")
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Dict = None,
        params: Dict = None,
        headers: Dict = None
    ) -> APIResponse:
        """
        Make HTTP request to DUANO API
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (without base URL)
            data: Request body data
            params: Query parameters
            headers: Additional headers
            
        Returns:
            APIResponse object with standardized response data
        """
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        # Ensure we have a valid token
        self._ensure_valid_token()
        
        # Add authorization header
        request_headers = headers or {}
        if self.current_token:
            request_headers['Authorization'] = self.current_token.authorization_header
        
        if self.debug:
            self.logger.debug(f"Making {method} request to {url}")
            if data:
                self.logger.debug(f"Request data: {data}")
            if params:
                self.logger.debug(f"Query params: {params}")
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=request_headers,
                timeout=self.timeout
            )
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                self.logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                time.sleep(retry_after)
                raise RateLimitError(f"Rate limit exceeded. Retry after {retry_after} seconds")
            
            # Handle authentication errors
            if response.status_code == 401:
                raise AuthenticationError("Authentication failed. Check your API credentials")
            
            # Handle validation errors
            if response.status_code == 400:
                error_msg = response.json().get('message', 'Validation error')
                raise ValidationError(f"Request validation failed: {error_msg}")
            
            # Parse response
            try:
                response_data = response.json()
            except ValueError:
                response_data = response.text
            
            success = response.status_code < 400
            
            if self.debug:
                self.logger.debug(f"Response status: {response.status_code}")
                self.logger.debug(f"Response data: {response_data}")
            
            return APIResponse(
                success=success,
                data=response_data,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {str(e)}")
            raise DuanoAPIError(f"Request failed: {str(e)}")
    
    def get(self, endpoint: str, params: Dict = None) -> APIResponse:
        """Make GET request"""
        return self._make_request('GET', endpoint, params=params)
    
    def post(self, endpoint: str, data: Dict = None) -> APIResponse:
        """Make POST request"""
        return self._make_request('POST', endpoint, data=data)
    
    def put(self, endpoint: str, data: Dict = None) -> APIResponse:
        """Make PUT request"""
        return self._make_request('PUT', endpoint, data=data)
    
    def delete(self, endpoint: str) -> APIResponse:
        """Make DELETE request"""
        return self._make_request('DELETE', endpoint)
    
    def test_connection(self) -> bool:
        """Test API connection and authentication"""
        try:
            # Try to authenticate first
            if not self.current_token:
                self.client_credentials_flow()
            
            # Test with a real DUANO endpoint
            response = self.get('/api/public/v1/crm/crm-contact-persons')  # Real DUANO endpoint
            return response.success
        except Exception as e:
            self.logger.error(f"Connection test failed: {str(e)}")
            return False
    
    def set_access_token(self, access_token: str, token_type: str = "Bearer", expires_in: int = 3600):
        """
        Set access token directly (useful for testing or when you already have a token)
        
        Args:
            access_token: The access token
            token_type: Token type (usually "Bearer")
            expires_in: Token expiration time in seconds
        """
        self.current_token = OAuthToken(
            access_token=access_token,
            token_type=token_type,
            expires_in=expires_in
        )


class BaseModule:
    """Base class for API modules"""
    
    def __init__(self, client: DuanoClient):
        self.client = client
    
    def _handle_response(self, response: APIResponse, error_message: str = None):
        """Handle API response and raise appropriate errors"""
        if not response.success:
            error_msg = error_message or f"API request failed: {response.message}"
            raise DuanoAPIError(error_msg)
        return response.data


class CRMModule(BaseModule):
    """Module for handling CRM data - contact persons, companies, and actions"""
    
    def get_companies(
        self,
        filter_by_created_since: str = None,
        filter_by_updated_since: str = None,
        filter_by_is_active: bool = None,
        filter_by_is_customer: bool = None,
        filter_by_is_supplier: bool = None,
        order_by_name: str = None,
        order_by_public_name: str = None,
        per_page: int = 50,
        page: int = 1,
        **kwargs
    ) -> Dict:
        """
        Get list of CRM companies
        
        Args:
            filter_by_created_since: Filter by creation date (YYYY-MM-DD)
            filter_by_updated_since: Filter by update date (YYYY-MM-DD)
            filter_by_is_active: Filter by active status
            filter_by_is_customer: Filter by customer status
            filter_by_is_supplier: Filter by supplier status
            order_by_name: Order by name (asc/desc)
            order_by_public_name: Order by public name (asc/desc)
            per_page: Number of results per page (default: 50)
            page: Page number (default: 1)
            **kwargs: Additional filter parameters
            
        Returns:
            Companies data
        """
        params = {}
        if filter_by_created_since:
            params['filter_by_created_since'] = filter_by_created_since
        if filter_by_updated_since:
            params['filter_by_updated_since'] = filter_by_updated_since
        if filter_by_is_active is not None:
            params['filter_by_is_active'] = filter_by_is_active
        if filter_by_is_customer is not None:
            params['filter_by_is_customer'] = filter_by_is_customer
        if filter_by_is_supplier is not None:
            params['filter_by_is_supplier'] = filter_by_is_supplier
        if order_by_name:
            params['order_by_name'] = order_by_name
        if order_by_public_name:
            params['order_by_public_name'] = order_by_public_name
        if per_page:
            params['per_page'] = per_page
        if page:
            params['page'] = page
        
        # Add any additional parameters
        params.update(kwargs)
        
        response = self.client.get('/api/public/v1/crm/crm-companies', params=params)
        return self._handle_response(response, "Failed to fetch companies")
    
    def get_company(self, company_id: int) -> Dict:
        """
        Get specific company by ID (includes commercial info like price list and discounts)
        
        Args:
            company_id: Company ID
            
        Returns:
            Company data with commercial information
        """
        response = self.client.get(f'/api/public/v1/crm/crm-companies/{company_id}')
        return self._handle_response(response, f"Failed to fetch company {company_id}")
    
    def get_contact_persons(
        self,
        filter_by_created_since: str = None,
        filter_by_updated_since: str = None,
        filter_by_crm_company: str = None,
        filter_by_is_active: bool = None,
        order_by_name: str = None,
        order_by_crm_company_name: str = None,
        **kwargs
    ) -> Dict:
        """
        Get list of CRM contact persons
        
        Args:
            filter_by_created_since: Filter by creation date (YYYY-MM-DD)
            filter_by_updated_since: Filter by update date (YYYY-MM-DD)
            filter_by_crm_company: Filter by company
            filter_by_is_active: Filter by active status
            order_by_name: Order by name
            order_by_crm_company_name: Order by company name
            **kwargs: Additional filter parameters
            
        Returns:
            Contact persons data
        """
        params = {}
        if filter_by_created_since:
            params['filter_by_created_since'] = filter_by_created_since
        if filter_by_updated_since:
            params['filter_by_updated_since'] = filter_by_updated_since
        if filter_by_crm_company:
            params['filter_by_crm_company'] = filter_by_crm_company
        if filter_by_is_active is not None:
            params['filter_by_is_active'] = filter_by_is_active
        if order_by_name:
            params['order_by_name'] = order_by_name
        if order_by_crm_company_name:
            params['order_by_crm_company_name'] = order_by_crm_company_name
        
        # Add any additional parameters
        params.update(kwargs)
        
        response = self.client.get('/api/public/v1/crm/crm-contact-persons', params=params)
        return self._handle_response(response, "Failed to fetch contact persons")
    
    def get_contact_person(self, contact_id: int) -> Dict:
        """
        Get specific contact person by ID
        
        Args:
            contact_id: Contact person ID
            
        Returns:
            Contact person data
        """
        response = self.client.get(f'/api/public/v1/crm/crm-contact-persons/{contact_id}')
        return self._handle_response(response, f"Failed to fetch contact person {contact_id}")
    
    def get_actions(
        self,
        filter_by_date: str = None,
        filter_by_start_date: str = None,
        filter_by_end_date: str = None,
        filter_by_crm_company_id: int = None,
        filter_by_user_id: int = None,
        filter_by_status: str = None,
        order_by_start_date: str = None,
        **kwargs
    ) -> Dict:
        """
        Get CRM actions
        
        Args:
            filter_by_date: Filter by specific date
            filter_by_start_date: Filter by start date
            filter_by_end_date: Filter by end date
            filter_by_crm_company_id: Filter by company ID
            filter_by_user_id: Filter by user ID
            filter_by_status: Filter by status (to_do, done, etc.)
            order_by_start_date: Order by start date
            **kwargs: Additional filter parameters
            
        Returns:
            Actions data
        """
        params = {}
        if filter_by_date:
            params['filter_by_date'] = filter_by_date
        if filter_by_start_date:
            params['filter_by_start_date'] = filter_by_start_date
        if filter_by_end_date:
            params['filter_by_end_date'] = filter_by_end_date
        if filter_by_crm_company_id:
            params['filter_by_crm_company_id'] = filter_by_crm_company_id
        if filter_by_user_id:
            params['filter_by_user_id'] = filter_by_user_id
        if filter_by_status:
            params['filter_by_status'] = filter_by_status
        if order_by_start_date:
            params['order_by_start_date'] = order_by_start_date
        
        # Add any additional parameters
        params.update(kwargs)
        
        response = self.client.get('/api/public/v1/crm/crm-actions', params=params)
        return self._handle_response(response, "Failed to fetch CRM actions")


class AccountancyModule(BaseModule):
    """Module for handling accountancy data - accounts, bookings, etc."""
    
    def get_accounts(
        self,
        order_by_number: str = None,
        order_by_description: str = None,
        filter_by_is_visible: bool = None,
        filter_by_type: str = None,
        **kwargs
    ) -> Dict:
        """
        Get list of accounts
        
        Args:
            order_by_number: Order by account number
            order_by_description: Order by description
            filter_by_is_visible: Filter by visibility
            filter_by_type: Filter by account type
            **kwargs: Additional filter parameters
            
        Returns:
            Accounts data
        """
        params = {}
        if order_by_number:
            params['order_by_number'] = order_by_number
        if order_by_description:
            params['order_by_description'] = order_by_description
        if filter_by_is_visible is not None:
            params['filter_by_is_visible'] = filter_by_is_visible
        if filter_by_type:
            params['filter_by_type'] = filter_by_type
        
        # Add any additional parameters
        params.update(kwargs)
        
        response = self.client.get('/api/public/v1/accountancy/accounts', params=params)
        return self._handle_response(response, "Failed to fetch accounts")
    
    def get_account(self, account_id: int) -> Dict:
        """
        Get specific account by ID
        
        Args:
            account_id: Account ID
            
        Returns:
            Account data
        """
        response = self.client.get(f'/api/public/v1/accountancy/accounts/{account_id}')
        return self._handle_response(response, f"Failed to fetch account {account_id}")
    
    def get_bookings(
        self,
        order_by_date: str = None,
        order_by_journal: str = None,
        order_by_account: str = None,
        order_by_book_number: str = None,
        order_by_booking_type: str = None,
        filter_by_start_date: str = None,
        filter_by_end_date: str = None,
        filter_by_journal: str = None,
        filter_by_account: str = None,
        filter_by_book_number: str = None,
        filter_by_cost_center: str = None,
        filter_by_cost_unit: str = None,
        filter_by_company: str = None,
        filter_by_product: str = None,
        filter_by_stock_location: str = None,
        filter_by_booking_type: str = None,
        filter_by_transaction: str = None,
        filter_by_updated_since: str = None,
        filter_by_created_since: str = None,
        per_page: int = 50,
        page: int = 1,
        **kwargs
    ) -> Dict:
        """
        Get list of bookings with extensive filtering and ordering options
        
        Args:
            order_by_date: Order by booking date (asc/desc)
            order_by_journal: Order by journal (asc/desc)
            order_by_account: Order by account (asc/desc)
            order_by_book_number: Order by book number (asc/desc)
            order_by_booking_type: Order by booking type (asc/desc)
            filter_by_start_date: Filter by start date (YYYY-MM-DD)
            filter_by_end_date: Filter by end date (YYYY-MM-DD)
            filter_by_journal: Filter by journal
            filter_by_account: Filter by account
            filter_by_book_number: Filter by book number
            filter_by_cost_center: Filter by cost center
            filter_by_cost_unit: Filter by cost unit
            filter_by_company: Filter by company
            filter_by_product: Filter by product
            filter_by_stock_location: Filter by stock location
            filter_by_booking_type: Filter by booking type
            filter_by_transaction: Filter by transaction
            filter_by_updated_since: Filter by update date (YYYY-MM-DD)
            filter_by_created_since: Filter by creation date (YYYY-MM-DD)
            per_page: Number of results per page (default: 50)
            page: Page number (default: 1)
            **kwargs: Additional filter parameters
            
        Returns:
            Bookings data
        """
        params = {}
        
        # Ordering parameters
        if order_by_date:
            params['order_by_date'] = order_by_date
        if order_by_journal:
            params['order_by_journal'] = order_by_journal
        if order_by_account:
            params['order_by_account'] = order_by_account
        if order_by_book_number:
            params['order_by_book_number'] = order_by_book_number
        if order_by_booking_type:
            params['order_by_booking_type'] = order_by_booking_type
        
        # Filtering parameters
        if filter_by_start_date:
            params['filter_by_start_date'] = filter_by_start_date
        if filter_by_end_date:
            params['filter_by_end_date'] = filter_by_end_date
        if filter_by_journal:
            params['filter_by_journal'] = filter_by_journal
        if filter_by_account:
            params['filter_by_account'] = filter_by_account
        if filter_by_book_number:
            params['filter_by_book_number'] = filter_by_book_number
        if filter_by_cost_center:
            params['filter_by_cost_center'] = filter_by_cost_center
        if filter_by_cost_unit:
            params['filter_by_cost_unit'] = filter_by_cost_unit
        if filter_by_company:
            params['filter_by_company'] = filter_by_company
        if filter_by_product:
            params['filter_by_product'] = filter_by_product
        if filter_by_stock_location:
            params['filter_by_stock_location'] = filter_by_stock_location
        if filter_by_booking_type:
            params['filter_by_booking_type'] = filter_by_booking_type
        if filter_by_transaction:
            params['filter_by_transaction'] = filter_by_transaction
        if filter_by_updated_since:
            params['filter_by_updated_since'] = filter_by_updated_since
        if filter_by_created_since:
            params['filter_by_created_since'] = filter_by_created_since
        
        # Pagination parameters
        if per_page:
            params['per_page'] = per_page
        if page:
            params['page'] = page
        
        # Add any additional parameters
        params.update(kwargs)
        
        response = self.client.get('/api/public/v1/accountancy/bookings', params=params)
        return self._handle_response(response, "Failed to fetch bookings")
    
    def get_booking(self, booking_id: int) -> Dict:
        """
        Get specific booking by ID
        
        Args:
            booking_id: Booking ID
            
        Returns:
            Booking data
        """
        response = self.client.get(f'/api/public/v1/accountancy/bookings/{booking_id}')
        return self._handle_response(response, f"Failed to fetch booking {booking_id}")
    
    def get_company_bookings(self, company_id: int, **kwargs) -> Dict:
        """
        Get bookings for a specific company
        
        Args:
            company_id: Company ID to get bookings for
            **kwargs: Additional filter parameters
            
        Returns:
            Bookings data for the company
        """
        params = {'filter_by_company': company_id}
        params.update(kwargs)
        
        return self.get_bookings(**params)


class SalesModule(BaseModule):
    """Module for handling Sales data - invoices, quotes, and trade data"""
    
    def get_sales_invoices(
        self,
        filter_by_created_since: str = None,
        filter_by_updated_since: str = None,
        filter_by_company: str = None,
        filter_by_status: str = None,
        order_by_date: str = None,
        order_by_amount: str = None,
        per_page: int = 50,
        page: int = 1,
        **kwargs
    ) -> Dict:
        """
        Get list of sales invoices
        
        Args:
            filter_by_created_since: Filter by creation date (YYYY-MM-DD)
            filter_by_updated_since: Filter by update date (YYYY-MM-DD)
            filter_by_company: Filter by company
            filter_by_status: Filter by invoice status
            order_by_date: Order by date (asc/desc)
            order_by_amount: Order by amount (asc/desc)
            per_page: Number of results per page (default: 50)
            page: Page number (default: 1)
            **kwargs: Additional filter parameters
            
        Returns:
            Sales invoices data
        """
        params = {}
        if filter_by_created_since:
            params['filter_by_created_since'] = filter_by_created_since
        if filter_by_updated_since:
            params['filter_by_updated_since'] = filter_by_updated_since
        if filter_by_company:
            params['filter_by_company'] = filter_by_company
        if filter_by_status:
            params['filter_by_status'] = filter_by_status
        if order_by_date:
            params['order_by_date'] = order_by_date
        if order_by_amount:
            params['order_by_amount'] = order_by_amount
        if per_page:
            params['per_page'] = per_page
        if page:
            params['page'] = page
        
        # Add any additional parameters
        params.update(kwargs)
        
        response = self.client.get('/api/public/v1/trade/sales-invoices', params=params)
        return self._handle_response(response, "Failed to fetch sales invoices")
    
    def get_sales_invoice(self, invoice_id: int) -> Dict:
        """
        Get specific sales invoice by ID
        
        Args:
            invoice_id: Sales invoice ID
            
        Returns:
            Sales invoice data
        """
        response = self.client.get(f'/api/public/v1/trade/sales-invoices/{invoice_id}')
        return self._handle_response(response, f"Failed to fetch sales invoice {invoice_id}")
    
    def get_company_sales(self, company_id: int, **kwargs) -> Dict:
        """
        Get sales data for a specific company
        
        Args:
            company_id: Company ID to get sales for
            **kwargs: Additional filter parameters
            
        Returns:
            Sales data for the company
        """
        params = {'filter_by_company': company_id}
        params.update(kwargs)
        
        return self.get_sales_invoices(**params)


class ProductsModule(BaseModule):
    """Module for handling Products data - composed product items, products, and inventory"""
    
    def get_product_categories(
        self,
        filter_by_created_since: str = None,
        filter_by_updated_since: str = None,
        filter_by_is_active: bool = None,
        order_by_name: str = None,
        per_page: int = 50,
        page: int = 1,
        **kwargs
    ) -> Dict:
        """
        Get list of product categories
        
        Args:
            filter_by_created_since: Filter by creation date (YYYY-MM-DD)
            filter_by_updated_since: Filter by update date (YYYY-MM-DD)
            filter_by_is_active: Filter by active status
            order_by_name: Order by name (asc/desc)
            per_page: Number of results per page (default: 50)
            page: Page number (default: 1)
            **kwargs: Additional filter parameters
            
        Returns:
            Product categories data
        """
        params = {}
        if filter_by_created_since:
            params['filter_by_created_since'] = filter_by_created_since
        if filter_by_updated_since:
            params['filter_by_updated_since'] = filter_by_updated_since
        if filter_by_is_active is not None:
            params['filter_by_is_active'] = filter_by_is_active
        if order_by_name:
            params['order_by_name'] = order_by_name
        if per_page:
            params['per_page'] = per_page
        if page:
            params['page'] = page
        
        # Add any additional parameters
        params.update(kwargs)
        
        response = self.client.get('/api/public/v1/core/product-categories', params=params)
        return self._handle_response(response, "Failed to fetch product categories")
    
    def get_product_category(self, category_id: int) -> Dict:
        """
        Get specific product category by ID
        
        Args:
            category_id: Product category ID
            
        Returns:
            Product category data
        """
        response = self.client.get(f'/api/public/v1/core/product-categories/{category_id}')
        return self._handle_response(response, f"Failed to fetch product category {category_id}")
    
    def get_products(
        self,
        filter_by_created_since: str = None,
        filter_by_updated_since: str = None,
        filter_by_is_active: bool = None,
        filter_by_is_sellable: bool = None,
        filter_by_category: int = None,
        order_by_name: str = None,
        order_by_sku: str = None,
        per_page: int = 50,
        page: int = 1,
        **kwargs
    ) -> Dict:
        """
        Get list of products
        
        Args:
            filter_by_created_since: Filter by creation date (YYYY-MM-DD)
            filter_by_updated_since: Filter by update date (YYYY-MM-DD)
            filter_by_is_active: Filter by active status
            filter_by_is_sellable: Filter by sellable status
            filter_by_category: Filter by product category ID
            order_by_name: Order by name (asc/desc)
            order_by_sku: Order by SKU (asc/desc)
            per_page: Number of results per page (default: 50)
            page: Page number (default: 1)
            **kwargs: Additional filter parameters
            
        Returns:
            Products data
        """
        params = {}
        if filter_by_created_since:
            params['filter_by_created_since'] = filter_by_created_since
        if filter_by_updated_since:
            params['filter_by_updated_since'] = filter_by_updated_since
        if filter_by_is_active is not None:
            params['filter_by_is_active'] = filter_by_is_active
        if filter_by_is_sellable is not None:
            params['filter_by_is_sellable'] = filter_by_is_sellable
        if filter_by_category:
            params['filter_by_category'] = filter_by_category
        if order_by_name:
            params['order_by_name'] = order_by_name
        if order_by_sku:
            params['order_by_sku'] = order_by_sku
        if per_page:
            params['per_page'] = per_page
        if page:
            params['page'] = page
        
        # Add any additional parameters
        params.update(kwargs)
        
        response = self.client.get('/api/public/v1/core/products', params=params)
        return self._handle_response(response, "Failed to fetch products")
    
    def get_product(self, product_id: int) -> Dict:
        """
        Get specific product by ID
        
        Args:
            product_id: Product ID
            
        Returns:
            Product data
        """
        response = self.client.get(f'/api/public/v1/core/products/{product_id}')
        return self._handle_response(response, f"Failed to fetch product {product_id}")
    
    def get_composed_product_items(
        self,
        filter_by_created_since: str = None,
        filter_by_updated_since: str = None,
        filter_by_composed_product: str = None,
        filter_by_product: str = None,
        order_by_name: str = None,
        order_by_sku: str = None,
        per_page: int = 50,
        page: int = 1,
        **kwargs
    ) -> Dict:
        """
        Get list of composed product items (product recipes/components)
        
        Args:
            filter_by_created_since: Filter by creation date (YYYY-MM-DD)
            filter_by_updated_since: Filter by update date (YYYY-MM-DD)
            filter_by_composed_product: Filter by composed product
            filter_by_product: Filter by component product
            order_by_name: Order by name (asc/desc)
            order_by_sku: Order by SKU (asc/desc)
            per_page: Number of results per page (default: 50)
            page: Page number (default: 1)
            **kwargs: Additional filter parameters
            
        Returns:
            Composed product items data
        """
        params = {}
        if filter_by_created_since:
            params['filter_by_created_since'] = filter_by_created_since
        if filter_by_updated_since:
            params['filter_by_updated_since'] = filter_by_updated_since
        if filter_by_composed_product:
            params['filter_by_composed_product'] = filter_by_composed_product
        if filter_by_product:
            params['filter_by_product'] = filter_by_product
        if order_by_name:
            params['order_by_name'] = order_by_name
        if order_by_sku:
            params['order_by_sku'] = order_by_sku
        if per_page:
            params['per_page'] = per_page
        if page:
            params['page'] = page
        
        # Add any additional parameters
        params.update(kwargs)
        
        response = self.client.get('/api/public/v1/core/composed-product-items', params=params)
        return self._handle_response(response, "Failed to fetch composed product items")
    
    def get_composed_product_item(self, item_id: int) -> Dict:
        """
        Get specific composed product item by ID
        
        Args:
            item_id: Composed product item ID
            
        Returns:
            Composed product item data
        """
        response = self.client.get(f'/api/public/v1/core/composed-product-items/{item_id}')
        return self._handle_response(response, f"Failed to fetch composed product item {item_id}")
    
    def get_products_by_composed_product(self, composed_product_id: int, **kwargs) -> Dict:
        """
        Get all component products for a specific composed product
        
        Args:
            composed_product_id: Composed product ID to get components for
            **kwargs: Additional filter parameters
            
        Returns:
            Component products data
        """
        params = {'filter_by_composed_product': composed_product_id}
        params.update(kwargs)
        
        return self.get_composed_product_items(**params)
    
    def get_composed_products_by_component(self, product_id: int, **kwargs) -> Dict:
        """
        Get all composed products that use a specific component product
        
        Args:
            product_id: Component product ID
            **kwargs: Additional filter parameters
            
        Returns:
            Composed products that use this component
        """
        params = {'filter_by_product': product_id}
        params.update(kwargs)
        
        return self.get_composed_product_items(**params)
    
    def get_product_hierarchy(self, **kwargs) -> Dict:
        """
        Get the complete product hierarchy with composed products and their components
        
        Args:
            **kwargs: Additional filter parameters
            
        Returns:
            Complete product hierarchy
        """
        # Get all composed product items to build hierarchy
        all_items = self.get_composed_product_items(per_page=1000, **kwargs)
        
        # Process the data to create a hierarchical structure
        if 'result' in all_items and 'data' in all_items['result']:
            items = all_items['result']['data']
            
            # Group by composed product
            hierarchy = {}
            for item in items:
                composed_product = item.get('composed_product', {})
                component_product = item.get('product', {})
                quantity = item.get('quantity', 0)
                
                composed_id = composed_product.get('id')
                if composed_id not in hierarchy:
                    hierarchy[composed_id] = {
                        'composed_product': composed_product,
                        'components': []
                    }
                
                hierarchy[composed_id]['components'].append({
                    'product': component_product,
                    'quantity': quantity,
                    'item_id': item.get('id')
                })
            
            # Convert to list format
            all_items['result']['hierarchy'] = list(hierarchy.values())
        
        return all_items


# Convenience function to create client instance
class DeliveryOrdersModule(BaseModule):
    """Module for handling Delivery Orders data - orders, items, and logistics"""
    
    def get_delivery_orders(
        self,
        filter_by_created_since: str = None,
        filter_by_updated_since: str = None,
        filter_by_customer: str = None,
        filter_by_supplier: str = None,
        filter_by_user: str = None,
        filter_by_date: str = None,
        filter_by_status: str = None,
        order_by_date: str = None,
        order_by_customer: str = None,
        per_page: int = 50,
        page: int = 1,
        **kwargs
    ) -> Dict:
        """
        Get list of delivery orders
        
        Args:
            filter_by_created_since: Filter by creation date (YYYY-MM-DD)
            filter_by_updated_since: Filter by update date (YYYY-MM-DD)
            filter_by_customer: Filter by customer ID
            filter_by_supplier: Filter by supplier ID
            filter_by_user: Filter by user ID
            filter_by_date: Filter by order date (YYYY-MM-DD)
            filter_by_status: Filter by order status
            order_by_date: Order by date (asc/desc)
            order_by_customer: Order by customer (asc/desc)
            per_page: Number of results per page (default: 50)
            page: Page number (default: 1)
            **kwargs: Additional filter parameters
            
        Returns:
            Delivery orders data
        """
        params = {}
        if filter_by_created_since:
            params['filter_by_created_since'] = filter_by_created_since
        if filter_by_updated_since:
            params['filter_by_updated_since'] = filter_by_updated_since
        if filter_by_customer:
            params['filter_by_customer'] = filter_by_customer
        if filter_by_supplier:
            params['filter_by_supplier'] = filter_by_supplier
        if filter_by_user:
            params['filter_by_user'] = filter_by_user
        if filter_by_date:
            params['filter_by_date'] = filter_by_date
        if filter_by_status:
            params['filter_by_status'] = filter_by_status
        if order_by_date:
            params['order_by_date'] = order_by_date
        if order_by_customer:
            params['order_by_customer'] = order_by_customer
        if per_page:
            params['per_page'] = per_page
        if page:
            params['page'] = page
        
        # Add any additional parameters
        params.update(kwargs)
        
        response = self.client.get('/api/public/v1/crm/delivery-orders', params=params)
        return self._handle_response(response, "Failed to fetch delivery orders")
    
    def get_delivery_order(self, order_id: int) -> Dict:
        """
        Get specific delivery order by ID
        
        Args:
            order_id: Delivery order ID
            
        Returns:
            Delivery order data
        """
        response = self.client.get(f'/api/public/v1/crm/delivery-orders/{order_id}')
        return self._handle_response(response, f"Failed to fetch delivery order {order_id}")
    
    def get_customer_orders(self, customer_id: int, **kwargs) -> Dict:
        """
        Get delivery orders for a specific customer
        
        Args:
            customer_id: Customer ID to get orders for
            **kwargs: Additional filter parameters
            
        Returns:
            Delivery orders data for the customer
        """
        params = {'filter_by_customer': customer_id}
        params.update(kwargs)
        
        return self.get_delivery_orders(**params)
    
    def get_supplier_orders(self, supplier_id: int, **kwargs) -> Dict:
        """
        Get delivery orders for a specific supplier
        
        Args:
            supplier_id: Supplier ID to get orders for
            **kwargs: Additional filter parameters
            
        Returns:
            Delivery orders data for the supplier
        """
        params = {'filter_by_supplier': supplier_id}
        params.update(kwargs)
        
        return self.get_delivery_orders(**params)
    
    def update_delivery_order(self, order_id: int, order_data: Dict) -> Dict:
        """
        Update a delivery order
        
        Args:
            order_id: Delivery order ID to update
            order_data: Order data to update
            
        Returns:
            Updated delivery order data
        """
        response = self.client.post(f'/api/public/v1/crm/delivery-orders/{order_id}', json=order_data)
        return self._handle_response(response, f"Failed to update delivery order {order_id}")


class PricingModule(BaseModule):
    """Module for handling Pricing data - price adjustments, discounts, and promotions"""
    
    def get_sales_price_lists(
        self,
        filter_by_created_since: str = None,
        filter_by_updated_since: str = None,
        filter_by_is_active: bool = None,
        order_by_name: str = None,
        per_page: int = 50,
        page: int = 1,
        **kwargs
    ) -> Dict:
        """
        Get list of sales price lists (verkoopprijzen)
        
        Args:
            filter_by_created_since: Filter by creation date (YYYY-MM-DD)
            filter_by_updated_since: Filter by update date (YYYY-MM-DD)
            filter_by_is_active: Filter by active status
            order_by_name: Order by name (asc/desc)
            per_page: Number of results per page (default: 50)
            page: Page number (default: 1)
            **kwargs: Additional filter parameters
            
        Returns:
            Sales price lists data
        """
        params = {}
        if filter_by_created_since:
            params['filter_by_created_since'] = filter_by_created_since
        if filter_by_updated_since:
            params['filter_by_updated_since'] = filter_by_updated_since
        if filter_by_is_active is not None:
            params['filter_by_is_active'] = filter_by_is_active
        if order_by_name:
            params['order_by_name'] = order_by_name
        if per_page:
            params['per_page'] = per_page
        if page:
            params['page'] = page
        
        # Add any additional parameters
        params.update(kwargs)
        
        response = self.client.get('/api/public/v1/core/sales-price-lists', params=params)
        return self._handle_response(response, "Failed to fetch sales price lists")
    
    def get_sales_price_list(self, price_list_id: int) -> Dict:
        """
        Get specific sales price list by ID
        
        Args:
            price_list_id: Sales price list ID
            
        Returns:
            Sales price list data with products and prices
        """
        response = self.client.get(f'/api/public/v1/core/sales-price-lists/{price_list_id}')
        return self._handle_response(response, f"Failed to fetch sales price list {price_list_id}")
    
    def get_sales_price_list_items(
        self,
        price_list_id: int = None,
        filter_by_product: int = None,
        per_page: int = 50,
        page: int = 1,
        **kwargs
    ) -> Dict:
        """
        Get items/products in sales price lists with their prices
        
        Args:
            price_list_id: Filter by specific price list ID
            filter_by_product: Filter by product ID
            per_page: Number of results per page (default: 50)
            page: Page number (default: 1)
            **kwargs: Additional filter parameters
            
        Returns:
            Sales price list items with products and prices
        """
        params = {}
        if price_list_id:
            params['filter_by_sales_price_list'] = price_list_id
        if filter_by_product:
            params['filter_by_product'] = filter_by_product
        if per_page:
            params['per_page'] = per_page
        if page:
            params['page'] = page
        
        # Add any additional parameters
        params.update(kwargs)
        
        response = self.client.get('/api/public/v1/core/sales-price-list-items', params=params)
        return self._handle_response(response, "Failed to fetch sales price list items")
    
    def get_purchase_price_adjustments(
        self,
        filter_by_companies: list = None,
        filter_by_price_classes: list = None,
        filter_by_product: int = None,
        filter_by_is_active: bool = None,
        filter_by_price_adjustment_type: str = None,
        filter_by_price_adjustment_discount_type: str = None,
        per_page: int = 50,
        page: int = 1,
        **kwargs
    ) -> Dict:
        """
        Get purchase price adjustment items
        
        Args:
            filter_by_companies: Array of company IDs
            filter_by_price_classes: Array of price class IDs
            filter_by_product: Product ID
            filter_by_is_active: Filter by active status
            filter_by_price_adjustment_type: promotion|contract
            filter_by_price_adjustment_discount_type: absolute_discount|percent_discount|new_price|free_product|derived_price_*
            per_page: Number of results per page (default: 50)
            page: Page number (default: 1)
            **kwargs: Additional filter parameters
            
        Returns:
            Purchase price adjustments data
        """
        params = {}
        if filter_by_companies:
            params['filter_by_companies'] = filter_by_companies
        if filter_by_price_classes:
            params['filter_by_price_classes'] = filter_by_price_classes
        if filter_by_product:
            params['filter_by_product'] = filter_by_product
        if filter_by_is_active is not None:
            params['filter_by_is_active'] = filter_by_is_active
        if filter_by_price_adjustment_type:
            params['filter_by_price_adjustment_type'] = filter_by_price_adjustment_type
        if filter_by_price_adjustment_discount_type:
            params['filter_by_price_adjustment_discount_type'] = filter_by_price_adjustment_discount_type
        if per_page:
            params['per_page'] = per_page
        if page:
            params['page'] = page
        
        # Add any additional parameters
        params.update(kwargs)
        
        response = self.client.get('/api/public/v1/trade/price-adjustments-items/purchase', params=params)
        return self._handle_response(response, "Failed to fetch purchase price adjustments")
    
    def get_sales_price_adjustments(
        self,
        filter_by_companies: list = None,
        filter_by_price_classes: list = None,
        filter_by_product: int = None,
        filter_by_is_active: bool = None,
        filter_by_price_adjustment_type: str = None,
        filter_by_price_adjustment_discount_type: str = None,
        per_page: int = 50,
        page: int = 1,
        **kwargs
    ) -> Dict:
        """
        Get sales price adjustment items
        
        Args:
            filter_by_companies: Array of company IDs
            filter_by_price_classes: Array of price class IDs
            filter_by_product: Product ID
            filter_by_is_active: Filter by active status
            filter_by_price_adjustment_type: promotion|contract
            filter_by_price_adjustment_discount_type: absolute_discount|percent_discount|new_price|free_product|derived_price_*
            per_page: Number of results per page (default: 50)
            page: Page number (default: 1)
            **kwargs: Additional filter parameters
            
        Returns:
            Sales price adjustments data
        """
        params = {}
        if filter_by_companies:
            params['filter_by_companies'] = filter_by_companies
        if filter_by_price_classes:
            params['filter_by_price_classes'] = filter_by_price_classes
        if filter_by_product:
            params['filter_by_product'] = filter_by_product
        if filter_by_is_active is not None:
            params['filter_by_is_active'] = filter_by_is_active
        if filter_by_price_adjustment_type:
            params['filter_by_price_adjustment_type'] = filter_by_price_adjustment_type
        if filter_by_price_adjustment_discount_type:
            params['filter_by_price_adjustment_discount_type'] = filter_by_price_adjustment_discount_type
        if per_page:
            params['per_page'] = per_page
        if page:
            params['page'] = page
        
        # Add any additional parameters
        params.update(kwargs)
        
        response = self.client.get('/api/public/v1/trade/price-adjustments-items/sales', params=params)
        return self._handle_response(response, "Failed to fetch sales price adjustments")
    
    def get_purchase_price_adjustment(self, adjustment_id: int) -> Dict:
        """
        Get specific purchase price adjustment by ID
        
        Args:
            adjustment_id: Price adjustment ID
            
        Returns:
            Purchase price adjustment data
        """
        response = self.client.get(f'/api/public/v1/trade/price-adjustments-items/purchase/{adjustment_id}')
        return self._handle_response(response, f"Failed to fetch purchase price adjustment {adjustment_id}")
    
    def get_sales_price_adjustment(self, adjustment_id: int) -> Dict:
        """
        Get specific sales price adjustment by ID
        
        Args:
            adjustment_id: Price adjustment ID
            
        Returns:
            Sales price adjustment data
        """
        response = self.client.get(f'/api/public/v1/trade/price-adjustments-items/sales/{adjustment_id}')
        return self._handle_response(response, f"Failed to fetch sales price adjustment {adjustment_id}")
    
    def get_company_pricing(self, company_id: int, **kwargs) -> Dict:
        """
        Get pricing adjustments for a specific company
        
        Args:
            company_id: Company ID to get pricing for
            **kwargs: Additional filter parameters
            
        Returns:
            Pricing data for the company
        """
        params = {'filter_by_companies': [company_id]}
        params.update(kwargs)
        
        # Get both purchase and sales adjustments
        purchase_adjustments = self.get_purchase_price_adjustments(**params)
        sales_adjustments = self.get_sales_price_adjustments(**params)
        
        return {
            'purchase_adjustments': purchase_adjustments,
            'sales_adjustments': sales_adjustments
        }


def create_client(client_id: str = None, client_secret: str = None, **kwargs) -> DuanoClient:
    """
    Create a DUANO client instance
    
    Args:
        client_id: OAuth2 client ID (or set DUANO_CLIENT_ID environment variable)
        client_secret: OAuth2 client secret (or set DUANO_CLIENT_SECRET environment variable)
        **kwargs: Additional client configuration
        
    Returns:
        Configured DuanoClient instance
    """
    return DuanoClient(client_id=client_id, client_secret=client_secret, **kwargs)
