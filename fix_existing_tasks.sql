-- Fix existing customer maintenance tasks
-- Run this in your Supabase SQL editor

-- Update all existing customer follow-up tasks to use the new category
UPDATE sales_tasks 
SET category = 'customer_maintenance'
WHERE 
    (title LIKE '%Check-in%' OR title LIKE '%Follow-up%' OR title LIKE '%Regular Check-in%')
    AND (description LIKE '%customer%' OR description LIKE '%satisfaction%' OR description LIKE '%relationship maintenance%')
    AND category = 'customer_success';

-- Also update any tasks with long due dates (more than 25 days from creation)
UPDATE sales_tasks 
SET category = 'customer_maintenance'
WHERE 
    due_date > CURRENT_DATE + INTERVAL '25 days'
    AND category = 'customer_success'
    AND (task_type = 'call' OR task_type = 'meeting');

-- Success message
SELECT 'Existing customer maintenance tasks updated!' as status,
       COUNT(*) as tasks_updated
FROM sales_tasks 
WHERE category = 'customer_maintenance';
