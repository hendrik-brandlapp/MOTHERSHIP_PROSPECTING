"""
Test DOUANO Core/Company Endpoints

Let's try the company-related endpoints which might be working
while CRM/Accountancy endpoints have server issues.
"""

import requests
import json
from duano_client import create_client


def test_company_endpoints():
    """Test the Core/Company endpoints from the documentation"""
    print("🏢 Testing DOUANO Core/Company Endpoints")
    print("=" * 50)
    
    # Get OAuth token
    client = create_client(
        client_id="3",
        client_secret="KBPJZ11EwPjAmEUKFWDoXGQaDdMRPFES2P6VCxEC",
        base_url="https://yugen.douano.com"
    )
    
    token = client.client_credentials_flow()
    print(f"✅ Token obtained: {token.access_token[:30]}...")
    
    headers = {
        'Authorization': f'Bearer {token.access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'DUANO-Python-Client/1.0'
    }
    
    # Test company category endpoints
    company_endpoints = [
        {
            'name': 'Company Categories',
            'url': '/api/public/v1/core/company-categories',
            'description': 'Get all company categories'
        },
        {
            'name': 'Company Category by ID',
            'url': '/api/public/v1/core/company-categories/1',
            'description': 'Get specific company category'
        },
        {
            'name': 'Company Statuses',
            'url': '/api/public/v1/core/company-statuses',
            'description': 'Get all company statuses'
        },
        {
            'name': 'Company Status by ID',
            'url': '/api/public/v1/core/company-statuses/10',
            'description': 'Get specific company status'
        }
    ]
    
    successful_endpoints = []
    
    for endpoint in company_endpoints:
        print(f"\n🧪 Testing: {endpoint['name']}")
        print(f"   URL: {endpoint['url']}")
        print(f"   Description: {endpoint['description']}")
        
        try:
            response = requests.get(
                f"https://yugen.douano.com{endpoint['url']}",
                headers=headers,
                timeout=15
            )
            
            print(f"   📊 Status: {response.status_code}")
            print(f"   📋 Content-Type: {response.headers.get('content-type', 'unknown')}")
            
            if response.status_code == 200:
                print(f"   ✅ SUCCESS!")
                
                try:
                    data = response.json()
                    print(f"   📊 Response type: {type(data)}")
                    
                    if isinstance(data, dict):
                        print(f"   🔑 Keys: {list(data.keys())}")
                        
                        if 'result' in data:
                            result = data['result']
                            print(f"   📋 Result type: {type(result)}")
                            
                            if isinstance(result, dict):
                                if 'data' in result:
                                    items = result['data']
                                    print(f"   📊 Data items: {len(items)}")
                                    
                                    # Show first item details
                                    if items and len(items) > 0:
                                        first_item = items[0]
                                        print(f"   🔍 First item: {first_item}")
                                else:
                                    # Single item result
                                    print(f"   🔍 Single result: {result}")
                            elif isinstance(result, list):
                                print(f"   📊 List with {len(result)} items")
                    
                    successful_endpoints.append(endpoint)
                    
                except json.JSONDecodeError as e:
                    print(f"   ❌ JSON decode error: {e}")
                    print(f"   📄 Raw response: {response.text[:200]}...")
                    
            elif response.status_code == 404:
                print(f"   ❌ Not Found - endpoint doesn't exist")
            elif response.status_code == 401:
                print(f"   🔐 Unauthorized - auth issue")
            elif response.status_code == 403:
                print(f"   🚫 Forbidden - permission issue")
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
    
    return successful_endpoints


def test_company_endpoints_with_parameters():
    """Test company endpoints with query parameters"""
    print(f"\n🔧 Testing Company Endpoints with Parameters")
    print("=" * 50)
    
    client = create_client()
    token = client.client_credentials_flow()
    
    headers = {
        'Authorization': f'Bearer {token.access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    # Test with different parameter combinations from the documentation
    test_cases = [
        {
            'endpoint': '/api/public/v1/core/company-categories',
            'params': {},
            'description': 'No parameters'
        },
        {
            'endpoint': '/api/public/v1/core/company-categories',
            'params': {'filter_by_is_active': 'true'},
            'description': 'Filter active only'
        },
        {
            'endpoint': '/api/public/v1/core/company-categories',
            'params': {'order_by_name': 'asc'},
            'description': 'Order by name ascending'
        },
        {
            'endpoint': '/api/public/v1/core/company-categories',
            'params': {'order_by_name': 'desc'},
            'description': 'Order by name descending'
        },
        {
            'endpoint': '/api/public/v1/core/company-categories',
            'params': {
                'filter_by_created_since': '2023-01-01',
                'filter_by_is_active': 'true',
                'order_by_name': 'asc'
            },
            'description': 'Multiple filters'
        }
    ]
    
    for test_case in test_cases:
        print(f"\n🧪 Testing: {test_case['endpoint']}")
        print(f"   Description: {test_case['description']}")
        print(f"   Parameters: {test_case['params']}")
        
        try:
            response = requests.get(
                f"https://yugen.douano.com{test_case['endpoint']}",
                headers=headers,
                params=test_case['params'],
                timeout=15
            )
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"   ✅ SUCCESS with parameters!")
                try:
                    data = response.json()
                    if 'result' in data and 'data' in data['result']:
                        items = data['result']['data']
                        print(f"   📊 Returned {len(items)} items")
                        
                        # Show first item
                        if items:
                            print(f"   🔍 First item: {items[0]['name']} (ID: {items[0]['id']})")
                except:
                    print(f"   📄 Non-JSON response")
            else:
                print(f"   ❌ Status: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:100]}...")


