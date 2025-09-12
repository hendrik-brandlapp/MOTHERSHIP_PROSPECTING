# DUANO API Client - Quick Start Guide

## 🚀 Get Started in 3 Minutes

### 1. Setup
```bash
# Run the setup script
python setup.py

# Or manually install dependencies
pip install -r requirements.txt
```

### 2. Configure API Credentials
Edit the `.env` file with your DUANO API credentials:
```bash
DUANO_API_KEY=your_actual_api_key
DUANO_API_SECRET=your_actual_api_secret
DUANO_API_BASE_URL=https://api.duano.com
```

### 3. Test Your Setup
```bash
python examples.py
```

## 💡 Basic Usage

```python
from duano_client import create_client

# Create client
client = create_client()

# Test connection
if client.test_connection():
    print("✅ Connected!")
    
    # Get sales summary
    sales = client.sales.get_sales_summary()
    print(f"Total sales: ${sales['total_sales']}")
    
    # List recent orders
    orders = client.orders.list_orders(limit=5)
    print(f"Recent orders: {len(orders['data'])}")
    
    # List clients
    clients = client.clients.list_clients(limit=5)
    print(f"Total clients: {clients['total']}")
    
    # List products
    products = client.products.list_products(limit=5)
    print(f"Total products: {products['total']}")
else:
    print("❌ Connection failed - check your credentials")
```

## 📊 Common Use Cases

### Sales Dashboard
```python
# Get comprehensive sales data
sales_summary = client.sales.get_sales_summary()
monthly_trends = client.sales.get_sales_by_period('monthly')
top_products = client.sales.get_top_products(10)

print(f"Total Revenue: ${sales_summary['total_sales']}")
print(f"Total Orders: {sales_summary['total_orders']}")
```

### Order Management
```python
# Get pending orders
pending = client.orders.list_orders(status='pending')
print(f"Pending orders: {len(pending['data'])}")

# Process an order
order_id = pending['data'][0]['id']
client.orders.update_order(order_id, {'status': 'processing'})
```

### Client Analysis
```python
# Find high-value clients
clients = client.clients.list_clients(limit=100)
for client_data in clients['data']:
    if client_data.get('total_orders', 0) > 10:
        print(f"VIP Client: {client_data['name']} - {client_data['total_orders']} orders")
```

### Inventory Management
```python
# Check low stock products
products = client.products.list_products(limit=100)
for product in products['data']:
    if product.get('stock', 0) < 10:
        print(f"Low stock: {product['name']} - {product['stock']} remaining")
```

## 🛠️ Error Handling
```python
from duano_client import DuanoAPIError, AuthenticationError

try:
    data = client.sales.get_sales_summary()
except AuthenticationError:
    print("Invalid credentials")
except DuanoAPIError as e:
    print(f"API error: {e}")
```

## 📈 Next Steps

1. **Explore the full API** - Check `examples.py` for comprehensive usage
2. **Build your dashboard** - Combine data from all modules
3. **Automate workflows** - Create scripts for routine tasks
4. **Monitor performance** - Use the built-in logging and error handling

## 🔗 Key Files

- `duano_client.py` - Main client library
- `examples.py` - Comprehensive usage examples
- `config.py` - Configuration management
- `README.md` - Full documentation
- `.env` - Your API credentials (don't commit this!)

## 💬 Need Help?

- Check the error messages - they're designed to be helpful
- Enable debug mode: `client = create_client(debug=True)`
- Review the examples for common patterns
- Check DUANO's API documentation for endpoint details

Happy coding! 🎉
