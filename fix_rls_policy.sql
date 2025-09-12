-- Fix RLS policy for prospects table
-- Run this in your Supabase SQL editor to fix the permission issue

-- Drop existing policies
DROP POLICY IF EXISTS "Enable all operations for authenticated users" ON prospects;
DROP POLICY IF EXISTS "Enable all operations for anon users" ON prospects;

-- Create new policy that allows all operations for anon users
CREATE POLICY "Enable all operations for anon users" ON prospects
    FOR ALL USING (true);

-- Verify the policy was created
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual 
FROM pg_policies 
WHERE tablename = 'prospects';
