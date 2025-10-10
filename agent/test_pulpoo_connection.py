#!/usr/bin/env python3
"""
Test Pulpoo API Connection
==========================
This script tests the Pulpoo API connection with dummy data.
"""

import requests
import os
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv

# Load environment variables
load_dotenv(".env")

PULPOO_API_KEY = os.getenv("PULPOO_API_KEY")

def test_pulpoo_connection():
    """Test the Pulpoo API connection with dummy data."""
    
    print("=" * 60)
    print("PULPOO API CONNECTION TEST")
    print("=" * 60)
    print()
    
    # Check if API key is set
    if not PULPOO_API_KEY:
        print("❌ ERROR: PULPOO_API_KEY not found in .env file")
        print("Please add your Pulpoo API key to the .env file")
        return False
    
    print(f"✓ API Key found: {PULPOO_API_KEY[:10]}... (hidden for security)")
    print()
    
    # Create dummy data
    deadline_dt = datetime.now(pytz.UTC) + timedelta(hours=24)
    deadline = deadline_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Test payload with a single user (API expects string, not array)
    payload = {
        "title": "Test Task - Summit Demo",
        "description": "This is a test task created by the Pulpoo API connection test script. Testing assignment to a single user.",
        "assigned_to_email":  "perezmd324@gmail.com",
        "deadline": deadline,
        "importance": "HIGH",
        "canal": "Engineering"
    }
    
    print("📝 Test Data:")
    print(f"   Title: {payload['title']}")
    print(f"   Description: {payload['description']}")
    print(f"   Assigned to: {payload['assigned_to_email']}")
    print(f"   Deadline: {deadline}")
    print(f"   Importance: {payload['importance']}")
    print(f"   Canal: {payload['canal']}")
    print()
    
    # API endpoint and headers
    url = "https://api.pulpoo.com/v1/external/tasks/create"
    headers = {
        "X-API-Key": PULPOO_API_KEY,
        "Content-Type": "application/json"
    }
    
    print("🔄 Sending request to Pulpoo API...")
    print(f"   Endpoint: {url}")
    print()
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        print("📥 Response Received:")
        print(f"   Status Code: {response.status_code}")
        print()
        
        # Parse response
        try:
            response_data = response.json()
            print("📄 Response Data:")
            print(f"   {response_data}")
            print()
        except:
            print("📄 Response Text:")
            print(f"   {response.text}")
            print()
        
        # Check if successful
        if response.status_code in [200, 201]:
            print("=" * 60)
            print("✅ SUCCESS! Task created successfully in Pulpoo")
            print("=" * 60)
            print()
            print("✓ Connection is working properly")
            print("✓ User assigned correctly:")
            print(f"  • {payload['assigned_to_email']}")
            return True
        else:
            print("=" * 60)
            print("❌ ERROR: Task creation failed")
            print("=" * 60)
            print()
            print(f"Status Code: {response.status_code}")
            print(f"Error Message: {response_data.get('error', 'Unknown error') if 'response_data' in locals() else response.text}")
            
            # Provide helpful debugging info
            if response.status_code == 401:
                print()
                print("🔍 Debugging Tips:")
                print("  • Check that your PULPOO_API_KEY is correct")
                print("  • Verify the API key starts with 'cwz'")
                print("  • Make sure the API key is active in your Pulpoo account")
            elif response.status_code == 403:
                print()
                print("🔍 Debugging Tips:")
                if 'App not installed' in response.text:
                    print("  • The Pulpoo app/integration needs to be installed in your organization")
                    print("  • Contact your Pulpoo administrator to install the external API app")
                    print("  • Verify the API key is associated with an organization")
                else:
                    print("  • Check that your API key has the correct permissions")
                    print("  • Verify you have access to create tasks in Pulpoo")
                    print("  • Contact your Pulpoo administrator for access")
            elif response.status_code == 400:
                print()
                print("🔍 Debugging Tips:")
                print("  • Check the request payload format")
                print("  • Verify all email addresses are valid Pulpoo users")
                print("  • Ensure the deadline format is correct (ISO 8601)")
            elif response.status_code == 404:
                print()
                print("🔍 Debugging Tips:")
                print("  • Verify the API endpoint URL is correct")
                print("  • Check if the Pulpoo API version has changed")
            
            return False
            
    except requests.exceptions.Timeout:
        print("=" * 60)
        print("❌ ERROR: Request timeout")
        print("=" * 60)
        print()
        print("The request took too long to complete.")
        print("This could indicate network issues or the Pulpoo API is slow/down.")
        return False
        
    except requests.exceptions.ConnectionError:
        print("=" * 60)
        print("❌ ERROR: Connection failed")
        print("=" * 60)
        print()
        print("Could not connect to the Pulpoo API.")
        print("Please check your internet connection.")
        return False
        
    except Exception as e:
        print("=" * 60)
        print("❌ ERROR: Unexpected error")
        print("=" * 60)
        print()
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_pulpoo_connection()
    exit(0 if success else 1)

