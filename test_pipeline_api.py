#!/usr/bin/env python3
"""
Quick test for the pipeline stats API endpoint
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_pipeline_api():
    """Test the pipeline stats API endpoint"""

    # Get Flask app URL (usually localhost:5000 or similar)
    flask_url = os.getenv('FLASK_URL', 'http://localhost:5000')

    try:
        print("Testing pipeline stats API...")

        # Test the pipeline stats endpoint
        response = requests.get(f'{flask_url}/api/prospects/pipeline-stats')

        print(f"Response status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ API call successful!")
            print(f"Total prospects: {data.get('total', 0)}")
            print("Stats by stage:")
            for stage, stats in data.get('stats', {}).items():
                print(f"  {stage}: {stats['count']} ({stats['percentage']}%)")
        elif response.status_code == 401:
            print("⚠️  Authentication required - this is expected if not logged in")
        else:
            print(f"❌ API call failed: {response.text}")

    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Flask app. Is it running?")
        print(f"   Make sure your Flask app is running on {flask_url}")
    except Exception as e:
        print(f"❌ Error testing API: {e}")

if __name__ == "__main__":
    test_pipeline_api()
