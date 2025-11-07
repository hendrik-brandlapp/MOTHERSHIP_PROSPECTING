# 📦 Products & Pricing System - Complete Setup Guide

## 🎯 What This System Does

This comprehensive system syncs **products, categories, price lists, and company-specific pricing** from Douano to Supabase, allowing you to:

1. View all products with their prices across different price lists
2. See which price list each company uses
3. View company-specific discounts (standard, extra, financial)
4. Calculate final prices for any product for any company

---

## 🚀 Setup Steps

### Step 1: Create Supabase Tables

1. Open your **Supabase SQL Editor**
2. Run the SQL from `create_products_pricing_tables.sql`
3. This creates 6 tables:
   - `product_categories` - Categories like "Gin", "Tripel", "Fles", etc.
   - `products` - All your sellable products
   - `sales_price_lists` - Price lists like "RRP delivery", "Horeca volume", "Retail"
   - `product_prices` - Prices for each product in each price list
   - `company_pricing` - Which price list each company uses + their extra discounts
   - `composed_product_items` - Product recipes (for composed products)

### Step 2: Sync Data from Douano

Once tables are created, you have several sync options:

#### Option A: Full Sync (Recommended for first time)
```bash
# In your Flask app (at /api/sync-all-products)
POST /api/sync-all-products
```

This will sync **everything** in sequence:
1. Product categories
2. Products
3. Price lists
4. Product prices
5. Company pricing

#### Option B: Individual Syncs
You can also sync each part individually:

```bash
# Sync categories
POST /api/sync-product-categories

# Sync products
POST /api/sync-products

# Sync price lists
POST /api/sync-price-lists

# Sync product prices
POST /api/sync-product-prices

# Sync company pricing
POST /api/sync-company-pricing
```

---

## 📊 Database Schema

### Products Hierarchy

```
product_categories
  └── products
        ├── product_prices (prices in different price lists)
        └── composed_product_items (if it's a composed product)
```

### Company Pricing

```
companies
  └── company_pricing
        ├── price_list_id (which price list they use)
        ├── standard_discount_percentage
        ├── extra_discount_percentage
        └── financial_discount_percentage
```

---

## 💰 How Pricing Works

For each **company** buying a **product**:

1. **Base Price**: Get the product's price from the company's assigned price list
2. **Standard Discount**: Apply the company's standard discount %
3. **Extra Discount**: Apply the company's extra discount %
4. **Financial Discount**: Apply financial discount % (if paid early)

### Example Calculation

```
Product: "Gin Wit 70cl"
Company: "GUAPA BRAVO"

1. Company uses price list: "Horeca volume"
2. Product price in "Horeca volume": €52.44
3. Company's standard discount: 0%
4. Company's extra discount: 5%
5. Company's financial discount: 2%

Final price:
  = €52.44
  - (€52.44 × 0%) = €52.44
  - (€52.44 × 5%) = €49.82
  - (€49.82 × 2%) = €48.82
```

---

## 🔍 Useful Views

The migration also creates 3 helpful views:

### 1. `products_overview`
Shows all products with:
- Category name
- Number of price lists they're in
- Min, max, and average price across all lists

```sql
SELECT * FROM products_overview WHERE is_active = true;
```

### 2. `company_pricing_overview`
Shows all companies with:
- Their price list name
- All discount percentages
- Payment terms

```sql
SELECT * FROM company_pricing_overview WHERE company_name ILIKE '%bravo%';
```

### 3. `product_prices_detailed`
Shows all product-price-list combinations with full context

```sql
SELECT * FROM product_prices_detailed 
WHERE product_name ILIKE '%gin%' 
ORDER BY price DESC;
```

---

## 📡 API Endpoints

### Sync Endpoints (POST)

- `/api/sync-product-categories` - Sync categories from Douano
- `/api/sync-products` - Sync products from Douano
- `/api/sync-price-lists` - Sync price lists from Douano
- `/api/sync-product-prices` - Sync all product prices
- `/api/sync-company-pricing` - Sync company pricing settings
- `/api/sync-all-products` - Sync everything in sequence

### Query Endpoints (GET) - To Be Built

- `/api/products` - Get all products with optional filters
- `/api/products/:id` - Get product details
- `/api/products/:id/prices` - Get all prices for a product
- `/api/products/:id/price-for-company/:company_id` - Calculate final price
- `/api/price-lists` - Get all price lists
- `/api/company-pricing/:company_id` - Get company's pricing settings

