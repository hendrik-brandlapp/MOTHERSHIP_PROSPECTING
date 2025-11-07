-- Add enhanced company columns to existing companies table
-- Run this after the basic companies table is created

-- Add new columns for enhanced company data
ALTER TABLE public.companies 
ADD COLUMN IF NOT EXISTS company_tag TEXT,
ADD COLUMN IF NOT EXISTS is_customer BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS is_supplier BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS company_status_id INTEGER,
ADD COLUMN IF NOT EXISTS company_status_name TEXT,
ADD COLUMN IF NOT EXISTS sales_price_class_id INTEGER,
ADD COLUMN IF NOT EXISTS sales_price_class_name TEXT,
ADD COLUMN IF NOT EXISTS document_delivery_type TEXT,
ADD COLUMN IF NOT EXISTS email_addresses TEXT,
ADD COLUMN IF NOT EXISTS default_document_notes TEXT[],
ADD COLUMN IF NOT EXISTS company_categories JSONB,
ADD COLUMN IF NOT EXISTS addresses JSONB,
ADD COLUMN IF NOT EXISTS bank_accounts JSONB,
ADD COLUMN IF NOT EXISTS extension_values JSONB;

-- Create indexes for new columns
CREATE INDEX IF NOT EXISTS idx_companies_company_tag ON public.companies(company_tag);
CREATE INDEX IF NOT EXISTS idx_companies_is_customer ON public.companies(is_customer);
CREATE INDEX IF NOT EXISTS idx_companies_sales_price_class ON public.companies(sales_price_class_id);
CREATE INDEX IF NOT EXISTS idx_companies_company_status ON public.companies(company_status_id);

-- Create GIN indexes for JSONB fields
CREATE INDEX IF NOT EXISTS idx_companies_categories ON public.companies USING GIN(company_categories);
CREATE INDEX IF NOT EXISTS idx_companies_addresses_gin ON public.companies USING GIN(addresses);
CREATE INDEX IF NOT EXISTS idx_companies_bank_accounts ON public.companies USING GIN(bank_accounts);
CREATE INDEX IF NOT EXISTS idx_companies_extensions ON public.companies USING GIN(extension_values);

-- Add comments for new columns
COMMENT ON COLUMN public.companies.company_tag IS 'Douano internal company tag/code';
COMMENT ON COLUMN public.companies.sales_price_class_id IS 'ID of the sales price class (Horeca, Retail, etc.)';
COMMENT ON COLUMN public.companies.company_categories IS 'Array of company category objects {id, name}';
COMMENT ON COLUMN public.companies.addresses IS 'Array of company address objects';
COMMENT ON COLUMN public.companies.extension_values IS 'Array of custom extension field values';

-- Verify new columns are added
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'companies' 
  AND table_schema = 'public'
ORDER BY ordinal_position;
