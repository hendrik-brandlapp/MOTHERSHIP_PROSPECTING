-- Create table for 2024 sales invoice data
-- This table stores raw invoice data from Douano API

CREATE TABLE IF NOT EXISTS public.sales_2024 (
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
CREATE INDEX IF NOT EXISTS idx_sales_2024_invoice_id ON public.sales_2024(invoice_id);
CREATE INDEX IF NOT EXISTS idx_sales_2024_company_id ON public.sales_2024(company_id);
CREATE INDEX IF NOT EXISTS idx_sales_2024_invoice_date ON public.sales_2024(invoice_date);
CREATE INDEX IF NOT EXISTS idx_sales_2024_company_name ON public.sales_2024(company_name);

-- Create GIN index for JSONB data for faster queries
CREATE INDEX IF NOT EXISTS idx_sales_2024_invoice_data ON public.sales_2024 USING GIN(invoice_data);

-- Add comment to table
COMMENT ON TABLE public.sales_2024 IS 'Raw sales invoice data from Douano API for year 2024';
COMMENT ON COLUMN public.sales_2024.invoice_data IS 'Complete raw JSON data from Douano API';

-- Enable RLS (Row Level Security)
ALTER TABLE public.sales_2024 ENABLE ROW LEVEL SECURITY;

-- Allow anon role to read all data
CREATE POLICY "Allow anon to read sales_2024"
ON public.sales_2024
FOR SELECT
TO anon
USING (true);

-- Allow authenticated users to read all data
CREATE POLICY "Allow authenticated to read sales_2024"
ON public.sales_2024
FOR SELECT
TO authenticated
USING (true);

-- Allow anon role to insert/update (needed for invoice sync)
CREATE POLICY "Allow anon to manage sales_2024"
ON public.sales_2024
FOR ALL
TO anon
USING (true)
WITH CHECK (true);

-- Allow service role to manage all data
CREATE POLICY "Allow service role to manage sales_2024"
ON public.sales_2024
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Verify policies are created
SELECT schemaname, tablename, policyname, roles, cmd, qual
FROM pg_policies 
WHERE tablename = 'sales_2024'
ORDER BY policyname;
