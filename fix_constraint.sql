-- EMERGENCY FIX: Prospects Status Constraint Issue
-- Run this in your Supabase SQL editor to fix the constraint problem

-- Step 1: Check what constraints currently exist on prospects table
SELECT conname, conrelid::regclass, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'prospects'::regclass;

-- Step 2: Check current status values in prospects table
SELECT DISTINCT status, COUNT(*) FROM prospects GROUP BY status ORDER BY status;

-- Step 3: Force drop any existing status constraint
ALTER TABLE prospects DROP CONSTRAINT IF EXISTS prospects_status_check;

-- Step 4: Ensure all existing records have valid status values
UPDATE prospects
SET status = 'new_leads'
WHERE status IS NULL OR status NOT IN (
    'new_leads', 'first_contact', 'meeting_planned', 'follow_up',
    'customer', 'ex_customer', 'contact_later', 'unqualified'
);

-- Step 5: Add the correct constraint
ALTER TABLE prospects ADD CONSTRAINT prospects_status_check
CHECK (status IN (
    'new_leads',           -- 🔍 New Leads – nog te contacteren
    'first_contact',       -- 🤝 First Contact – eerste gesprek gehad
    'meeting_planned',     -- 📅 Meeting Planned – afspraak vastgelegd
    'follow_up',           -- ✍️ Follow-up – samples verstuurd of tasting gedaan
    'customer',            -- 🌱 Customer – actieve klant
    'ex_customer',         -- 🔙 Ex-Customer – gestopt met bestellen
    'contact_later',       -- ⏳ Contact Later – interessant, maar nog niet het juiste moment
    'unqualified'          -- ❌ Unqualified – niet relevant
));

-- Step 6: Verify the constraint was created and works
SELECT conname, conrelid::regclass, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'prospects'::regclass AND conname = 'prospects_status_check';

-- Step 7: Test constraint by trying to insert a valid row (this should work)
-- Note: Comment out this test if you don't want to create a test record
/*
INSERT INTO prospects (name, address, status)
VALUES ('Test Prospect', 'Test Address', 'new_leads');
*/

-- Step 8: Show final status distribution
SELECT status, COUNT(*) as count
FROM prospects
GROUP BY status
ORDER BY
    CASE status
        WHEN 'new_leads' THEN 1
        WHEN 'first_contact' THEN 2
        WHEN 'meeting_planned' THEN 3
        WHEN 'follow_up' THEN 4
        WHEN 'customer' THEN 5
        WHEN 'ex_customer' THEN 6
        WHEN 'contact_later' THEN 7
        WHEN 'unqualified' THEN 8
        ELSE 9
    END;