---

## 🖼️ Frontend UI (To Build)

### Products Page Features:

1. **Product List View**
   - Filter by category
   - Search by name/SKU
   - Sort by name, price, category
   - Show product card with:
     - Name & SKU
     - Category
     - Price range across all lists
     - Number of price lists

2. **Product Detail View**
   - All product information
   - Prices in all price lists (table)
   - If composed: show recipe (components + quantities)
   - Calculate price for specific company

3. **Company Pricing View**
   - Select a company
   - See their price list
   - See all discounts
   - See final prices for all products

4. **Sync Controls**
   - Buttons to trigger each sync
   - Progress indicators
   - Sync status and timestamps

---

## 🎨 Example Queries

### Get all products in a specific category
```sql
SELECT p.*, pc.name as category_name
FROM products p
LEFT JOIN product_categories pc ON p.category_id = pc.id
WHERE pc.name = 'Gin'
ORDER BY p.name;
```

### Get all prices for a specific product
```sql
SELECT 
  p.name as product_name,
  spl.name as price_list_name,
  pp.price,
  pp.currency
FROM product_prices pp
LEFT JOIN products p ON pp.product_id = p.id
LEFT JOIN sales_price_lists spl ON pp.price_list_id = spl.id
WHERE p.id = 104  -- Gin Zwart 70cl
ORDER BY pp.price DESC;
```

### Get final prices for a company
```sql
SELECT 
  p.name as product,
  pp.price as base_price,
  cp.standard_discount_percentage,
  cp.extra_discount_percentage,
  pp.price * (1 - cp.standard_discount_percentage/100) * (1 - cp.extra_discount_percentage/100) as final_price
FROM products p
LEFT JOIN product_prices pp ON p.id = pp.product_id
LEFT JOIN company_pricing cp ON pp.price_list_id = cp.price_list_id
LEFT JOIN companies c ON cp.company_id = c.id
WHERE c.id = 123  -- Your company ID
ORDER BY p.name;
```

### Find products with biggest discounts
```sql
SELECT 
  p.name,
  spl.name as price_list,
  pp.price as base_price,
  cp.standard_discount_percentage + cp.extra_discount_percentage as total_discount,
  c.name as company
FROM product_prices pp
LEFT JOIN products p ON pp.product_id = p.id
LEFT JOIN sales_price_lists spl ON pp.price_list_id = spl.id
LEFT JOIN company_pricing cp ON spl.id = cp.price_list_id
LEFT JOIN companies c ON cp.company_id = c.id
WHERE cp.standard_discount_percentage + cp.extra_discount_percentage > 10
ORDER BY total_discount DESC;
```

---

## ✅ Testing Checklist

### After Running SQL Migration:

- [ ] Check tables exist in Supabase
- [ ] Verify RLS policies are active
- [ ] Verify views are created

### After First Sync:

- [ ] Product categories populated
- [ ] Products populated
- [ ] Price lists populated
- [ ] Product prices populated
- [ ] Company pricing populated

### Verification Queries:

```sql
-- Check sync counts
SELECT 'Categories' as table, COUNT(*) FROM product_categories
UNION ALL
SELECT 'Products', COUNT(*) FROM products
UNION ALL
SELECT 'Price Lists', COUNT(*) FROM sales_price_lists
UNION ALL
SELECT 'Product Prices', COUNT(*) FROM product_prices
UNION ALL
SELECT 'Company Pricing', COUNT(*) FROM company_pricing;

-- Check last sync times
SELECT 
  'Categories' as table, 
  MAX(last_sync_at) as last_synced
FROM product_categories
UNION ALL
SELECT 'Products', MAX(last_sync_at) FROM products
UNION ALL
SELECT 'Price Lists', MAX(last_sync_at) FROM sales_price_lists;
```

---

## 🔄 Regular Maintenance

### Recommended Sync Schedule:

- **Daily**: Sync product prices (prices may change)
- **Weekly**: Sync products and categories (new products)
- **Monthly**: Sync company pricing (discount changes)

You can set up automated syncs using cron jobs or scheduled tasks.

---

## 🎉 You're Ready!

The backend is complete. Now you just need to:

1. ✅ **Run the SQL migration** in Supabase
2. ✅ **Click "Sync All Products"** in your app
3. ✅ **Build the frontend UI** to display this data
4. ✅ **Create price calculation tools** for sales

**Everything you need to see products, prices, and company-specific discounts is now in place!** 🚀

