#!/usr/bin/env python3
"""
Geocode Companies Script
========================
This script geocodes all companies in the database that don't have coordinates yet.
It uses the Mapbox Geocoding API to convert addresses to latitude/longitude.

Usage:
    python geocode_companies.py [--force] [--limit N] [--batch-size N]
    
Options:
    --force: Re-geocode all companies, even those already geocoded
    --limit N: Only geocode N companies
    --batch-size N: Number of companies to geocode in one batch (default: 50)
"""

import os
import sys
import time
import argparse
import requests
from datetime import datetime
from supabase import create_client, Client
from typing import Optional, Tuple, Dict
from config import SUPABASE_URL, SUPABASE_KEY, MAPBOX_API_KEY

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Mapbox Geocoding API endpoint
MAPBOX_GEOCODING_URL = "https://api.mapbox.com/geocoding/v5/mapbox.places"

# Rate limiting
REQUESTS_PER_SECOND = 10  # Mapbox allows higher, but we play it safe
DELAY_BETWEEN_REQUESTS = 1.0 / REQUESTS_PER_SECOND


def get_company_address(company: Dict) -> Optional[str]:
    """
    Extract full address from company data.
    Tries multiple data sources: addresses JSONB, individual fields, raw_company_data.
    """
    # Try invoice_address from raw_company_data first
    if company.get('raw_company_data') and company['raw_company_data'].get('invoice_address'):
        addr = company['raw_company_data']['invoice_address']
        parts = [
            addr.get('address_line1') or addr.get('address1') or addr.get('street'),
            addr.get('address_line2') or addr.get('address2'),
            addr.get('city') or addr.get('town'),
            addr.get('post_code') or addr.get('postal_code') or addr.get('zip_code'),
            addr.get('country', {}).get('name') if isinstance(addr.get('country'), dict) else addr.get('country_name') or addr.get('country')
        ]
        address = ', '.join([str(p) for p in parts if p])
        if address and len(address) > 10:  # Basic validation
            return address
    
    # Try addresses JSONB array
    if company.get('addresses') and isinstance(company['addresses'], list) and len(company['addresses']) > 0:
        addr = company['addresses'][0]  # Use first address
        parts = [
            addr.get('address_line1') or addr.get('street'),
            addr.get('address_line2'),
            addr.get('city'),
            addr.get('post_code') or addr.get('postal_code'),
            addr.get('country_name') or addr.get('country')
        ]
        address = ', '.join([str(p) for p in parts if p])
        if address and len(address) > 10:
            return address
    
    # Try individual address fields
    parts = [
        company.get('address_line1'),
        company.get('address_line2'),
        company.get('city'),
        company.get('post_code'),
        company.get('country_name') or company.get('country_code')
    ]
    address = ', '.join([str(p) for p in parts if p])
    if address and len(address) > 10:
        return address
    
    return None


def geocode_address_mapbox(address: str, country_bias: str = 'BE') -> Optional[Tuple[float, float, str]]:
    """
    Geocode an address using Mapbox Geocoding API.
    
    Returns:
        Tuple of (latitude, longitude, quality) or None if geocoding failed
    """
    try:
        # Encode address for URL
        encoded_address = requests.utils.quote(address)
        
        # Build Mapbox API URL
        url = f"{MAPBOX_GEOCODING_URL}/{encoded_address}.json"
        params = {
            'access_token': MAPBOX_API_KEY,
            'country': country_bias,  # Bias results to Belgium
            'limit': 1,
            'types': 'address,poi,place'
        }
        
        # Make request
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Check if we got results
        if not data.get('features') or len(data['features']) == 0:
            print(f"  ❌ No results found for: {address}")
            return None
        
        # Extract coordinates from first result
        feature = data['features'][0]
        coordinates = feature['geometry']['coordinates']
        longitude, latitude = coordinates  # Mapbox returns [lon, lat]
        
        # Determine quality based on result type
        place_type = feature.get('place_type', ['unknown'])[0]
        quality_map = {
            'address': 'exact',
            'poi': 'exact',
            'place': 'city',
            'postcode': 'postal_code',
            'locality': 'approximate',
            'neighborhood': 'approximate',
            'region': 'region',
            'country': 'country'
        }
        quality = quality_map.get(place_type, 'approximate')
        
        print(f"  ✅ Geocoded: {latitude}, {longitude} (quality: {quality})")
        return (latitude, longitude, quality)
        
    except requests.exceptions.RequestException as e:
        print(f"  ❌ API error: {e}")
        return None
    except Exception as e:
        print(f"  ❌ Unexpected error: {e}")
        return None


