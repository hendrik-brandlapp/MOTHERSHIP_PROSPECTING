#!/usr/bin/env python3

import requests
import json

def test_prospects_api():
    """Test the prospects API and show current statuses"""
    try:
        print("🔍 Testing prospects API...")
        response = requests.get('http://localhost:5000/api/prospects')
        
        if response.status_code == 200:
            data = response.json()
            prospects = data.get('prospects', [])
            print(f"✅ Found {len(prospects)} prospects")
            
            # Count by status
            status_counts = {}
            for prospect in prospects:
                status = prospect.get('status', 'unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
            
            print("\n📊 Current status distribution:")
            for status, count in status_counts.items():
                print(f"   {status}: {count}")
            
            # Show first few prospects
            print(f"\n📋 First 3 prospects:")
            for i, prospect in enumerate(prospects[:3]):
                print(f"   {i+1}. {prospect.get('name', 'Unknown')} - Status: {prospect.get('status', 'None')}")
                
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - make sure Flask app is running on localhost:5000")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_pipeline_stats():
    """Test the pipeline stats API"""
    try:
        print("\n🔍 Testing pipeline stats API...")
        response = requests.get('http://localhost:5000/api/prospects/pipeline-stats')
        
        if response.status_code == 200:
            data = response.json()
            stats = data.get('stats', {})
            print("✅ Pipeline stats:")
            for status, stat in stats.items():
                count = stat.get('count', 0)
                percentage = stat.get('percentage', 0)
                print(f"   {status}: {count} ({percentage:.1f}%)")
        else:
            print(f"❌ Pipeline API Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Pipeline Error: {e}")

if __name__ == "__main__":
    test_prospects_api()
    test_pipeline_stats()
