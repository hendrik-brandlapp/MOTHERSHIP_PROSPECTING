-- =====================================================
-- Products & Pricing System Tables for Douano Integration
-- =====================================================
-- This migration creates comprehensive product and pricing tables
-- for syncing from Douano and managing company-specific pricing

-- =====================================================
-- 1. PRODUCT CATEGORIES TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS product_categories (
    id BIGINT PRIMARY KEY,  -- Douano category ID
    name TEXT NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    douano_created_at TIMESTAMP WITH TIME ZONE,
    douano_updated_at TIMESTAMP WITH TIME ZONE,
    last_sync_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for category lookups
CREATE INDEX IF NOT EXISTS idx_product_categories_name ON product_categories(name);
CREATE INDEX IF NOT EXISTS idx_product_categories_active ON product_categories(is_active);

-- =====================================================
-- 2. PRODUCTS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS products (
    id BIGINT PRIMARY KEY,  -- Douano product ID
    name TEXT NOT NULL,
    sku TEXT,
    category_id BIGINT REFERENCES product_categories(id),
    unit TEXT,  -- pieces, liter, kilogram, etc.
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    is_sellable BOOLEAN DEFAULT true,
    is_composed BOOLEAN DEFAULT false,  -- Whether it's a composed product
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    douano_created_at TIMESTAMP WITH TIME ZONE,
    douano_updated_at TIMESTAMP WITH TIME ZONE,
    last_sync_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for product lookups
CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);
CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_products_active ON products(is_active);
CREATE INDEX IF NOT EXISTS idx_products_sellable ON products(is_sellable);

-- =====================================================
-- 3. SALES PRICE LISTS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS sales_price_lists (
    id BIGINT PRIMARY KEY,  -- Douano price list ID
    name TEXT NOT NULL,  -- e.g., "RRP delivery", "Horeca volume", "Retail"
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    douano_created_at TIMESTAMP WITH TIME ZONE,
    douano_updated_at TIMESTAMP WITH TIME ZONE,
    last_sync_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for price list lookups
CREATE INDEX IF NOT EXISTS idx_sales_price_lists_name ON sales_price_lists(name);
CREATE INDEX IF NOT EXISTS idx_sales_price_lists_active ON sales_price_lists(is_active);
CREATE INDEX IF NOT EXISTS idx_sales_price_lists_default ON sales_price_lists(is_default);

-- =====================================================
-- 4. PRODUCT PRICES TABLE (Products in Price Lists)
-- =====================================================
CREATE TABLE IF NOT EXISTS product_prices (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    price_list_id BIGINT NOT NULL REFERENCES sales_price_lists(id) ON DELETE CASCADE,
    price DECIMAL(15, 2) NOT NULL,  -- Base price for this product in this price list
    cost_price DECIMAL(15, 2),  -- Optional: cost price
    currency TEXT DEFAULT 'EUR',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_sync_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(product_id, price_list_id)  -- One price per product per price list
);

-- Indexes for price lookups
CREATE INDEX IF NOT EXISTS idx_product_prices_product ON product_prices(product_id);
CREATE INDEX IF NOT EXISTS idx_product_prices_price_list ON product_prices(price_list_id);
CREATE INDEX IF NOT EXISTS idx_product_prices_active ON product_prices(is_active);

-- =====================================================
-- 5. COMPANY PRICING TABLE (Company-Specific Pricing)
-- =====================================================
CREATE TABLE IF NOT EXISTS company_pricing (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    price_list_id BIGINT REFERENCES sales_price_lists(id),  -- Which price list this company uses
    standard_discount_percentage DECIMAL(5, 2) DEFAULT 0,  -- Standard discount %
    extra_discount_percentage DECIMAL(5, 2) DEFAULT 0,  -- Extra discount %
    financial_discount_percentage DECIMAL(5, 2) DEFAULT 0,  -- Financial discount %
    payment_term_days INTEGER DEFAULT 30,  -- Payment terms
    is_active BOOLEAN DEFAULT true,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_sync_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(company_id)  -- One pricing config per company
);

-- Indexes for company pricing lookups
CREATE INDEX IF NOT EXISTS idx_company_pricing_company ON company_pricing(company_id);
CREATE INDEX IF NOT EXISTS idx_company_pricing_price_list ON company_pricing(price_list_id);
CREATE INDEX IF NOT EXISTS idx_company_pricing_active ON company_pricing(is_active);

-- =====================================================
-- 6. COMPOSED PRODUCT ITEMS TABLE (Product Recipes)
-- =====================================================
CREATE TABLE IF NOT EXISTS composed_product_items (
    id BIGINT PRIMARY KEY,  -- Douano composed product item ID
    composed_product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,  -- The final product
    component_product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,  -- A component
    quantity DECIMAL(15, 4) NOT NULL,  -- How much of this component is needed
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    douano_created_at TIMESTAMP WITH TIME ZONE,
    douano_updated_at TIMESTAMP WITH TIME ZONE,
    last_sync_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for composed product lookups
CREATE INDEX IF NOT EXISTS idx_composed_product_items_composed ON composed_product_items(composed_product_id);
CREATE INDEX IF NOT EXISTS idx_composed_product_items_component ON composed_product_items(component_product_id);

-- =====================================================
-- 7. ADD RLS (Row Level Security) POLICIES
-- =====================================================
ALTER TABLE product_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE sales_price_lists ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_prices ENABLE ROW LEVEL SECURITY;
ALTER TABLE company_pricing ENABLE ROW LEVEL SECURITY;
ALTER TABLE composed_product_items ENABLE ROW LEVEL SECURITY;

-- Policy: Allow authenticated users to read all
CREATE POLICY "Allow authenticated read on product_categories"
    ON product_categories FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Allow authenticated read on products"
    ON products FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Allow authenticated read on sales_price_lists"
    ON sales_price_lists FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Allow authenticated read on product_prices"
    ON product_prices FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Allow authenticated read on company_pricing"
    ON company_pricing FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Allow authenticated read on composed_product_items"
    ON composed_product_items FOR SELECT
    TO authenticated
    USING (true);

-- Policy: Allow service role to do anything (for sync operations)
CREATE POLICY "Allow service role full access on product_categories"
    ON product_categories FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Allow service role full access on products"
    ON products FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Allow service role full access on sales_price_lists"
    ON sales_price_lists FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Allow service role full access on product_prices"
    ON product_prices FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Allow service role full access on company_pricing"
    ON company_pricing FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Allow service role full access on composed_product_items"
    ON composed_product_items FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- =====================================================
-- 8. CREATE HELPFUL VIEWS
-- =====================================================

-- View: Products with their category names and price count
CREATE OR REPLACE VIEW products_overview AS
SELECT 
    p.id,
    p.name,
    p.sku,
    p.unit,
    p.is_active,
    p.is_sellable,
    p.is_composed,
    pc.name as category_name,
    pc.id as category_id,
    COUNT(DISTINCT pp.price_list_id) as price_lists_count,
    MIN(pp.price) as min_price,
    MAX(pp.price) as max_price,
    AVG(pp.price) as avg_price
FROM products p
LEFT JOIN product_categories pc ON p.category_id = pc.id
LEFT JOIN product_prices pp ON p.id = pp.product_id AND pp.is_active = true
GROUP BY p.id, p.name, p.sku, p.unit, p.is_active, p.is_sellable, p.is_composed, pc.name, pc.id;

-- View: Company pricing with price list names
CREATE OR REPLACE VIEW company_pricing_overview AS
SELECT 
    cp.id,
    cp.company_id,
    c.name as company_name,
    c.public_name as company_public_name,
    cp.price_list_id,
    spl.name as price_list_name,
    cp.standard_discount_percentage,
    cp.extra_discount_percentage,
    cp.financial_discount_percentage,
    cp.payment_term_days,
    cp.is_active
FROM company_pricing cp
LEFT JOIN companies c ON cp.company_id = c.id
LEFT JOIN sales_price_lists spl ON cp.price_list_id = spl.id;

-- View: Product prices with full context
CREATE OR REPLACE VIEW product_prices_detailed AS
SELECT 
    pp.id,
    pp.product_id,
    p.name as product_name,
    p.sku as product_sku,
    pp.price_list_id,
    spl.name as price_list_name,
    pp.price,
    pp.cost_price,
    pp.currency,
    pp.is_active,
    pc.name as category_name
FROM product_prices pp
LEFT JOIN products p ON pp.product_id = p.id
LEFT JOIN sales_price_lists spl ON pp.price_list_id = spl.id
LEFT JOIN product_categories pc ON p.category_id = pc.id;

-- =====================================================
-- DONE!
-- =====================================================
-- Run this SQL in your Supabase SQL Editor
-- Then use the Flask endpoints to sync data from Douano

