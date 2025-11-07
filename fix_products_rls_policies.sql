-- =====================================================
-- Fix RLS Policies for Product Tables
-- =====================================================
-- Allow authenticated users (anon key) to INSERT and UPDATE
-- This is needed for sync operations from the Flask app

-- Drop existing policies
DROP POLICY IF EXISTS "Allow authenticated read on product_categories" ON product_categories;
DROP POLICY IF EXISTS "Allow authenticated read on products" ON products;
DROP POLICY IF EXISTS "Allow authenticated read on sales_price_lists" ON sales_price_lists;
DROP POLICY IF EXISTS "Allow authenticated read on product_prices" ON product_prices;
DROP POLICY IF EXISTS "Allow authenticated read on company_pricing" ON company_pricing;
DROP POLICY IF EXISTS "Allow authenticated read on composed_product_items" ON composed_product_items;

-- Create new policies that allow INSERT/UPDATE for authenticated users
-- Product Categories
CREATE POLICY "Allow authenticated all access on product_categories"
    ON product_categories FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- Products
CREATE POLICY "Allow authenticated all access on products"
    ON products FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- Sales Price Lists
CREATE POLICY "Allow authenticated all access on sales_price_lists"
    ON sales_price_lists FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- Product Prices
CREATE POLICY "Allow authenticated all access on product_prices"
    ON product_prices FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- Company Pricing
CREATE POLICY "Allow authenticated all access on company_pricing"
    ON company_pricing FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- Composed Product Items
CREATE POLICY "Allow authenticated all access on composed_product_items"
    ON composed_product_items FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- Service role policies remain unchanged (already have full access)

