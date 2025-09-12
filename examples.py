"""
Usage examples for DUANO API client

This file demonstrates how to use the DUANO client to interact with
all the different data types and endpoints.
"""

import os
from datetime import datetime, timedelta
from duano_client import create_client, DuanoAPIError


def setup_client():
    """Setup and return a DUANO client instance"""
    # Option 1: Use environment variables (OAuth2)
    client = create_client()
    
    # Option 2: Pass OAuth2 credentials directly
    # client = create_client(
    #     client_id="3",
    #     client_secret="KBPJZ11EwPjAmEUKFWDoXGQaDdMRPFES2P6VCxEC",
    #     base_url="https://api.duano.com",
    #     debug=True
    # )
    
    return client


def sales_examples():
    """Examples of working with sales data"""
    print("=== Sales Data Examples ===")
    
    client = setup_client()
    
    try:
        # Test connection first
        if not client.test_connection():
            print("❌ Connection test failed")
            return
        
        print("✅ Connected to DUANO API")
        
        # Get sales summary
        print("\n📊 Getting sales summary...")
        sales_summary = client.sales.get_sales_summary()
        print(f"Total sales: {sales_summary.get('total_sales', 'N/A')}")
        print(f"Total orders: {sales_summary.get('total_orders', 'N/A')}")
        
        # Get sales for specific date range
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        print(f"\n📅 Getting sales from {start_date} to {end_date}...")
        monthly_sales = client.sales.get_sales_summary(
            start_date=start_date,
            end_date=end_date
        )
        print(f"Monthly sales: {monthly_sales.get('total_sales', 'N/A')}")
        
        # Get sales by period
        print("\n📈 Getting monthly sales breakdown...")
        sales_by_month = client.sales.get_sales_by_period(period='monthly')
        for period in sales_by_month[:5]:  # Show first 5 months
            print(f"  {period.get('period')}: {period.get('sales', 'N/A')}")
        
        # Get top products
        print("\n🏆 Top 5 selling products...")
        top_products = client.sales.get_top_products(limit=5)
        for i, product in enumerate(top_products, 1):
            print(f"  {i}. {product.get('name', 'Unknown')} - {product.get('sales_count', 0)} sold")
    
    except DuanoAPIError as e:
        print(f"❌ Sales API error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def orders_examples():
    """Examples of working with orders"""
    print("\n=== Orders Management Examples ===")
    
    client = setup_client()
    
    try:
        # List recent orders
        print("\n📋 Listing recent orders...")
        orders = client.orders.list_orders(page=1, limit=10)
        print(f"Found {orders.get('total', 0)} total orders")
        
        for order in orders.get('data', [])[:5]:  # Show first 5
            print(f"  Order #{order.get('id')}: {order.get('status')} - ${order.get('total', 0)}")
        
        # Filter orders by status
        print("\n🔍 Getting pending orders...")
        pending_orders = client.orders.list_orders(status='pending', limit=5)
        print(f"Pending orders: {len(pending_orders.get('data', []))}")
        
        # Get specific order details
        if orders.get('data'):
            first_order = orders['data'][0]
            order_id = first_order.get('id')
            
            print(f"\n🔍 Getting details for order #{order_id}...")
            order_details = client.orders.get_order(order_id)
            print(f"Customer: {order_details.get('customer_name', 'N/A')}")
            print(f"Items: {len(order_details.get('items', []))}")
            print(f"Total: ${order_details.get('total', 0)}")
        
        # Create a new order example
        print("\n➕ Creating new order example...")
        new_order_data = {
            "customer_id": "customer_123",
            "items": [
                {
                    "product_id": "product_456",
                    "quantity": 2,
                    "price": 29.99
                }
            ],
            "shipping_address": {
                "street": "123 Main St",
                "city": "Anytown",
                "country": "US",
                "postal_code": "12345"
            }
        }
        
        # Uncomment to actually create an order
        # new_order = client.orders.create_order(new_order_data)
        # print(f"Created order: {new_order.get('id')}")
        print("(Order creation example - uncomment to execute)")
    
    except DuanoAPIError as e:
        print(f"❌ Orders API error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def clients_examples():
    """Examples of working with client data"""
    print("\n=== Client Management Examples ===")
    
    client = setup_client()
    
    try:
        # List clients
        print("\n👥 Listing clients...")
        clients = client.clients.list_clients(page=1, limit=10)
        print(f"Found {clients.get('total', 0)} total clients")
        
        for client_data in clients.get('data', [])[:5]:  # Show first 5
            print(f"  {client_data.get('name', 'N/A')} - {client_data.get('email', 'N/A')}")
        
        # Search for clients
        print("\n🔍 Searching for clients with 'john'...")
        search_results = client.clients.list_clients(search='john', limit=5)
        print(f"Found {len(search_results.get('data', []))} matching clients")
        
        # Get specific client details
        if clients.get('data'):
            first_client = clients['data'][0]
            client_id = first_client.get('id')
            
            print(f"\n🔍 Getting details for client {client_id}...")
            client_details = client.clients.get_client(client_id)
            print(f"Name: {client_details.get('name', 'N/A')}")
            print(f"Email: {client_details.get('email', 'N/A')}")
            print(f"Total orders: {client_details.get('total_orders', 0)}")
        
        # Create new client example
        print("\n➕ Creating new client example...")
        new_client_data = {
            "name": "Jane Smith",
            "email": "jane.smith@example.com",
            "phone": "+1-555-0123",
            "address": {
                "street": "456 Oak Ave",
                "city": "Somewhere",
                "country": "US",
                "postal_code": "67890"
            }
        }
        
        # Uncomment to actually create a client
        # new_client = client.clients.create_client(new_client_data)
        # print(f"Created client: {new_client.get('id')}")
        print("(Client creation example - uncomment to execute)")
    
    except DuanoAPIError as e:
        print(f"❌ Clients API error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def products_examples():
    """Examples of working with product data"""
    print("\n=== Product Management Examples ===")
    
    client = setup_client()
    
    try:
        # List products
        print("\n📦 Listing products...")
        products = client.products.list_products(page=1, limit=10)
        print(f"Found {products.get('total', 0)} total products")
        
        for product in products.get('data', [])[:5]:  # Show first 5
            print(f"  {product.get('name', 'N/A')} - ${product.get('price', 0)} (Stock: {product.get('stock', 0)})")
        
        # Filter products by category
        print("\n🏷️ Getting electronics products...")
        electronics = client.products.list_products(category='electronics', limit=5)
        print(f"Electronics products: {len(electronics.get('data', []))}")
        
        # Filter products in stock
        print("\n📈 Getting products in stock...")
        in_stock = client.products.list_products(in_stock=True, limit=5)
        print(f"Products in stock: {len(in_stock.get('data', []))}")
        
        # Get specific product details
        if products.get('data'):
            first_product = products['data'][0]
            product_id = first_product.get('id')
            
            print(f"\n🔍 Getting details for product {product_id}...")
            product_details = client.products.get_product(product_id)
            print(f"Name: {product_details.get('name', 'N/A')}")
            print(f"Price: ${product_details.get('price', 0)}")
            print(f"Category: {product_details.get('category', 'N/A')}")
            print(f"Stock: {product_details.get('stock', 0)}")
        
        # Create new product example
        print("\n➕ Creating new product example...")
        new_product_data = {
            "name": "Awesome Widget",
            "description": "The most amazing widget you'll ever use",
            "price": 49.99,
            "category": "widgets",
            "stock": 100,
            "sku": "AWG-001"
        }
        
        # Uncomment to actually create a product
        # new_product = client.products.create_product(new_product_data)
        # print(f"Created product: {new_product.get('id')}")
        print("(Product creation example - uncomment to execute)")
        
        # Update inventory example
        if products.get('data'):
            product_id = products['data'][0].get('id')
            print(f"\n📊 Updating inventory for product {product_id}...")
            
            # Uncomment to actually update inventory
            # updated_product = client.products.update_inventory(product_id, quantity=150)
            # print(f"Updated stock to: {updated_product.get('stock')}")
            print("(Inventory update example - uncomment to execute)")
    
    except DuanoAPIError as e:
        print(f"❌ Products API error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def comprehensive_dashboard_example():
    """Example of creating a comprehensive dashboard with data from all modules"""
    print("\n=== Comprehensive Dashboard Example ===")
    
    client = setup_client()
    
    try:
        print("🚀 Building comprehensive dashboard...")
        
        # Gather data from all modules
        dashboard_data = {}
        
        # Sales metrics
        print("  📊 Fetching sales metrics...")
        dashboard_data['sales'] = {
            'summary': client.sales.get_sales_summary(),
            'monthly_trend': client.sales.get_sales_by_period('monthly'),
            'top_products': client.sales.get_top_products(5)
        }
        
        # Orders overview
        print("  📋 Fetching orders overview...")
        dashboard_data['orders'] = {
            'recent': client.orders.list_orders(limit=10),
            'pending': client.orders.list_orders(status='pending', limit=5)
        }
        
        # Clients overview
        print("  👥 Fetching clients overview...")
        dashboard_data['clients'] = {
            'recent': client.clients.list_clients(limit=10),
            'total_count': client.clients.list_clients(limit=1).get('total', 0)
        }
        
        # Products overview
        print("  📦 Fetching products overview...")
        dashboard_data['products'] = {
            'all': client.products.list_products(limit=10),
            'low_stock': client.products.list_products(limit=5),  # You might want to add a low_stock filter
            'categories': {}  # You might want to fetch category breakdown
        }
        
        # Display dashboard summary
        print("\n📈 DASHBOARD SUMMARY")
        print("=" * 50)
        
        # Sales summary
        sales = dashboard_data['sales']['summary']
        print(f"💰 Total Sales: ${sales.get('total_sales', 'N/A')}")
        print(f"📦 Total Orders: {sales.get('total_orders', 'N/A')}")
        print(f"👥 Total Clients: {dashboard_data['clients']['total_count']}")
        print(f"🏷️  Total Products: {dashboard_data['products']['all'].get('total', 'N/A')}")
        
        # Recent activity
        print(f"\n📋 Recent Orders: {len(dashboard_data['orders']['recent'].get('data', []))}")
        print(f"⏳ Pending Orders: {len(dashboard_data['orders']['pending'].get('data', []))}")
        
        # Top products
        print("\n🏆 Top Products:")
        for i, product in enumerate(dashboard_data['sales']['top_products'][:3], 1):
            print(f"  {i}. {product.get('name', 'Unknown')} ({product.get('sales_count', 0)} sold)")
        
        print("\n✅ Dashboard data successfully compiled!")
        
    except DuanoAPIError as e:
        print(f"❌ Dashboard API error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def main():
    """Run all examples"""
    print("🚀 DUANO API Client Examples")
    print("=" * 50)
    
    # Check if we have OAuth2 credentials
    if not os.getenv('DUANO_CLIENT_ID') or not os.getenv('DUANO_CLIENT_SECRET'):
        print("⚠️  Warning: DUANO_CLIENT_ID and DUANO_CLIENT_SECRET environment variables not set")
        print("Using default credentials from the screenshot provided")
        print("\nTo use custom credentials, set these variables:")
        print("export DUANO_CLIENT_ID='your_client_id'")
        print("export DUANO_CLIENT_SECRET='your_client_secret'")
        print("export DUANO_API_BASE_URL='https://api.duano.com'")
        print("export DUANO_REDIRECT_URI='http://localhost:5001/oauth/callback'")
        print()
    
    # Run all examples
    sales_examples()
    orders_examples()
    clients_examples()
    products_examples()
    comprehensive_dashboard_example()
    
    print("\n🎉 All examples completed!")


if __name__ == "__main__":
    main()
