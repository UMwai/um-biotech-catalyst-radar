
import requests
from datetime import datetime, timedelta

BASE_URL = "https://clinicaltrials.gov/api/v2/studies"

def test_query():
    today = datetime.now()
    end_date = today + timedelta(days=90)
    
    # Try filter.phases (plural)
    print("Testing with filter.phases...")
    params = {
        "format": "json",
        "pageSize": 5,
        "filter.overallStatus": "RECRUITING,ACTIVE_NOT_RECRUITING",
        "filter.phases": "PHASE2,PHASE3", # Plural?
        "fields": "NCTId,Phase",
    }
    
    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(response.json()['studies'][0] if response.json()['studies'] else "No studies found")
        else:
            print(response.text)
    except Exception as e:
        print(f"Error: {e}")

    # Try putting phase in query.term
    print("\nTesting phase in query.term...")
    params_term = {
        "format": "json",
        "pageSize": 5,
        "filter.overallStatus": "RECRUITING,ACTIVE_NOT_RECRUITING",
        "query.term": "AREA[Phase]PHASE2 OR AREA[Phase]PHASE3",
        "fields": "NCTId,Phase",
    }
    try:
        response = requests.get(BASE_URL, params=params_term, timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code != 200:
            print(response.text)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_query()
