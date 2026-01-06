-- Create table for 2026 sales invoice data
-- This table stores raw invoice data from Douano API

CREATE TABLE IF NOT EXISTS public.sales_2026 (
    id SERIAL PRIMARY KEY,
    invoice_id INTEGER UNIQUE NOT NULL,
    invoice_data JSONB NOT NULL,
    company_id INTEGER,
    company_name TEXT,
    invoice_number TEXT,
    invoice_date DATE,
    due_date DATE,
    total_amount DECIMAL(10, 2),
    balance DECIMAL(10, 2),
    is_paid BOOLEAN DEFAULT true,  -- Default to true since payment status not synced
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_sales_2026_invoice_id ON public.sales_2026(invoice_id);
CREATE INDEX IF NOT EXISTS idx_sales_2026_company_id ON public.sales_2026(company_id);
CREATE INDEX IF NOT EXISTS idx_sales_2026_invoice_date ON public.sales_2026(invoice_date);
CREATE INDEX IF NOT EXISTS idx_sales_2026_company_name ON public.sales_2026(company_name);
CREATE INDEX IF NOT EXISTS idx_sales_2026_total_amount ON public.sales_2026(total_amount);

-- Create GIN index for JSONB data for faster queries
CREATE INDEX IF NOT EXISTS idx_sales_2026_invoice_data ON public.sales_2026 USING GIN(invoice_data);

-- Add comment to table
COMMENT ON TABLE public.sales_2026 IS 'Raw sales invoice data from Douano API for year 2026';
COMMENT ON COLUMN public.sales_2026.invoice_data IS 'Complete raw JSON data from Douano API';

-- Enable RLS (Row Level Security)
ALTER TABLE public.sales_2026 ENABLE ROW LEVEL SECURITY;

-- Create policy to allow authenticated users to read
CREATE POLICY "Allow authenticated users to read sales_2026"
ON public.sales_2026
FOR SELECT
TO authenticated
USING (true);

-- Create policy to allow service role to manage
CREATE POLICY "Allow service role to manage sales_2026"
ON public.sales_2026
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Create policy for anon (for development/demo purposes)
CREATE POLICY "Allow anon to read sales_2026"
ON public.sales_2026
FOR SELECT
TO anon
USING (true);

CREATE POLICY "Allow anon to manage sales_2026"
ON public.sales_2026
FOR ALL
TO anon
USING (true)
WITH CHECK (true);