def update_company_coordinates(company_id: int, latitude: float, longitude: float, 
                               quality: str, geocoded_address: str) -> bool:
    """Update company coordinates in the database."""
    try:
        result = supabase.table('companies').update({
            'latitude': latitude,
            'longitude': longitude,
            'geocoded_address': geocoded_address,
            'geocoding_quality': quality,
            'geocoded_at': datetime.utcnow().isoformat(),
            'geocoding_provider': 'mapbox'
        }).eq('id', company_id).execute()
        
        return True
    except Exception as e:
        print(f"  ❌ Database update error: {e}")
        return False


def geocode_companies(force: bool = False, limit: Optional[int] = None, batch_size: int = 50):
    """
    Main function to geocode companies.
    
    Args:
        force: If True, re-geocode all companies even if already geocoded
        limit: Maximum number of companies to geocode
        batch_size: Number of companies to process in one database query
    """
    print("🌍 Starting company geocoding process...")
    print(f"   Force mode: {force}")
    print(f"   Limit: {limit or 'None (all companies)'}")
    print(f"   Batch size: {batch_size}\n")
    
    # Build query
    query = supabase.table('companies').select('*')
    
    if not force:
        # Only get companies without coordinates
        query = query.is_('geocoded_at', 'null')
    
    if limit:
        query = query.limit(limit)
    
    # Fetch companies
    print("📥 Fetching companies from database...")
    result = query.execute()
    companies = result.data
    
    if not companies:
        print("✅ No companies need geocoding!")
        return
    
    print(f"📊 Found {len(companies)} companies to geocode\n")
    
    # Process each company
    success_count = 0
    failed_count = 0
    skipped_count = 0
    
    for i, company in enumerate(companies, 1):
        company_id = company['id']
        company_name = company.get('name', 'Unnamed Company')
        
        print(f"[{i}/{len(companies)}] Processing: {company_name} (ID: {company_id})")
        
        # Get address
        address = get_company_address(company)
        if not address:
            print(f"  ⚠️  No valid address found")
            skipped_count += 1
            continue
        
        print(f"  📍 Address: {address}")
        
        # Determine country bias
        country_bias = 'BE'  # Default to Belgium
        if company.get('country_code'):
            country_bias = company['country_code']
        
        # Geocode the address
        result = geocode_address_mapbox(address, country_bias)
        
        if result:
            latitude, longitude, quality = result
            
            # Update database
            if update_company_coordinates(company_id, latitude, longitude, quality, address):
                success_count += 1
                print(f"  💾 Updated database")
            else:
                failed_count += 1
        else:
            failed_count += 1
        
        # Rate limiting
        if i < len(companies):  # Don't delay after last request
            time.sleep(DELAY_BETWEEN_REQUESTS)
        
        print()  # Blank line for readability
    
    # Summary
    print("=" * 60)
    print("📊 GEOCODING SUMMARY")
    print("=" * 60)
    print(f"✅ Successfully geocoded: {success_count}")
    print(f"❌ Failed to geocode:    {failed_count}")
    print(f"⚠️  Skipped (no address): {skipped_count}")
    print(f"📝 Total processed:      {len(companies)}")
    print("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Geocode company addresses in the database',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--force', action='store_true',
                       help='Re-geocode all companies, even those already geocoded')
    parser.add_argument('--limit', type=int, default=None,
                       help='Maximum number of companies to geocode')
    parser.add_argument('--batch-size', type=int, default=50,
                       help='Number of companies to process in one batch (default: 50)')
    
    args = parser.parse_args()
    
    # Validate environment
    if not MAPBOX_API_KEY:
        print("❌ Error: MAPBOX_API_KEY not found in environment")
        print("   Please set MAPBOX_API_KEY in your .env file or config.py")
        sys.exit(1)
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Error: SUPABASE_URL or SUPABASE_KEY not found")
        print("   Please check your .env file or config.py")
        sys.exit(1)
    
    try:
        geocode_companies(
            force=args.force,
            limit=args.limit,
            batch_size=args.batch_size
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  Geocoding interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

