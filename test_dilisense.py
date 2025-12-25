#!/usr/bin/env python3
"""Test Dilisense API directly"""

import os
import httpx
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("DILISENSE_API_KEY")

if not api_key:
    print("❌ DILISENSE_API_KEY not found in .env")
    exit(1)

print(f"✅ API Key found: {api_key[:10]}...{api_key[-5:]}")

# Test with a known name
test_names = [
    "NAVIN RAMGOOLAM",
    "Vladimir Putin",
    "John Smith"
]

for name in test_names:
    print(f"\n{'='*50}")
    print(f"Testing: {name}")
    print('='*50)
    
    try:
        response = httpx.get(
            "https://api.dilisense.com/v1/checkIndividual",
            params={
                "names": name,
                "fuzzy_search": 1,
                "search_type": "individual"
            },
            headers={
                "x-api-key": api_key
            },
            timeout=30.0
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Total Hits: {result.get('total_hits', 0)}")
            
            for record in result.get('found_records', [])[:3]:
                print(f"\n  📌 Match: {record.get('name')}")
                print(f"     Type: {record.get('source_type')}")
                print(f"     Entity: {record.get('entity_type')}")
                if record.get('positions'):
                    print(f"     Positions: {record.get('positions', [])[:2]}")
        
        elif response.status_code == 429:
            print("⚠️ RATE LIMITED (429) - Too many requests")
            print("   Wait a few minutes before trying again")
            print(f"   Response: {response.text[:200]}")
        
        elif response.status_code == 401:
            print("❌ UNAUTHORIZED (401) - Invalid API key")
        
        elif response.status_code == 403:
            print("❌ FORBIDDEN (403) - API key doesn't have access")
        
        else:
            print(f"❌ Error: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

print("\n" + "="*50)
print("Test complete")