def update_client_with_working_endpoints(successful_endpoints):
    """Update our client to include the working Core endpoints"""
    if not successful_endpoints:
        print("❌ No working endpoints to add to client")
        return
    
    print(f"\n🔧 Updating Client with Working Endpoints")
    print("=" * 45)
    
    print("✅ Found working endpoints:")
    for endpoint in successful_endpoints:
        print(f"  • {endpoint['name']}: {endpoint['url']}")
    
    # Create a simple Core module addition
    core_module_code = '''
class CoreModule(BaseModule):
    """Module for handling Core/Company data"""
    
    def get_company_categories(
        self,
        filter_by_created_since: str = None,
        filter_by_updated_since: str = None,
        filter_by_is_active: bool = None,
        order_by_name: str = None,
        order_by_description: str = None,
        **kwargs
    ) -> Dict:
        """
        Get company categories
        
        Args:
            filter_by_created_since: Filter by creation date (YYYY-MM-DD)
            filter_by_updated_since: Filter by update date (YYYY-MM-DD)
            filter_by_is_active: Filter by active status
            order_by_name: Order by name (asc/desc)
            order_by_description: Order by description (asc/desc)
            **kwargs: Additional filter parameters
            
        Returns:
            Company categories data
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
        if order_by_description:
            params['order_by_description'] = order_by_description
        
        # Add any additional parameters
        params.update(kwargs)
        
        response = self.client.get('/api/public/v1/core/company-categories', params=params)
        return self._handle_response(response, "Failed to fetch company categories")
    
    def get_company_category(self, category_id: int) -> Dict:
        """
        Get specific company category by ID
        
        Args:
            category_id: Company category ID
            
        Returns:
            Company category data
        """
        response = self.client.get(f'/api/public/v1/core/company-categories/{category_id}')
        return self._handle_response(response, f"Failed to fetch company category {category_id}")
    
    def get_company_statuses(self, **kwargs) -> Dict:
        """Get company statuses"""
        params = kwargs
        response = self.client.get('/api/public/v1/core/company-statuses', params=params)
        return self._handle_response(response, "Failed to fetch company statuses")
    
    def get_company_status(self, status_id: int) -> Dict:
        """Get specific company status by ID"""
        response = self.client.get(f'/api/public/v1/core/company-statuses/{status_id}')
        return self._handle_response(response, f"Failed to fetch company status {status_id}")
'''
    
    print(f"\n📋 Core Module Code Generated:")
    print("Add this to your duano_client.py:")
    print(core_module_code)
    
    print(f"\nAnd add this to the DuanoClient __init__ method:")
    print("self.core = CoreModule(self)")


def main():
    """Main test function for company endpoints"""
    print("🏢 DOUANO Company Endpoints Test")
    print("Testing Core/Company endpoints that might work")
    print("=" * 60)
    
    # Test basic company endpoints
    successful_endpoints = test_company_endpoints()
    
    # If we found working endpoints, test with parameters
    if successful_endpoints:
        test_company_endpoints_with_parameters()
        update_client_with_working_endpoints(successful_endpoints)
    
    # Summary
    print(f"\n📋 Company Endpoints Summary")
    print("=" * 35)
    
    if successful_endpoints:
        print(f"🎉 SUCCESS! Found {len(successful_endpoints)} working endpoints!")
        print("✅ OAuth2 authentication working")
        print("✅ Core/Company API endpoints working") 
        print("🔧 Ready to add Core module to your client")
        
        print(f"\n🎯 Next Steps:")
        print("1. Add CoreModule to your duano_client.py")
        print("2. Test other Core endpoints (users, settings, etc.)")
        print("3. Contact DOUANO about CRM/Accountancy endpoint issues")
        
    else:
        print("❌ Company endpoints also not working")
        print("📞 Definitely need DOUANO support assistance")
    
    print(f"\n🏆 Your OAuth2 implementation is perfect!")


if __name__ == "__main__":
    main()
