-- Mark all invoices as paid in both 2024 and 2025 tables
-- Payment status is not synced from Duano, so we're setting all to paid

-- Update sales_2024
UPDATE public.sales_2024
SET is_paid = true,
    updated_at = NOW()
WHERE is_paid = false;

-- Update sales_2025
UPDATE public.sales_2025
SET is_paid = true,
    updated_at = NOW()
WHERE is_paid = false;

-- Verify the updates
SELECT
    'sales_2024' as table_name,
    COUNT(*) as total,
    SUM(CASE WHEN is_paid THEN 1 ELSE 0 END) as paid,
    SUM(CASE WHEN NOT is_paid THEN 1 ELSE 0 END) as unpaid
FROM public.sales_2024
UNION ALL
SELECT
    'sales_2025' as table_name,
    COUNT(*) as total,
    SUM(CASE WHEN is_paid THEN 1 ELSE 0 END) as paid,
    SUM(CASE WHEN NOT is_paid THEN 1 ELSE 0 END) as unpaid
FROM public.sales_2025;
