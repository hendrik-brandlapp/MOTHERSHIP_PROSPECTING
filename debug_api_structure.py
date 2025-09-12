"""
Debug DOUANO API Structure

Let's systematically figure out what we're doing wrong with the API calls.
We know OAuth2 works, so the issue must be in our endpoint structure or parameters.
"""

import requests
import json
from duano_client import create_client


def test_different_api_structures():
    """Test different API endpoint structures"""
    print("🔍 Debugging API Endpoint Structure")
    print("=" * 50)
    
    # Get valid token
    client = create_client(
        client_id="3",
        client_secret="KBPJZ11EwPjAmEUKFWDoXGQaDdMRPFES2P6VCxEC", 
        base_url="https://yugen.douano.com"
    )
    
    token = client.client_credentials_flow()
    print(f"✅ Got token: {token.access_token[:30]}...")
    
    headers = {
        'Authorization': f'Bearer {token.access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'DUANO-Python-Client/1.0'
    }
    
    # Test different base paths
    base_paths = [
        "/api/v1",
        "/api/public", 
        "/api/public/v1",
        "/api/v2",
        "/api/public/v2",
        "/v1",
        "/public/v1"
    ]
    
    print(f"\n🧪 Testing different base API paths...")
    
    for base_path in base_paths:
        url = f"https://yugen.douano.com{base_path}"
        print(f"\n🔍 Testing: {base_path}")
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"   ✅ Working base path found!")
                try:
                    data = response.json()
                    print(f"   📊 Response: {str(data)[:200]}...")
                except:
                    print(f"   📄 Text: {response.text[:200]}...")
            elif response.status_code == 404:
                print(f"   ❌ Not found")
            elif response.status_code == 401:
                print(f"   🔐 Unauthorized")
            elif response.status_code == 403:
                print(f"   🚫 Forbidden")
            else:
                print(f"   ⚠️  Status: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:100]}...")


def test_endpoint_variations():
    """Test different endpoint naming conventions"""
    print(f"\n📋 Testing Endpoint Naming Variations")
    print("=" * 45)
    
    client = create_client()
    token = client.client_credentials_flow()
    
    headers = {
        'Authorization': f'Bearer {token.access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    # Test different CRM endpoint variations
    crm_endpoints = [
        "/api/public/v1/crm",
        "/api/public/v1/crm/",
        "/api/public/v1/crm/contacts",
        "/api/public/v1/crm/contact-persons",
        "/api/public/v1/crm/crm-contact-persons",
        "/api/public/v1/crm/contactpersons",
        "/api/public/v1/crm/contact_persons",
        "/api/public/v1/contacts",
        "/api/public/v1/contact-persons",
        "/api/v1/crm/contacts",
        "/api/v1/crm/contact-persons",
        "/api/crm/contacts",
        "/crm/contacts"
    ]
    
    print(f"🧪 Testing CRM endpoint variations...")
    
    for endpoint in crm_endpoints:
        url = f"https://yugen.douano.com{endpoint}"
        print(f"\n🔍 {endpoint}")
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"   ✅ SUCCESS! Working endpoint found!")
                try:
                    data = response.json()
                    print(f"   📊 Data: {str(data)[:200]}...")
                    return endpoint  # Return first working endpoint
                except:
                    print(f"   📄 Text response")
            elif response.status_code == 500:
                print(f"   🔥 Server error")
            elif response.status_code == 404:
                print(f"   ❌ Not found")
            else:
                print(f"   ⚠️  Status: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:50]}...")
    
    return None


def test_with_required_parameters():
    """Test if endpoints require specific parameters"""
    print(f"\n🔧 Testing with Required Parameters")
    print("=" * 40)
    
    client = create_client()
    token = client.client_credentials_flow()
    
    headers = {
        'Authorization': f'Bearer {token.access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    # Test with different parameter combinations
    test_cases = [
        {
            'endpoint': '/api/public/v1/crm/crm-contact-persons',
            'params': {}
        },
        {
            'endpoint': '/api/public/v1/crm/crm-contact-persons',
            'params': {'page': 1}
        },
        {
            'endpoint': '/api/public/v1/crm/crm-contact-persons',
            'params': {'page': 1, 'per_page': 10}
        },
        {
            'endpoint': '/api/public/v1/crm/crm-contact-persons',
            'params': {'limit': 10}
        },
        {
            'endpoint': '/api/public/v1/crm/crm-contact-persons',
            'params': {'filter_by_is_active': 'true'}
        }
    ]
    
    for test_case in test_cases:
        endpoint = test_case['endpoint']
        params = test_case['params']
        
        print(f"\n🧪 Testing: {endpoint}")
        print(f"   Params: {params}")
        
        try:
            response = requests.get(
                f"https://yugen.douano.com{endpoint}",
                headers=headers,
                params=params,
                timeout=15
            )
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"   ✅ SUCCESS with params: {params}")
                try:
                    data = response.json()
                    print(f"   📊 Data: {str(data)[:200]}...")
                    return True
                except:
                    print(f"   📄 Non-JSON response")
            elif response.status_code == 500:
                print(f"   🔥 Still getting server error")
            else:
                print(f"   ⚠️  Status: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:100]}...")
    
    return False


def test_different_http_methods():
    """Test if endpoints require different HTTP methods"""
    print(f"\n🌐 Testing Different HTTP Methods")
    print("=" * 40)
    
    client = create_client()
    token = client.client_credentials_flow()
    
    headers = {
        'Authorization': f'Bearer {token.access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    endpoint = "/api/public/v1/crm/crm-contact-persons"
    methods = ['GET', 'POST', 'PUT', 'HEAD', 'OPTIONS']
    
    for method in methods:
        print(f"\n🧪 Testing {method} {endpoint}")
        
        try:
            response = requests.request(
                method=method,
                url=f"https://yugen.douano.com{endpoint}",
                headers=headers,
                timeout=10
            )
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"   ✅ SUCCESS with {method}!")
                if method == 'GET':
                    try:
                        data = response.json()
                        print(f"   📊 Data: {str(data)[:200]}...")
                    except:
                        print(f"   📄 Non-JSON response")
                return method
            elif response.status_code == 405:
                print(f"   ❌ Method not allowed")
            elif response.status_code == 500:
                print(f"   🔥 Server error")
            else:
                print(f"   ⚠️  Status: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:50]}...")
    
    return None


def main():
    """Main debugging function"""
    print("🐛 DOUANO API Debugging Session")
    print("Let's find out what we're doing wrong!")
    print("=" * 60)
    
    # Test 1: Different API structures
    test_different_api_structures()
    
    # Test 2: Endpoint variations
    working_endpoint = test_endpoint_variations()
    
    if working_endpoint:
        print(f"\n🎉 Found working endpoint: {working_endpoint}")
    else:
        # Test 3: Required parameters
        if test_with_required_parameters():
            print(f"\n🎉 Found working parameter combination!")
        else:
            # Test 4: Different HTTP methods
            working_method = test_different_http_methods()
            
            if working_method:
                print(f"\n🎉 Found working HTTP method: {working_method}")
    
    print(f"\n🎯 Debugging Summary")
    print("=" * 25)
    print("✅ OAuth2 authentication is working")
    print("✅ We have valid access tokens")
    print("🔍 Need to find the correct API structure")
    
    print(f"\n💡 Next steps:")
    print("1. Try the working endpoints we found")
    print("2. Check DOUANO documentation for exact parameter requirements")
    print("3. Look for API versioning or different base paths")
    print("4. Check if there are required headers we're missing")


if __name__ == "__main__":
    main()
