-- =====================================================
-- DISABLE RLS for Product Tables (Simple Fix)
-- =====================================================
-- Since these tables are only accessed via the backend,
-- we can simply disable RLS entirely

-- Disable RLS on all product tables
ALTER TABLE product_categories DISABLE ROW LEVEL SECURITY;
ALTER TABLE products DISABLE ROW LEVEL SECURITY;
ALTER TABLE sales_price_lists DISABLE ROW LEVEL SECURITY;
ALTER TABLE product_prices DISABLE ROW LEVEL SECURITY;
ALTER TABLE company_pricing DISABLE ROW LEVEL SECURITY;
ALTER TABLE composed_product_items DISABLE ROW LEVEL SECURITY;

-- Drop all existing policies (cleanup)
DROP POLICY IF EXISTS "Allow anon all access on product_categories" ON product_categories;
DROP POLICY IF EXISTS "Allow anon all access on products" ON products;
DROP POLICY IF EXISTS "Allow anon all access on sales_price_lists" ON sales_price_lists;
DROP POLICY IF EXISTS "Allow anon all access on product_prices" ON product_prices;
DROP POLICY IF EXISTS "Allow anon all access on company_pricing" ON company_pricing;
DROP POLICY IF EXISTS "Allow anon all access on composed_product_items" ON composed_product_items;

DROP POLICY IF EXISTS "Allow authenticated all access on product_categories" ON product_categories;
DROP POLICY IF EXISTS "Allow authenticated all access on products" ON products;
DROP POLICY IF EXISTS "Allow authenticated all access on sales_price_lists" ON sales_price_lists;
DROP POLICY IF EXISTS "Allow authenticated all access on product_prices" ON product_prices;
DROP POLICY IF EXISTS "Allow authenticated all access on company_pricing" ON company_pricing;
DROP POLICY IF EXISTS "Allow authenticated all access on composed_product_items" ON composed_product_items;

DROP POLICY IF EXISTS "Allow authenticated read on product_categories" ON product_categories;
DROP POLICY IF EXISTS "Allow authenticated read on products" ON products;
DROP POLICY IF EXISTS "Allow authenticated read on sales_price_lists" ON sales_price_lists;
DROP POLICY IF EXISTS "Allow authenticated read on product_prices" ON product_prices;
DROP POLICY IF EXISTS "Allow authenticated read on company_pricing" ON company_pricing;
DROP POLICY IF EXISTS "Allow authenticated read on composed_product_items" ON composed_product_items;

