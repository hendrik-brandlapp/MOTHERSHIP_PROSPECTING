-- Create table for 2025 sales invoice data
-- This table stores raw invoice data from Douano API

CREATE TABLE IF NOT EXISTS public.sales_2025 (
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
    is_paid BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_sales_2025_invoice_id ON public.sales_2025(invoice_id);
CREATE INDEX IF NOT EXISTS idx_sales_2025_company_id ON public.sales_2025(company_id);
CREATE INDEX IF NOT EXISTS idx_sales_2025_invoice_date ON public.sales_2025(invoice_date);
CREATE INDEX IF NOT EXISTS idx_sales_2025_company_name ON public.sales_2025(company_name);

-- Create GIN index for JSONB data for faster queries
CREATE INDEX IF NOT EXISTS idx_sales_2025_invoice_data ON public.sales_2025 USING GIN(invoice_data);

-- Add comment to table
COMMENT ON TABLE public.sales_2025 IS 'Raw sales invoice data from Douano API for year 2025';
COMMENT ON COLUMN public.sales_2025.invoice_data IS 'Complete raw JSON data from Douano API';

-- Enable RLS (Row Level Security)
ALTER TABLE public.sales_2025 ENABLE ROW LEVEL SECURITY;

-- Create policy to allow authenticated users to read
CREATE POLICY "Allow authenticated users to read sales_2025"
ON public.sales_2025
FOR SELECT
TO authenticated
USING (true);

-- Create policy to allow service role to insert/update
CREATE POLICY "Allow service role to manage sales_2025"
ON public.sales_2025
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

