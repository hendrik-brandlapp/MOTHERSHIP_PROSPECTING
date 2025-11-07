-- Fix RLS policy for sales_2025 table
-- This allows the anon role to insert/update data for invoice sync

-- Drop existing restrictive policies
DROP POLICY IF EXISTS "Allow authenticated users to read sales_2025" ON public.sales_2025;
DROP POLICY IF EXISTS "Allow service role to manage sales_2025" ON public.sales_2025;

-- Create more permissive policies for the application

-- Allow anon role to read all data
CREATE POLICY "Allow anon to read sales_2025"
ON public.sales_2025
FOR SELECT
TO anon
USING (true);

-- Allow authenticated users to read all data
CREATE POLICY "Allow authenticated to read sales_2025"
ON public.sales_2025
FOR SELECT
TO authenticated
USING (true);

-- Allow anon role to insert/update (needed for invoice sync)
CREATE POLICY "Allow anon to manage sales_2025"
ON public.sales_2025
FOR ALL
TO anon
USING (true)
WITH CHECK (true);

-- Allow service role to manage all data
CREATE POLICY "Allow service role to manage sales_2025"
ON public.sales_2025
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Verify policies are created
SELECT schemaname, tablename, policyname, roles, cmd, qual
FROM pg_policies 
WHERE tablename = 'sales_2025'
ORDER BY policyname;
