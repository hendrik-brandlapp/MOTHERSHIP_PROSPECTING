"""
Workaround DUANO Client

This version bypasses the problematic endpoints and provides
a foundation you can build on once the API issues are resolved.
"""

from duano_client import create_client
import requests
import json


class WorkaroundDuanoClient:
    """
    Workaround client that handles authentication and provides
    a foundation for when the API endpoints are fixed
    """
    
    def __init__(self):
        self.client = create_client()
        self.token = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate and store token"""
        try:
            self.token = self.client.client_credentials_flow()
            print(f"✅ Authenticated with Yugen DOUANO")
            return True
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            return False
    
    def make_custom_request(self, endpoint, method="GET", params=None, data=None):
        """
        Make a custom request to any endpoint
        Use this to test different endpoint patterns
        """
        if not self.token:
            raise Exception("Not authenticated")
        
        url = f"https://yugen.douano.com{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.token.access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=data,
                timeout=30
            )
            
            print(f"📡 {method} {endpoint}")
            print(f"   Status: {response.status_code}")
            print(f"   Content-Type: {response.headers.get('content-type', 'unknown')}")
            
            if response.status_code == 200:
                try:
                    return response.json()
                except:
                    return response.text
            else:
                print(f"   Error: {response.text[:200]}...")
                return None
                
        except Exception as e:
            print(f"   Exception: {e}")
            return None
    
    def test_endpoint_variations(self):
        """Test different endpoint variations to find what works"""
        print("\n🔍 Testing endpoint variations...")
        
        # Try different patterns for contact persons
        contact_variations = [
            "/api/v1/crm/contacts",
            "/api/v1/crm/contact-persons", 
            "/api/v1/crm/crm-contact-persons",
            "/api/crm/contacts",
            "/api/crm/contact-persons",
            "/crm/contacts",
            "/crm/contact-persons",
        ]
        
        for endpoint in contact_variations:
            result = self.make_custom_request(endpoint)
            if result:
                print(f"✅ Working endpoint found: {endpoint}")
                return endpoint
        
        print("❌ No working contact endpoints found")
        return None
    
    def get_token_info(self):
        """Get information about the current token"""
        if not self.token:
            return None
        
        return {
            'access_token': f"{self.token.access_token[:30]}...",
            'token_type': self.token.token_type,
            'expires_in': self.token.expires_in,
            'expires_at': self.token.expires_at.isoformat(),
            'is_expired': self.token.is_expired
        }


def main():
    """Demonstrate the workaround client"""
    print("🛠️ DUANO Workaround Client")
    print("=" * 35)
    
    # Create workaround client
    client = WorkaroundDuanoClient()
    
    # Show token info
    token_info = client.get_token_info()
    if token_info:
        print(f"\n🎫 Token Info:")
        for key, value in token_info.items():
            print(f"   {key}: {value}")
    
    # Test endpoint variations
    client.test_endpoint_variations()
    
    # You can test custom endpoints like this:
    print(f"\n🧪 Testing custom endpoints...")
    
    # Try some custom endpoint patterns
    custom_endpoints = [
        "/api/health",
        "/api/status", 
        "/api/user",
        "/api/me",
    ]
    
    for endpoint in custom_endpoints:
        result = client.make_custom_request(endpoint)
        if result:
            print(f"✅ {endpoint} returned data")
    
    print(f"\n💡 Use client.make_custom_request() to test any endpoint!")
    print(f"Example: client.make_custom_request('/your/custom/endpoint')")


if __name__ == "__main__":
    main()
