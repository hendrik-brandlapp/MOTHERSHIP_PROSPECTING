-- Add 'visited' as a valid prospect status
-- Run this in your Supabase SQL editor

-- Update the check constraint to include 'visited' status
ALTER TABLE prospects 
DROP CONSTRAINT IF EXISTS prospects_status_check;

ALTER TABLE prospects 
ADD CONSTRAINT prospects_status_check 
CHECK (status IN ('new_leads', 'visited', 'first_contact', 'meeting_planned', 'follow_up', 'customer', 'ex_customer', 'contact_later', 'unqualified'));

-- Success message
SELECT 'Visited status added to prospects table successfully!' as status;
