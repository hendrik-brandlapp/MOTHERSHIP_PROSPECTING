"""
Investigate the working endpoint we found

We found that /crm/contacts returns 200, let's see what it actually contains
and if we can find the correct API structure from there.
"""

import requests
import json
from duano_client import create_client


def investigate_crm_endpoint():
    """Investigate the /crm/contacts endpoint that returned 200"""
    print("🔍 Investigating Working CRM Endpoint")
    print("=" * 45)
    
    client = create_client()
    token = client.client_credentials_flow()
    
    headers = {
        'Authorization': f'Bearer {token.access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'DUANO-Python-Client/1.0'
    }
    
    endpoint = "/crm/contacts"
    url = f"https://yugen.douano.com{endpoint}"
    
    print(f"🧪 Detailed investigation of: {endpoint}")
    print(f"URL: {url}")
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📋 Content-Type: {response.headers.get('content-type', 'unknown')}")
        print(f"📏 Content-Length: {response.headers.get('content-length', 'unknown')}")
        
        # Check if it's actually an API endpoint or a web page
        content_type = response.headers.get('content-type', '').lower()
        
        if 'application/json' in content_type:
            try:
                data = response.json()
                print(f"✅ JSON Response received!")
                print(f"📊 Data structure: {type(data)}")
                
                if isinstance(data, dict):
                    print(f"🔑 Keys: {list(data.keys())}")
                elif isinstance(data, list):
                    print(f"📋 List with {len(data)} items")
                
                print(f"📄 Full response: {json.dumps(data, indent=2)}")
                return data
                
            except json.JSONDecodeError as e:
                print(f"❌ JSON decode error: {e}")
                print(f"📄 Raw response: {response.text[:500]}...")
                
        elif 'text/html' in content_type:
            print(f"🌐 HTML response (probably web interface)")
            
            # Check if it contains any API-related information
            html_content = response.text.lower()
            
            if 'api' in html_content:
                print(f"🔍 Contains 'api' references")
            if 'json' in html_content:
                print(f"🔍 Contains 'json' references")
            if 'contact' in html_content:
                print(f"🔍 Contains 'contact' references")
            
            # Look for any embedded JSON or API endpoints
            if '{' in response.text and '}' in response.text:
                print(f"🔍 Contains JSON-like structures")
                
                # Try to extract JSON from HTML
                start = response.text.find('{')
                end = response.text.rfind('}') + 1
                if start != -1 and end != 0:
                    potential_json = response.text[start:end]
                    try:
                        data = json.loads(potential_json)
                        print(f"✅ Found embedded JSON!")
                        print(f"📊 Data: {json.dumps(data, indent=2)[:500]}...")
                        return data
                    except:
                        print(f"❌ Could not parse embedded JSON")
            
            print(f"📄 HTML preview: {response.text[:300]}...")
        else:
            print(f"📄 Other content type: {response.text[:200]}...")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return None


def test_alternative_api_paths():
    """Test alternative API paths based on what we learned"""
    print(f"\n🔍 Testing Alternative API Paths")
    print("=" * 40)
    
    client = create_client()
    token = client.client_credentials_flow()
    
    headers = {
        'Authorization': f'Bearer {token.access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    # Test paths without /api/public/v1 prefix
    alternative_paths = [
        "/crm/contacts",
        "/crm/contact-persons", 
        "/crm/crm-contact-persons",
        "/crm/actions",
        "/crm/crm-actions",
        "/accountancy/accounts",
        "/accountancy/bookings",
        
        # Try with /api prefix but different structure
        "/api/crm/contacts",
        "/api/crm/contact-persons",
        "/api/accountancy/accounts",
        
        # Try different version paths
        "/v1/crm/contacts",
        "/v1/crm/contact-persons",
        "/v1/accountancy/accounts",
    ]
    
    working_endpoints = []
    
    for path in alternative_paths:
        url = f"https://yugen.douano.com{path}"
        print(f"\n🧪 Testing: {path}")
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '').lower()
                
                if 'application/json' in content_type:
                    print(f"   ✅ JSON API endpoint found!")
                    try:
                        data = response.json()
                        print(f"   📊 Data: {str(data)[:100]}...")
                        working_endpoints.append(path)
                    except:
                        print(f"   ⚠️  Invalid JSON")
                else:
                    print(f"   🌐 HTML response (web interface)")
                    
            elif response.status_code == 404:
                print(f"   ❌ Not found")
            elif response.status_code == 500:
                print(f"   🔥 Server error")
            else:
                print(f"   ⚠️  Status: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:50]}...")
    
    return working_endpoints


def test_with_different_accept_headers():
    """Test if different Accept headers make a difference"""
    print(f"\n🔧 Testing Different Accept Headers")
    print("=" * 42)
    
    client = create_client()
    token = client.client_credentials_flow()
    
    base_headers = {
        'Authorization': f'Bearer {token.access_token}',
        'Content-Type': 'application/json',
        'User-Agent': 'DUANO-Python-Client/1.0'
    }
    
    accept_headers = [
        'application/json',
        'application/json, text/plain, */*',
        '*/*',
        'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'application/vnd.api+json',
        'application/hal+json'
    ]
    
    endpoint = "/api/public/v1/crm/crm-contact-persons"
    
    for accept_header in accept_headers:
        headers = base_headers.copy()
        headers['Accept'] = accept_header
        
        print(f"\n🧪 Testing Accept: {accept_header}")
        
        try:
            response = requests.get(
                f"https://yugen.douano.com{endpoint}",
                headers=headers,
                timeout=10
            )
            
            print(f"   Status: {response.status_code}")
            print(f"   Content-Type: {response.headers.get('content-type', 'unknown')}")
            
            if response.status_code == 200:
                print(f"   ✅ SUCCESS with Accept: {accept_header}")
                try:
                    data = response.json()
                    print(f"   📊 Data: {str(data)[:100]}...")
                    return accept_header
                except:
                    print(f"   📄 Non-JSON response")
            elif response.status_code != 500:
                print(f"   ⚠️  Different status code!")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:50]}...")
    
    return None


def main():
    """Main investigation function"""
    print("🕵️ DOUANO API Deep Investigation")
    print("Let's figure out the correct API structure!")
    print("=" * 60)
    
    # Investigate the working endpoint
    data = investigate_crm_endpoint()
    
    # Test alternative paths
    working_endpoints = test_alternative_api_paths()
    
    if working_endpoints:
        print(f"\n✅ Found working JSON endpoints:")
        for endpoint in working_endpoints:
            print(f"  • {endpoint}")
    
    # Test different headers
    working_accept = test_with_different_accept_headers()
    
    if working_accept:
        print(f"\n✅ Found working Accept header: {working_accept}")
    
    print(f"\n🎯 Investigation Summary")
    print("=" * 30)
    
    if working_endpoints:
        print("✅ Found working API endpoints!")
        print("🔧 Update client to use these endpoints")
    elif data:
        print("✅ Found data in working endpoint")
        print("🔧 Need to adjust endpoint structure")
    else:
        print("⚠️  Still investigating...")
        print("💡 May need to contact DOUANO for correct API structure")


if __name__ == "__main__":
    main()
