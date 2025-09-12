# DUANO API Client

A comprehensive Python interface for interacting with DUANO's API - the heart of your organization's data including sales numbers, orders, client data, product data, and everything else.

## Features

- 🔐 **OAuth2 Authentication** - Full OAuth2 support with multiple flow types
- 📊 **Sales Analytics** - Comprehensive sales data and reporting
- 📦 **Order Management** - Full CRUD operations for orders
- 👥 **Client Management** - Complete client data handling
- 🏷️ **Product Management** - Product catalog and inventory management
- 🔄 **Automatic Retries** - Built-in retry logic with exponential backoff
- 📝 **Comprehensive Logging** - Detailed logging for debugging
- ⚡ **Rate Limiting** - Automatic handling of API rate limits
- 🛡️ **Error Handling** - Robust error handling with custom exceptions

## Installation

1. Install required dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your environment variables (you can copy `ENV.EXAMPLE` to `.env` and fill in values):
```bash
export DUANO_CLIENT_ID="3"
export DUANO_CLIENT_SECRET="KBPJZ11EwPjAmEUKFWDoXGQaDdMRPFES2P6VCxEC"
export DUANO_API_BASE_URL="https://yugen.douano.com"
export DUANO_REDIRECT_URI="http://localhost:5002/oauth/callback"
export GOOGLE_MAPS_API_KEY="<your_maps_key>"
export OPENAI_API_KEY="<your_openai_key>"
```

## Prospecting Page

- A new page is available at `/prospecting` with Google Maps and Places Autocomplete.
- You can extract VAT numbers from a company's website and check if the VAT exists in your DUANO database.

**Note**: This is configured for the `yugen.douano.com` instance. Update if using a different subdomain.

## Quick Start

```python
from duano_client import create_client

# Create client (uses environment variables)
client = create_client()

# Or pass OAuth2 credentials directly
client = create_client(
    client_id="3",
    client_secret="KBPJZ11EwPjAmEUKFWDoXGQaDdMRPFES2P6VCxEC",
    debug=True
)

# Test connection
if client.test_connection():
    print("✅ Connected to DUANO API")
else:
    print("❌ Connection failed")
```

## OAuth2 Authentication

The DUANO API uses OAuth2 for authentication. The client supports multiple OAuth2 flows:

### 1. Client Credentials Flow (Recommended)
For server-to-server authentication:

```python
from duano_client import create_client

client = create_client(
    client_id="3",
    client_secret="KBPJZ11EwPjAmEUKFWDoXGQaDdMRPFES2P6VCxEC",
    base_url="https://yugen.douano.com"
)

# The client will automatically authenticate when making the first API call
contacts = client.crm.get_contact_persons()
```

### 2. Authorization Code Flow
For user authentication (requires browser interaction):

```python
# Get authorization URL
auth_url = client.get_authorization_url(scope="read write")
print(f"Visit: {auth_url}")

# After user authorizes, you'll get a callback with authorization code
# Exchange the code for an access token
token = client.exchange_code_for_token(authorization_code)
```

### 3. Interactive OAuth2 Flow
Use the included OAuth2 server for easy testing:

```bash
python oauth_server.py
```

Or run the interactive examples:

```bash
python oauth_example.py
```

## Usage Examples

### CRM Data

```python
# Get all contact persons
contacts = client.crm.get_contact_persons()
print(f"Total contacts: {len(contacts['result']['data'])}")

# Get contact persons with filters
filtered_contacts = client.crm.get_contact_persons(
    filter_by_created_since="2023-01-01",
    filter_by_is_active=True,
    order_by_name="asc"
)

# Get specific contact person
contact = client.crm.get_contact_person(contact_id=153)
print(f"Contact: {contact['result']['name']} - {contact['result']['email_address']}")

# Get CRM actions
actions = client.crm.get_actions()
for action in actions['result']['data']:
    print(f"Action: {action['subject']} - {action['status']}")

# Get filtered actions
pending_actions = client.crm.get_actions(
    filter_by_status="to_do",
    order_by_start_date="asc"
)
```

### Accountancy Data

```python
# Get all accounts
accounts = client.accountancy.get_accounts()

# Get accounts with filters
filtered_accounts = client.accountancy.get_accounts(
    filter_by_is_visible=True,
    order_by_number="asc"
)

# Get specific account
account = client.accountancy.get_account(account_id=123)

# Get specific booking
booking = client.accountancy.get_booking(booking_id=456)
```

### Real-world Example

