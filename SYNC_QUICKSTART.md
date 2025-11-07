# 🚀 Products & Pricing Sync - Quick Start

## ✅ Setup Complete!

All the backend and frontend is ready. Follow these 3 steps:

---

## Step 1: Run the SQL Migration

1. Open **Supabase SQL Editor**
2. Copy all SQL from `create_products_pricing_tables.sql`
3. Click **Run**
4. ✅ This creates 6 tables + 3 views

---

## Step 2: Navigate to Products Page

In your browser, go to: **http://localhost:5002/products**

Or click **"Products"** in your navigation menu.

---

## Step 3: Click "Sync All"

You'll see a blue card at the top with sync buttons:

```
┌────────────────────────────────────────────────────┐
│ 📥 Sync from Douano                                │
├────────────────────────────────────────────────────┤
│                                                     │
│ [Categories] [Products] [Price Lists] [Prices]     │
│                                                     │
│ [Co. Pricing] [✅ Sync All]                        │
│                                                     │
└────────────────────────────────────────────────────┘
```

**Click the green "Sync All" button** to sync everything at once!

---

## What Gets Synced:

1. **📚 Product Categories** - Gin, Tripel, Fles, etc.
2. **📦 Products** - All your sellable products
3. **💰 Price Lists** - RRP delivery, Horeca volume, Retail, etc.
4. **💵 Product Prices** - Prices for each product in each price list
5. **🏢 Company Pricing** - Which price list each company uses + their discounts

---

## What Happens:

1. You click "Sync All"
2. Progress bar shows
3. Backend syncs from Douano → Supabase
4. Success message shows with counts
5. Done!

---

## Check Your Data:

After sync, run in Supabase SQL Editor:

```sql
-- Check what was synced
SELECT 
  'Categories' as table, COUNT(*) as count FROM product_categories
UNION ALL
SELECT 'Products', COUNT(*) FROM products
UNION ALL
SELECT 'Price Lists', COUNT(*) FROM sales_price_lists
UNION ALL
SELECT 'Product Prices', COUNT(*) FROM product_prices
UNION ALL
SELECT 'Company Pricing', COUNT(*) FROM company_pricing;
```

---

## Example Queries:

### Get all products with prices
```sql
SELECT * FROM products_overview;
```

### Get company pricing
```sql
SELECT * FROM company_pricing_overview 
WHERE company_name ILIKE '%bravo%';
```

### Calculate final price for a company
```sql
SELECT 
  p.name as product,
  pp.price as base_price,
  cp.extra_discount_percentage,
  pp.price * (1 - cp.extra_discount_percentage/100) as final_price
FROM products p
JOIN product_prices pp ON p.id = pp.product_id
JOIN company_pricing cp ON pp.price_list_id = cp.price_list_id
JOIN companies c ON cp.company_id = c.id
WHERE c.name ILIKE '%guapa bravo%'
LIMIT 10;
```

---

## 🎉 That's It!

You now have:
- ✅ All products from Douano
- ✅ All categories
- ✅ All price lists
- ✅ All prices per product per list
- ✅ All company-specific pricing (discounts)

Ready to build more UI on top of this! 🚀

