#!/usr/bin/env python3
"""
Test script for the comprehensive task management system
"""

import requests
import json
from datetime import datetime, date, timedelta

# Configuration
BASE_URL = "http://localhost:5000"
API_BASE = f"{BASE_URL}/api"

def test_task_system():
    """Test the complete task management system"""
    print("🧪 Testing Task Management System")
    print("=" * 50)
    
    # Test 1: Create a new task
    print("\n1. Testing Task Creation...")
    task_data = {
        "title": "Test Follow-up Call",
        "description": "Call prospect to discuss their requirements",
        "task_type": "call",
        "priority": 2,
        "due_date": (date.today() + timedelta(days=3)).isoformat(),
        "due_time": "14:00",
        "estimated_duration": 30,
        "assigned_to": "Sales Rep",
        "notes": "Important follow-up for high-value prospect"
    }
    
    try:
        response = requests.post(f"{API_BASE}/tasks", json=task_data)
        if response.status_code == 201:
            task = response.json()['task']
            task_id = task['id']
            print(f"✅ Task created successfully: {task['title']}")
            print(f"   Task ID: {task_id}")
            print(f"   Type: {task['task_type']}, Priority: {task['priority']}")
        else:
            print(f"❌ Failed to create task: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Error creating task: {e}")
        return
    
    # Test 2: Get all tasks
    print("\n2. Testing Task Retrieval...")
    try:
        response = requests.get(f"{API_BASE}/tasks")
        if response.status_code == 200:
            tasks = response.json()['tasks']
            print(f"✅ Retrieved {len(tasks)} tasks")
            for task in tasks[:3]:  # Show first 3 tasks
                print(f"   - {task['title']} ({task['status']})")
        else:
            print(f"❌ Failed to retrieve tasks: {response.status_code}")
    except Exception as e:
        print(f"❌ Error retrieving tasks: {e}")
    
    # Test 3: Get task analytics
    print("\n3. Testing Task Analytics...")
    try:
        response = requests.get(f"{API_BASE}/tasks/analytics")
        if response.status_code == 200:
            analytics = response.json()
            print("✅ Task analytics retrieved:")
            print(f"   Total tasks: {analytics['total_tasks']}")
            print(f"   Overdue: {analytics['overdue_count']}")
            print(f"   Due today: {analytics['due_today']}")
            print(f"   Completion rate: {analytics['completion_rate']}%")
        else:
            print(f"❌ Failed to get analytics: {response.status_code}")
    except Exception as e:
        print(f"❌ Error getting analytics: {e}")
    
    # Test 4: Update task status
    print("\n4. Testing Task Update...")
    try:
        update_data = {
            "status": "in_progress",
            "progress_percentage": 50
        }
        response = requests.patch(f"{API_BASE}/tasks/{task_id}", json=update_data)
        if response.status_code == 200:
            updated_task = response.json()['task']
            print(f"✅ Task updated successfully")
            print(f"   Status: {updated_task['status']}")
            print(f"   Progress: {updated_task['progress_percentage']}%")
        else:
            print(f"❌ Failed to update task: {response.status_code}")
    except Exception as e:
        print(f"❌ Error updating task: {e}")
    
    # Test 5: Get task templates
    print("\n5. Testing Task Templates...")
    try:
        response = requests.get(f"{API_BASE}/task-templates")
        if response.status_code == 200:
            templates = response.json()['templates']
            print(f"✅ Retrieved {len(templates)} task templates:")
            for template in templates[:3]:  # Show first 3 templates
                print(f"   - {template['name']} ({template['task_type']})")
        else:
            print(f"❌ Failed to retrieve templates: {response.status_code}")
    except Exception as e:
        print(f"❌ Error retrieving templates: {e}")
    
    # Test 6: Get upcoming tasks
    print("\n6. Testing Upcoming Tasks...")
    try:
        response = requests.get(f"{API_BASE}/tasks/upcoming?days=7")
        if response.status_code == 200:
            upcoming = response.json()['tasks']
            print(f"✅ Retrieved {len(upcoming)} upcoming tasks")
            for task in upcoming[:2]:  # Show first 2 upcoming tasks
                print(f"   - {task['title']} (Due: {task['due_date']})")
        else:
            print(f"❌ Failed to retrieve upcoming tasks: {response.status_code}")
    except Exception as e:
        print(f"❌ Error retrieving upcoming tasks: {e}")
    
    # Test 7: Add task comment
    print("\n7. Testing Task Comments...")
    try:
        comment_data = {
            "comment": "Called prospect - will follow up next week",
            "comment_type": "comment",
            "created_by": "Test User"
        }
        response = requests.post(f"{API_BASE}/tasks/{task_id}/comments", json=comment_data)
        if response.status_code == 201:
            comment = response.json()['comment']
            print(f"✅ Comment added successfully: {comment['comment']}")
        else:
            print(f"❌ Failed to add comment: {response.status_code}")
    except Exception as e:
        print(f"❌ Error adding comment: {e}")
    
    # Test 8: Get task with full details
    print("\n8. Testing Task Detail Retrieval...")
    try:
        response = requests.get(f"{API_BASE}/tasks/{task_id}")
        if response.status_code == 200:
            task = response.json()['task']
            print(f"✅ Task details retrieved:")
            print(f"   Title: {task['title']}")
            print(f"   Status: {task['status']}")
            print(f"   Comments: {len(task.get('comments', []))}")
        else:
            print(f"❌ Failed to retrieve task details: {response.status_code}")
    except Exception as e:
        print(f"❌ Error retrieving task details: {e}")
    
    # Test 9: Filter tasks
    print("\n9. Testing Task Filtering...")
    try:
        response = requests.get(f"{API_BASE}/tasks?status=in_progress&priority=2")
        if response.status_code == 200:
            filtered_tasks = response.json()['tasks']
            print(f"✅ Filtered tasks retrieved: {len(filtered_tasks)} tasks")
        else:
            print(f"❌ Failed to filter tasks: {response.status_code}")
    except Exception as e:
        print(f"❌ Error filtering tasks: {e}")
    
    # Test 10: Complete the task
    print("\n10. Testing Task Completion...")
    try:
        completion_data = {
            "status": "completed",
            "progress_percentage": 100
        }
        response = requests.patch(f"{API_BASE}/tasks/{task_id}", json=completion_data)
        if response.status_code == 200:
            completed_task = response.json()['task']
            print(f"✅ Task completed successfully")
            print(f"   Status: {completed_task['status']}")
            print(f"   Completed at: {completed_task.get('completed_at', 'N/A')}")
        else:
            print(f"❌ Failed to complete task: {response.status_code}")
    except Exception as e:
        print(f"❌ Error completing task: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Task Management System Test Complete!")
    print("\nNext steps:")
    print("1. Run the SQL migration: tasks_system_migration.sql")
    print("2. Start the Flask app: python app.py")
    print("3. Navigate to /tasks to see the full interface")
    print("4. Create tasks and test the integration with prospects")

def test_database_schema():
    """Test if the database schema is properly set up"""
    print("\n🗄️  Database Schema Test")
    print("-" * 30)
    
    # This would require a database connection
    # For now, just print the expected tables
    expected_tables = [
        "sales_tasks",
        "task_comments", 
        "task_templates"
    ]
    
    print("Expected tables:")
    for table in expected_tables:
        print(f"  ✓ {table}")
    
    print("\nTo verify schema, run:")
    print("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")

if __name__ == "__main__":
    print("🚀 DOUANO Task Management System Test Suite")
    print("=" * 60)
    
    # Test database schema expectations
    test_database_schema()
    
    # Test API endpoints (requires running Flask app)
    print("\n⚠️  Note: API tests require the Flask app to be running")
    print("Start the app with: python app.py")
    print("Then run this script again to test the API endpoints")
    
    # Uncomment the line below when the Flask app is running
    # test_task_system()
