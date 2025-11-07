#!/usr/bin/env python3
"""
Test script to verify the prospecting pipeline migration worked correctly.
Run this after executing the migration in Supabase.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    import supabase
    from supabase import create_client, Client
except ImportError:
    print("❌ Supabase client not installed. Run: pip install supabase")
    sys.exit(1)

def test_migration():
    """Test the prospecting pipeline migration"""

    # Initialize Supabase client
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')

    if not supabase_url or not supabase_key:
        print("❌ Supabase credentials not found in environment variables")
        return False

    try:
        supabase_client: Client = create_client(supabase_url, supabase_key)
        print("✅ Connected to Supabase")

        # Test 1: Check if new columns exist
        print("\n🔍 Testing new prospect columns...")
        result = supabase_client.table('prospects').select(
            'id, name, status, region, prospect_type, contact_later_date, unqualified_reason'
        ).limit(1).execute()

        if result.data:
            prospect = result.data[0]
            required_columns = ['status', 'region', 'prospect_type']
            missing_columns = [col for col in required_columns if col not in prospect]

            if missing_columns:
                print(f"❌ Missing columns: {missing_columns}")
                return False
            else:
                print("✅ All new prospect columns exist")

        # Test 2: Check if status constraint works
        print("\n🔍 Testing status constraint...")

        # First check what statuses currently exist
        status_check = supabase_client.table('prospects').select('status').limit(5).execute()
        if status_check.data:
            current_statuses = set(row['status'] for row in status_check.data if row['status'])
            print(f"📊 Current statuses in database: {sorted(current_statuses)}")

        # Try to insert a prospect with valid status
        test_data = {
            'name': 'Test Prospect for Migration',
            'address': 'Test Address',
            'status': 'new_leads',
            'region': 'Test Region',
            'prospect_type': 'Test Type'
        }

        try:
            result = supabase_client.table('prospects').insert(test_data).execute()
            if result.data:
                test_prospect_id = result.data[0]['id']
                print("✅ Valid status insertion works")

                # Clean up test data
                supabase_client.table('prospects').delete().eq('id', test_prospect_id).execute()
                print("✅ Test data cleaned up")
            else:
                print("❌ Insert returned no data")
                return False
        except Exception as e:
            print(f"❌ Valid status insertion failed: {e}")
            print("💡 This suggests the constraint is still blocking 'new_leads'")
            print("   Try running the fix_constraint.sql script first")
            return False

        # Test 3: Check if pipeline stats view exists
        print("\n🔍 Testing pipeline stats view...")
        try:
            result = supabase_client.rpc('get_pipeline_stats').execute()
            print("✅ Pipeline stats function exists")
        except Exception as e:
            print(f"⚠️  Pipeline stats function not found (this is optional): {e}")

        # Test 4: Check if unqualified reasons table exists
        print("\n🔍 Testing unqualified reasons table...")
        try:
            result = supabase_client.table('unqualified_reasons').select('*').limit(1).execute()
            print("✅ Unqualified reasons table exists")
        except Exception as e:
            print(f"❌ Unqualified reasons table missing: {e}")
            return False

        # Test 5: Check if prospect tasks table exists
        print("\n🔍 Testing prospect tasks table...")
        try:
            result = supabase_client.table('prospect_tasks').select('*').limit(1).execute()
            print("✅ Prospect tasks table exists")
        except Exception as e:
            print(f"❌ Prospect tasks table missing: {e}")
            return False

        print("\n🎉 Migration test completed successfully!")
        print("\n📋 Your enhanced prospecting pipeline is ready to use!")
        print("\n🔄 Pipeline Stages Available:")
        print("  🔍 New Leads")
        print("  🤝 First Contact")
        print("  📅 Meeting Planned")
        print("  ✍️ Follow-up")
        print("  🌱 Customer")
        print("  🔙 Ex-Customer")
        print("  ⏳ Contact Later")
        print("  ❌ Unqualified")

        return True

    except Exception as e:
        print(f"❌ Migration test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Prospecting Pipeline Migration")
    print("=" * 50)

    success = test_migration()

    if success:
        print("\n✅ All tests passed! Your migration was successful.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please check your migration.")
        sys.exit(1)