```python
# Get active contacts and their recent actions
contacts = client.crm.get_contact_persons(filter_by_is_active=True)
actions = client.crm.get_actions(filter_by_status="to_do")

print(f"Active contacts: {len(contacts['result']['data'])}")
print(f"Pending actions: {len(actions['result']['data'])}")

# Show pending actions for each contact
for action in actions['result']['data'][:5]:
    company = action.get('crm_company', {}).get('name', 'Unknown')
    print(f"• {action['subject']} - {company} ({action['start_date']})")
```

## Configuration

The client can be configured using environment variables or by passing parameters directly:

### Environment Variables

```bash
# Required OAuth2 Credentials
DUANO_CLIENT_ID=3
DUANO_CLIENT_SECRET=KBPJZ11EwPjAmEUKFWDoXGQaDdMRPFES2P6VCxEC

# Optional
DUANO_API_BASE_URL=https://api.duano.com
DUANO_REDIRECT_URI=http://localhost:5001/oauth/callback
DUANO_TIMEOUT=30
DUANO_MAX_RETRIES=3
DUANO_DEBUG=false
DUANO_DEFAULT_PAGE_SIZE=50
DUANO_MAX_PAGE_SIZE=1000
```

### Direct Configuration

```python
from duano_client import DuanoClient

client = DuanoClient(
    client_id="3",
    client_secret="KBPJZ11EwPjAmEUKFWDoXGQaDdMRPFES2P6VCxEC",
    base_url="https://api.duano.com",
    redirect_uri="http://localhost:5001/oauth/callback",
    timeout=30,
    max_retries=3,
    debug=True
)
```

## Error Handling

The client includes comprehensive error handling:

```python
from duano_client import DuanoAPIError, AuthenticationError, RateLimitError

try:
    sales_data = client.sales.get_sales_summary()
except AuthenticationError:
    print("Invalid API credentials")
except RateLimitError:
    print("Rate limit exceeded - please wait")
except DuanoAPIError as e:
    print(f"API error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## API Modules

### CRMModule (`client.crm`)
- `get_contact_persons(**filters)` - Get list of contact persons with optional filters
- `get_contact_person(contact_id)` - Get specific contact person by ID
- `get_actions(**filters)` - Get CRM actions with optional filters

**Available filters for contact persons:**
- `filter_by_created_since` - Filter by creation date (YYYY-MM-DD)
- `filter_by_updated_since` - Filter by update date (YYYY-MM-DD)
- `filter_by_crm_company` - Filter by company
- `filter_by_is_active` - Filter by active status
- `order_by_name` - Order by name
- `order_by_crm_company_name` - Order by company name

**Available filters for actions:**
- `filter_by_date` - Filter by specific date
- `filter_by_start_date` - Filter by start date
- `filter_by_end_date` - Filter by end date
- `filter_by_crm_company_id` - Filter by company ID
- `filter_by_user_id` - Filter by user ID
- `filter_by_status` - Filter by status (to_do, done, etc.)
- `order_by_start_date` - Order by start date

### AccountancyModule (`client.accountancy`)
- `get_accounts(**filters)` - Get list of accounts with optional filters
- `get_account(account_id)` - Get specific account by ID
- `get_booking(booking_id)` - Get specific booking by ID

**Available filters for accounts:**
- `order_by_number` - Order by account number
- `order_by_description` - Order by description
- `filter_by_is_visible` - Filter by visibility
- `filter_by_type` - Filter by account type

## Advanced Features

### Automatic Retries
The client automatically retries failed requests with exponential backoff for transient errors (5xx status codes, network timeouts).

### Rate Limiting
Automatic handling of rate limits with respect for `Retry-After` headers.

### Logging
Enable debug logging to see detailed request/response information:

```python
client = create_client(debug=True)
```

### Pagination
All list endpoints support pagination:

```python
# Get all orders across multiple pages
all_orders = []
page = 1
while True:
    response = client.orders.list_orders(page=page, limit=100)
    all_orders.extend(response['data'])
    
    if page >= response['total_pages']:
        break
    page += 1
```

## Running Examples

Run the included examples to test your setup:

```bash
python examples.py
```

This will run comprehensive examples showing how to use all modules and features.

## Contributing

1. Ensure your API credentials are set up correctly
2. Run examples to verify functionality
3. Add new features following the existing patterns
4. Include comprehensive error handling
5. Add examples for new functionality

## Support

For issues with the DUANO API itself, contact DUANO support. For issues with this client library, check the error messages and logging output for troubleshooting information.
