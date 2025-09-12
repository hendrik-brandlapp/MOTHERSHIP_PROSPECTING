#!/usr/bin/env python3
"""
Debug Company Categories
Let's see exactly what the API is returning
"""

from duano_client import create_client
import json

def test_company_categories():
    """Test company categories with different parameters"""
    print("🔍 Debugging Company Categories API")
    print("=" * 50)
    
    # Create client and authenticate
    client = create_client()
    
    try:
        # Test client credentials flow
        print("🔐 Authenticating...")
        token = client.client_credentials_flow()
        print(f"✅ Token obtained: {token.access_token[:30]}...")
        
        # Test different parameter combinations
        test_cases = [
            {"name": "No parameters", "params": {}},
            {"name": "With per_page=100", "params": {"per_page": 100}},
            {"name": "With per_page=100, page=1", "params": {"per_page": 100, "page": 1}},
            {"name": "With per_page=50", "params": {"per_page": 50}},
            {"name": "With limit=100", "params": {"limit": 100}},
            {"name": "With size=100", "params": {"size": 100}},
        ]
        
        for test_case in test_cases:
            print(f"\n🧪 Testing: {test_case['name']}")
            print(f"   Parameters: {test_case['params']}")
            
            try:
                # Make direct API call
                response = client.session.get(
                    f"{client.base_url}/api/public/v1/core/company-categories",
                    headers={'Authorization': f'Bearer {token.access_token}'},
                    params=test_case['params'],
                    timeout=15
                )
                
                print(f"   Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"   Response type: {type(data)}")
                    print(f"   Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                    
                    if isinstance(data, dict):
                        if 'result' in data:
                            result = data['result']
                            print(f"   Result type: {type(result)}")
                            
                            if isinstance(result, dict):
                                print(f"   Result keys: {list(result.keys())}")
                                if 'data' in result:
                                    items = result['data']
                                    print(f"   📊 Items count: {len(items)}")
                                    print(f"   Total: {result.get('total', 'Not specified')}")
                                    print(f"   Current page: {result.get('current_page', 'Not specified')}")
                                    print(f"   Last page: {result.get('last_page', 'Not specified')}")
                                    print(f"   Per page: {result.get('per_page', 'Not specified')}")
                                    
                                    # Show first few items
                                    if items:
                                        print(f"   📋 First 3 items:")
                                        for i, item in enumerate(items[:3]):
                                            print(f"      {i+1}. {item.get('name', 'No name')} (ID: {item.get('id')})")
                                    
                                    if len(items) >= 21:
                                        print(f"   🎉 SUCCESS! Found all {len(items)} company categories!")
                                        return True
                                    else:
                                        print(f"   ⚠️  Only {len(items)} items returned")
                                        
                            elif isinstance(result, list):
                                print(f"   📊 Direct list with {len(result)} items")
                                if len(result) >= 21:
                                    print(f"   🎉 SUCCESS! Found all {len(result)} company categories!")
                                    return True
                        else:
                            print(f"   📄 No 'result' key in response")
                            print(f"   Raw data preview: {str(data)[:200]}...")
                else:
                    print(f"   ❌ Error: {response.status_code}")
                    print(f"   Response: {response.text[:200]}...")
                    
            except Exception as e:
                print(f"   ❌ Exception: {str(e)}")
        
        print(f"\n💡 None of the test cases returned all 21 company categories")
        print(f"   This suggests the API might have server-side pagination limits")
        
        return False
        
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return False


if __name__ == "__main__":
    test_company_categories()
