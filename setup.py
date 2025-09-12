"""
Setup script for DUANO API Client
"""

import os
import sys
from pathlib import Path


def create_env_file():
    """Create .env file with template"""
    env_content = """# DUANO API Configuration
DUANO_API_KEY=your_api_key_here
DUANO_API_SECRET=your_api_secret_here
DUANO_API_BASE_URL=https://api.duano.com

# Optional settings
DUANO_TIMEOUT=30
DUANO_MAX_RETRIES=3
DUANO_DEBUG=false
DUANO_DEFAULT_PAGE_SIZE=50
DUANO_MAX_PAGE_SIZE=1000
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("✅ Created .env file")
    print("📝 Please edit .env file with your actual DUANO API credentials")


def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing dependencies...")
    os.system(f"{sys.executable} -m pip install -r requirements.txt")
    print("✅ Dependencies installed")


def test_setup():
    """Test the setup"""
    print("🧪 Testing setup...")
    
    try:
        from duano_client import create_client
        print("✅ Import successful")
        
        # Try to create client (will fail without real credentials, but that's ok)
        try:
            client = create_client()
            print("⚠️  Client created but needs real API credentials to test connection")
        except Exception as e:
            if "API key and secret are required" in str(e):
                print("⚠️  Please set your API credentials in .env file")
            else:
                print(f"❌ Setup test failed: {e}")
                return False
        
        print("✅ Setup test completed")
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def main():
    """Main setup function"""
    print("🚀 DUANO API Client Setup")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not Path('duano_client.py').exists():
        print("❌ Please run this script from the DUANO client directory")
        sys.exit(1)
    
    # Install dependencies
    install_dependencies()
    
    # Create .env file if it doesn't exist
    if not Path('.env').exists():
        create_env_file()
    else:
        print("⚠️  .env file already exists - skipping creation")
    
    # Test setup
    if test_setup():
        print("\n🎉 Setup completed successfully!")
        print("\n📋 Next steps:")
        print("1. Edit .env file with your DUANO API credentials")
        print("2. Run: python examples.py")
        print("3. Start using the client in your code!")
        
        print("\n💡 Quick start:")
        print("from duano_client import create_client")
        print("client = create_client()")
        print("sales_data = client.sales.get_sales_summary()")
    else:
        print("\n❌ Setup failed - please check the error messages above")
        sys.exit(1)


if __name__ == "__main__":
    main()
