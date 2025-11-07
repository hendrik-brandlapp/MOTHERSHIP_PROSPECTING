-- Mark all 2025 invoices as paid
-- These are outgoing invoices sent to customers that have been paid

-- Update all invoices to mark them as paid
UPDATE public.sales_2025 
SET 
    is_paid = TRUE,
    balance = 0.00,
    updated_at = NOW()
WHERE is_paid = FALSE;

-- Verify the update
SELECT 
    'Update completed!' as status,
    COUNT(*) as total_invoices,
    SUM(CASE WHEN is_paid = TRUE THEN 1 ELSE 0 END) as paid_invoices,
    SUM(CASE WHEN is_paid = FALSE THEN 1 ELSE 0 END) as unpaid_invoices,
    SUM(total_amount) as total_revenue,
    SUM(balance) as total_outstanding
FROM public.sales_2025;

-- Show a sample of updated records
SELECT 
    invoice_number,
    company_name,
    total_amount,
    balance,
    is_paid,
    updated_at
FROM public.sales_2025
ORDER BY updated_at DESC
LIMIT 10;
