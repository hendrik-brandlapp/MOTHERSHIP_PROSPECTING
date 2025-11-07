-- Create comprehensive companies table
-- This table stores all company data extracted from invoices and enriched with additional information

CREATE TABLE IF NOT EXISTS public.companies (
    id SERIAL PRIMARY KEY,
    company_id INTEGER UNIQUE NOT NULL, -- Douano company ID
    name TEXT NOT NULL,
    public_name TEXT,
    vat_number TEXT,
    email TEXT,
    phone_number TEXT,
    website TEXT,
    
    -- Address information
    address_line1 TEXT,
    address_line2 TEXT,
    city TEXT,
    post_code TEXT,
    country_id INTEGER,
    country_name TEXT,
    country_code TEXT,
    is_eu_country BOOLEAN DEFAULT false,
    
    -- Contact information
    contact_person_name TEXT,
    contact_person_email TEXT,
    contact_person_phone TEXT,
    
    -- Business information
    industry TEXT,
    company_size TEXT,
    business_type TEXT,
    registration_number TEXT,
    company_tag TEXT, -- Douano internal tag
    
    -- Company classification
    is_customer BOOLEAN DEFAULT false,
    is_supplier BOOLEAN DEFAULT false,
    company_status_id INTEGER,
    company_status_name TEXT,
    sales_price_class_id INTEGER,
    sales_price_class_name TEXT,
    
    -- Document and communication
    document_delivery_type TEXT,
    email_addresses TEXT,
    default_document_notes TEXT[],
    
    -- Company categories (multiple)
    company_categories JSONB, -- Array of {id, name}
    
    -- Addresses (multiple)
    addresses JSONB, -- Array of address objects
    
    -- Bank accounts
    bank_accounts JSONB, -- Array of bank account objects
    
    -- Extension values (custom fields)
    extension_values JSONB, -- Array of extension objects
    
    -- Financial summary (calculated from invoices)
    total_revenue_2024 DECIMAL(12, 2) DEFAULT 0,
    total_revenue_2025 DECIMAL(12, 2) DEFAULT 0,
    total_revenue_all_time DECIMAL(12, 2) DEFAULT 0,
    invoice_count_2024 INTEGER DEFAULT 0,
    invoice_count_2025 INTEGER DEFAULT 0,
    invoice_count_all_time INTEGER DEFAULT 0,
    average_invoice_value DECIMAL(10, 2) DEFAULT 0,
    
    -- Relationship timeline
    first_invoice_date DATE,
    last_invoice_date DATE,
    customer_since DATE,
    last_activity_date DATE,
    
    -- Additional metadata
    payment_terms TEXT[],
    currencies_used TEXT[],
    has_attachments BOOLEAN DEFAULT false,
    notes TEXT,
    tags TEXT[],
    
    -- Audit fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_sync_at TIMESTAMP WITH TIME ZONE,
    
    -- Raw data preservation
    raw_company_data JSONB,
    data_sources TEXT[] DEFAULT ARRAY['invoices'] -- Track where data came from
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_companies_company_id ON public.companies(company_id);
CREATE INDEX IF NOT EXISTS idx_companies_name ON public.companies(name);
CREATE INDEX IF NOT EXISTS idx_companies_vat_number ON public.companies(vat_number);
CREATE INDEX IF NOT EXISTS idx_companies_country_id ON public.companies(country_id);
CREATE INDEX IF NOT EXISTS idx_companies_city ON public.companies(city);
CREATE INDEX IF NOT EXISTS idx_companies_total_revenue ON public.companies(total_revenue_all_time);
CREATE INDEX IF NOT EXISTS idx_companies_last_activity ON public.companies(last_activity_date);

-- Create GIN indexes for array and JSONB fields
CREATE INDEX IF NOT EXISTS idx_companies_payment_terms ON public.companies USING GIN(payment_terms);
CREATE INDEX IF NOT EXISTS idx_companies_currencies ON public.companies USING GIN(currencies_used);
CREATE INDEX IF NOT EXISTS idx_companies_tags ON public.companies USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_companies_raw_data ON public.companies USING GIN(raw_company_data);

-- Add comments
COMMENT ON TABLE public.companies IS 'Master companies table with data from invoices and external sources';
COMMENT ON COLUMN public.companies.company_id IS 'Unique Douano company ID';
COMMENT ON COLUMN public.companies.raw_company_data IS 'Complete raw JSON data from various sources';
COMMENT ON COLUMN public.companies.data_sources IS 'Array tracking which sources provided data (invoices, api, manual, etc.)';

-- Enable RLS (Row Level Security)
ALTER TABLE public.companies ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Allow anon to read companies" ON public.companies;
DROP POLICY IF EXISTS "Allow authenticated to read companies" ON public.companies;
DROP POLICY IF EXISTS "Allow anon to manage companies" ON public.companies;
DROP POLICY IF EXISTS "Allow service role to manage companies" ON public.companies;

-- Allow anon role to read all data
CREATE POLICY "Allow anon to read companies"
ON public.companies
FOR SELECT
TO anon
USING (true);

-- Allow authenticated users to read all data
CREATE POLICY "Allow authenticated to read companies"
ON public.companies
FOR SELECT
TO authenticated
USING (true);

-- Allow anon role to insert/update (needed for company sync)
CREATE POLICY "Allow anon to manage companies"
ON public.companies
FOR ALL
TO anon
USING (true)
WITH CHECK (true);

-- Allow service role to manage all data
CREATE POLICY "Allow service role to manage companies"
ON public.companies
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_companies_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop existing trigger if it exists
DROP TRIGGER IF EXISTS companies_updated_at_trigger ON public.companies;

-- Create trigger for automatic timestamp updates
CREATE TRIGGER companies_updated_at_trigger
    BEFORE UPDATE ON public.companies
    FOR EACH ROW
    EXECUTE FUNCTION update_companies_updated_at();

-- Verify policies are created
SELECT schemaname, tablename, policyname, roles, cmd, qual
FROM pg_policies 
WHERE tablename = 'companies'
ORDER BY policyname;
