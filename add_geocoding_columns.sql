-- Add geocoding columns to companies table
-- This migration adds latitude, longitude, and geocoding metadata

-- Add latitude and longitude columns
ALTER TABLE public.companies 
ADD COLUMN IF NOT EXISTS latitude DECIMAL(10, 8),
ADD COLUMN IF NOT EXISTS longitude DECIMAL(11, 8),
ADD COLUMN IF NOT EXISTS geocoded_address TEXT,
ADD COLUMN IF NOT EXISTS geocoding_quality TEXT,
ADD COLUMN IF NOT EXISTS geocoded_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS geocoding_provider TEXT DEFAULT 'mapbox';

-- Create spatial index for efficient location queries
CREATE INDEX IF NOT EXISTS idx_companies_coordinates ON public.companies(latitude, longitude);

-- Create index for geocoded status
CREATE INDEX IF NOT EXISTS idx_companies_geocoded ON public.companies(geocoded_at) 
WHERE geocoded_at IS NOT NULL;

-- Add comments for the new columns
COMMENT ON COLUMN public.companies.latitude IS 'Latitude coordinate for company address';
COMMENT ON COLUMN public.companies.longitude IS 'Longitude coordinate for company address';
COMMENT ON COLUMN public.companies.geocoded_address IS 'The full address that was geocoded';
COMMENT ON COLUMN public.companies.geocoding_quality IS 'Quality of geocoding result (exact, approximate, city, etc)';
COMMENT ON COLUMN public.companies.geocoded_at IS 'Timestamp when geocoding was performed';
COMMENT ON COLUMN public.companies.geocoding_provider IS 'Service used for geocoding (mapbox, google, etc)';

-- Verify the new columns
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'companies' 
  AND table_schema = 'public'
  AND column_name IN ('latitude', 'longitude', 'geocoded_address', 'geocoding_quality', 'geocoded_at', 'geocoding_provider')
ORDER BY ordinal_position;

