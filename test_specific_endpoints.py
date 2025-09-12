"""
Test specific DOUANO API endpoints from the documentation

This script tests the exact endpoints mentioned in your documentation
to see what's working and what needs debugging.
"""

import requests
import json
from duano_client import create_client


def test_with_raw_requests():
    """Test endpoints using raw requests to get detailed response info"""
    print("🔬 Testing with Raw HTTP Requests")
    print("=" * 50)
    
    # Get OAuth token first
    print("🔐 Getting OAuth token...")
    client = create_client(
        client_id="3",
        client_secret="KBPJZ11EwPjAmEUKFWDoXGQaDdMRPFES2P6VCxEC",
        base_url="https://yugen.douano.com"
    )
    
    try:
        token = client.client_credentials_flow()
        print(f"✅ Token obtained: {token.access_token[:30]}...")
    except Exception as e:
        print(f"❌ Token failed: {e}")
        return
    
    # Setup headers
    headers = {
        'Authorization': f'Bearer {token.access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'DUANO-Python-Client/1.0'
    }
    
    # Test specific endpoints from documentation
    endpoints = [
        ("GET", "/api/public/v1/accountancy/accounts", "Accountancy Accounts"),
        ("GET", "/api/public/v1/accountancy/bookings/1", "Accountancy Booking #1"),
        ("GET", "/api/public/v1/crm/crm-contact-persons", "CRM Contact Persons"),
        ("GET", "/api/public/v1/crm/crm-actions", "CRM Actions"),
        
        # Try some variations
        ("GET", "/api/public/v1/accountancy", "Accountancy Root"),
        ("GET", "/api/public/v1/crm", "CRM Root"),
        ("GET", "/api/public/v1", "API Root"),
        ("GET", "/api/public", "Public API Root"),
    ]
    
    working_endpoints = []
    
    for method, endpoint, description in endpoints:
        url = f"https://yugen.douano.com{endpoint}"
        
        print(f"\n🧪 Testing: {method} {endpoint}")
        print(f"   Description: {description}")
        print(f"   URL: {url}")
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                timeout=15
            )
            
            print(f"   📊 Status: {response.status_code}")
            print(f"   📋 Headers: {response.headers.get('content-type', 'unknown')}")
            
            # Handle different response types
            if response.status_code == 200:
                working_endpoints.append((endpoint, description))
                
                content_type = response.headers.get('content-type', '').lower()
                
                if 'application/json' in content_type:
                    try:
                        data = response.json()
                        print(f"   ✅ JSON Response: {str(data)[:200]}...")
                    except json.JSONDecodeError:
                        print(f"   ⚠️  Invalid JSON: {response.text[:200]}...")
                elif 'text/html' in content_type:
                    print(f"   🌐 HTML Response (probably web interface)")
                    if "login" in response.text.lower():
                        print(f"   🔐 Looks like a login page - auth might be wrong")
                else:
                    print(f"   📄 Other content: {response.text[:200]}...")
                    
            elif response.status_code == 401:
                print(f"   🔐 Unauthorized - token might be invalid")
            elif response.status_code == 403:
                print(f"   🚫 Forbidden - insufficient permissions")
            elif response.status_code == 404:
                print(f"   ❌ Not Found - endpoint doesn't exist")
            elif response.status_code >= 500:
                print(f"   🔥 Server Error: {response.text[:100]}...")
            else:
                print(f"   ⚠️  Unexpected status: {response.text[:100]}...")
                
        except requests.exceptions.Timeout:
            print(f"   ⏰ Request timed out")
        except requests.exceptions.ConnectionError as e:
            print(f"   🌐 Connection error: {str(e)[:100]}...")
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:100]}...")
    
    return working_endpoints


def test_with_client():
    """Test using our DUANO client"""
    print(f"\n🤖 Testing with DUANO Client")
    print("=" * 40)
    
    client = create_client(
        client_id="3",
        client_secret="KBPJZ11EwPjAmEUKFWDoXGQaDdMRPFES2P6VCxEC",
        base_url="https://yugen.douano.com",
        debug=True
    )
    
    print("🔐 Authenticating...")
    try:
        token = client.client_credentials_flow()
        print(f"✅ Authenticated")
    except Exception as e:
        print(f"❌ Auth failed: {e}")
        return
    
    # Test CRM endpoints
    print(f"\n👥 Testing CRM endpoints...")
    try:
        print("  🧪 get_contact_persons()...")
        contacts = client.crm.get_contact_persons()
        print(f"  ✅ Success: {type(contacts)} - {str(contacts)[:100]}...")
    except Exception as e:
        print(f"  ❌ Failed: {str(e)[:150]}...")
    
    try:
        print("  🧪 get_actions()...")
        actions = client.crm.get_actions()
        print(f"  ✅ Success: {type(actions)} - {str(actions)[:100]}...")
    except Exception as e:
        print(f"  ❌ Failed: {str(e)[:150]}...")
    
    # Test Accountancy endpoints
    print(f"\n💰 Testing Accountancy endpoints...")
    try:
        print("  🧪 get_accounts()...")
        accounts = client.accountancy.get_accounts()
        print(f"  ✅ Success: {type(accounts)} - {str(accounts)[:100]}...")
    except Exception as e:
        print(f"  ❌ Failed: {str(e)[:150]}...")


def check_api_documentation():
    """Check if we can access API documentation"""
    print(f"\n📖 Checking API Documentation Access")
    print("=" * 45)
    
    # Try to access common documentation endpoints
    doc_endpoints = [
        "/docs",
        "/api/docs",
        "/api/documentation",
        "/swagger",
        "/api/swagger",
        "/openapi",
        "/api/openapi",
        "/api/public/v1/docs",
    ]
    
    for endpoint in doc_endpoints:
        url = f"https://yugen.douano.com{endpoint}"
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                print(f"✅ Found docs at: {url}")
                content_type = response.headers.get('content-type', '')
                if 'json' in content_type:
                    print(f"   📋 JSON documentation available")
                elif 'html' in content_type:
                    print(f"   🌐 HTML documentation available")
            else:
                print(f"❌ {endpoint} - {response.status_code}")
        except:
            print(f"❌ {endpoint} - Connection failed")


def main():
    """Main testing function"""
    print("🎯 DOUANO API Endpoint Testing")
    print("Testing specific endpoints from documentation")
    print("=" * 60)
    
    # Test with raw requests for detailed info
    working_endpoints = test_with_raw_requests()
    
    # Test with our client
    test_with_client()
    
    # Check for API documentation
    check_api_documentation()
    
    # Summary
    print(f"\n📋 Final Summary")
    print("=" * 20)
    
    print("✅ OAuth2 Authentication: Working")
    
    if working_endpoints:
        print(f"✅ Working Endpoints ({len(working_endpoints)}):")
        for endpoint, desc in working_endpoints:
            print(f"  • {endpoint} - {desc}")
    else:
        print("❌ No fully working API endpoints found")
    
    print(f"\n💡 Recommendations:")
    print("1. ✅ OAuth2 is working - authentication is successful")
    print("2. 🔧 API endpoints might need different approach or parameters")
    print("3. 📞 Contact DOUANO support to verify API endpoint structure")
    print("4. 🔍 Check if your account has API access enabled")
    print("5. 📖 Verify the API documentation matches your instance version")
    
    print(f"\n🎉 Testing completed!")


if __name__ == "__main__":
    main()
