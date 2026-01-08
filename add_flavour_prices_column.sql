-- Migration: Add flavour_prices JSONB column to companies table
-- This stores per-flavour retail prices for each horeca location
-- Example: {"Elderflower": "2.50", "Ginger Lemon": "3.00"}

ALTER TABLE companies ADD COLUMN IF NOT EXISTS flavour_prices JSONB DEFAULT '{}';

-- Add index for efficient querying (optional, for filtering by price existence)
CREATE INDEX IF NOT EXISTS idx_companies_flavour_prices ON companies USING GIN (flavour_prices);
