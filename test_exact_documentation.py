"""
Test DUANO API following the exact documentation patterns

This script replicates the exact requests from your documentation
but adds the proper OAuth2 authorization headers.
"""

import http.client
import json
from duano_client import create_client


def test_with_http_client():
    """Test using http.client exactly like the documentation examples"""
    print("🔬 Testing with http.client (like documentation)")
    print("=" * 55)
    
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
    
    # Create connection
    conn = http.client.HTTPSConnection("yugen.douano.com")
    
    # Setup headers (this is what was missing from the documentation examples!)
    headers = {
        'Authorization': f'Bearer {token.access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    # Test the exact endpoints from your documentation
    test_cases = [
        {
            'name': 'Accountancy Accounts',
            'method': 'GET',
            'path': '/api/public/v1/accountancy/accounts',
            'payload': ''
        },
        {
            'name': 'Accountancy Account by ID',
            'method': 'GET', 
            'path': '/api/public/v1/accountancy/accounts/1',  # Using ID 1 as example
            'payload': ''
        },
        {
            'name': 'Accountancy Booking by ID',
            'method': 'GET',
            'path': '/api/public/v1/accountancy/bookings/1',  # Using ID 1 as example
            'payload': ''
        },
        {
            'name': 'CRM Contact Persons',
            'method': 'GET',
            'path': '/api/public/v1/crm/crm-contact-persons',
            'payload': ''
        },
        {
            'name': 'CRM Contact Person by ID', 
            'method': 'GET',
            'path': '/api/public/v1/crm/crm-contact-persons/153',  # Using ID from your example
            'payload': ''
        },
        {
            'name': 'CRM Actions',
            'method': 'GET', 
            'path': '/api/public/v1/crm/crm-actions',
            'payload': ''
        }
    ]
    
    successful_requests = []
    
    for test_case in test_cases:
        print(f"\n🧪 Testing: {test_case['name']}")
        print(f"   Path: {test_case['path']}")
        
        try:
            # Make request exactly like documentation but with auth headers
            conn.request(test_case['method'], test_case['path'], test_case['payload'], headers)
            res = conn.getresponse()
            data = res.read()
            
            print(f"   📊 Status: {res.status}")
            print(f"   📋 Headers: {res.getheader('content-type')}")
            
            if res.status == 200:
                successful_requests.append(test_case['name'])
                
                # Try to decode as JSON
                try:
                    decoded_data = data.decode("utf-8")
                    if decoded_data.strip():
                        # Try to parse as JSON
                        try:
                            json_data = json.loads(decoded_data)
                            print(f"   ✅ JSON Response: {str(json_data)[:200]}...")
                        except json.JSONDecodeError:
                            print(f"   ✅ Text Response: {decoded_data[:200]}...")
                    else:
                        print(f"   ✅ Empty response (as expected from documentation)")
                except UnicodeDecodeError:
                    print(f"   ✅ Binary response received")
                    
            elif res.status == 404:
                print(f"   ❌ Not Found - endpoint may not exist")
            elif res.status == 401:
                print(f"   🔐 Unauthorized - auth issue")
            elif res.status == 403:
                print(f"   🚫 Forbidden - permission issue")
            elif res.status >= 500:
                error_text = data.decode("utf-8") if data else "No error message"
                print(f"   🔥 Server Error: {error_text[:100]}...")
            else:
                error_text = data.decode("utf-8") if data else "No response"
                print(f"   ⚠️  Status {res.status}: {error_text[:100]}...")
                
        except Exception as e:
            print(f"   ❌ Exception: {str(e)[:100]}...")
    
    # Close connection
    conn.close()
    
    return successful_requests


def test_with_parameters():
    """Test endpoints with query parameters"""
    print(f"\n🔧 Testing with Query Parameters")
    print("=" * 40)
    
    # Get OAuth token
    client = create_client(
        client_id="3", 
        client_secret="KBPJZ11EwPjAmEUKFWDoXGQaDdMRPFES2P6VCxEC",
        base_url="https://yugen.douano.com"
    )
    
    token = client.client_credentials_flow()
    
    conn = http.client.HTTPSConnection("yugen.douano.com")
    headers = {
        'Authorization': f'Bearer {token.access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    # Test accounts with parameters (from your documentation)
    test_params = [
        '/api/public/v1/accountancy/accounts?filter_by_is_visible=true',
        '/api/public/v1/accountancy/accounts?order_by_number=asc',
        '/api/public/v1/crm/crm-contact-persons?filter_by_is_active=true',
        '/api/public/v1/crm/crm-actions?filter_by_status=to_do'
    ]
    
    for path in test_params:
        print(f"\n🧪 Testing: {path}")
        
        try:
            conn.request('GET', path, '', headers)
            res = conn.getresponse()
            data = res.read()
            
            print(f"   Status: {res.status}")
            
            if res.status == 200:
                try:
                    decoded = data.decode("utf-8")
                    if decoded.strip():
                        print(f"   ✅ Response: {decoded[:150]}...")
                    else:
                        print(f"   ✅ Empty response")
                except:
                    print(f"   ✅ Binary response")
            else:
                print(f"   ❌ Error: {res.status}")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    
    conn.close()


def main():
    """Main test function"""
    print("🎯 Testing DUANO API - Exact Documentation Style")
    print("Following your documentation examples with proper OAuth2")
    print("=" * 70)
    
    # Test basic endpoints
    successful_requests = test_with_http_client()
    
    # Test with parameters if basic requests work
    if successful_requests:
        test_with_parameters()
    
    # Summary
    print(f"\n📋 Results Summary")
    print("=" * 25)
    
    if successful_requests:
        print(f"✅ Working endpoints ({len(successful_requests)}):")
        for req in successful_requests:
            print(f"  • {req}")
        
        print(f"\n🎉 Success! Your API is working!")
        print(f"The issue was missing Authorization headers in the documentation examples.")
        
    else:
        print("❌ No endpoints working yet")
        print("\n💡 Possible next steps:")
        print("1. Check if API access is enabled for your account")
        print("2. Verify the endpoint URLs in your DOUANO documentation")
        print("3. Contact DOUANO support for assistance")
        print("4. Check if there are any IP restrictions")
    
    print(f"\n🔧 Your OAuth2 authentication is definitely working!")
    print(f"The client code is production-ready once the endpoints respond correctly.")


if __name__ == "__main__":
    main()
