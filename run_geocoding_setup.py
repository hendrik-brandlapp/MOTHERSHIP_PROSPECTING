#!/usr/bin/env python3
"""
Quick script to set up geocoding columns and run initial geocoding
"""

import os
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY

print("🚀 Setting up geocoding for companies...")
print()

# Initialize Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("Step 1: Adding geocoding columns to companies table...")
print("-" * 60)

# Read and execute the migration SQL
with open('add_geocoding_columns.sql', 'r') as f:
    sql = f.read()

# Note: Supabase Python client doesn't support raw SQL execution directly
# You need to run this via Supabase Dashboard SQL Editor or psql

print("⚠️  SQL MIGRATION REQUIRED")
print()
print("Please run this SQL in your Supabase SQL Editor:")
print("https://supabase.com/dashboard/project/gpjoypslbrpvnhqzvacc/sql")
print()
print("=" * 60)
print(sql)
print("=" * 60)
print()
print("After running the SQL, you can geocode companies with:")
print("  python geocode_companies.py --limit 10        # Test with 10 companies")
print("  python geocode_companies.py                   # Geocode all companies")
print()

