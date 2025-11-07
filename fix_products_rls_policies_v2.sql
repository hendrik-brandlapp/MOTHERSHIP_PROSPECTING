-- =====================================================
-- Fix RLS Policies for Product Tables (Version 2)
-- =====================================================
-- Grant access to BOTH anon and authenticated roles
-- This is needed because the Supabase anon key uses the 'anon' role

-- Drop all existing policies first
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

-- Create new policies that allow ANON role (used by Supabase anon key)
-- Product Categories
CREATE POLICY "Allow anon all access on product_categories"
    ON product_categories FOR ALL
    TO anon
    USING (true)
    WITH CHECK (true);

-- Products
CREATE POLICY "Allow anon all access on products"
    ON products FOR ALL
    TO anon
    USING (true)
    WITH CHECK (true);

-- Sales Price Lists
CREATE POLICY "Allow anon all access on sales_price_lists"
    ON sales_price_lists FOR ALL
    TO anon
    USING (true)
    WITH CHECK (true);

-- Product Prices
CREATE POLICY "Allow anon all access on product_prices"
    ON product_prices FOR ALL
    TO anon
    USING (true)
    WITH CHECK (true);

-- Company Pricing
CREATE POLICY "Allow anon all access on company_pricing"
    ON company_pricing FOR ALL
    TO anon
    USING (true)
    WITH CHECK (true);

-- Composed Product Items
CREATE POLICY "Allow anon all access on composed_product_items"
    ON composed_product_items FOR ALL
    TO anon
    USING (true)
    WITH CHECK (true);

