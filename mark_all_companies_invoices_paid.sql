-- Mark all invoices as paid for all companies
-- Run this after populating the companies table

-- Update all 2024 invoices to paid
UPDATE public.sales_2024 
SET 
    is_paid = TRUE,
    balance = 0.00,
    updated_at = NOW()
WHERE is_paid = FALSE;

-- Update all 2025 invoices to paid  
UPDATE public.sales_2025 
SET 
    is_paid = TRUE,
    balance = 0.00,
    updated_at = NOW()
WHERE is_paid = FALSE;

-- Verify the updates
SELECT 
    'Companies and invoices update completed!' as status,
    (SELECT COUNT(*) FROM public.companies) as total_companies,
    (SELECT COUNT(*) FROM public.sales_2024 WHERE is_paid = TRUE) as paid_2024_invoices,
    (SELECT COUNT(*) FROM public.sales_2025 WHERE is_paid = TRUE) as paid_2025_invoices,
    (SELECT SUM(total_revenue_all_time) FROM public.companies) as total_revenue_all_companies;
