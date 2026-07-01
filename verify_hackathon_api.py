import requests
import json
import time

url = "http://127.0.0.1:8124/api/hackathon/rank"

print("Triggering One-Click Hackathon Ranking API...")
print("This will process the candidates and job description using fallback defaults.")

t_start = time.time()
try:
    # Trigger post request with no files (to test the workspace fallbacks)
    res = requests.post(url)
    t_end = time.time()
    
    print(f"Response status code: {res.status_code}")
    print(f"Total response time: {t_end - t_start:.2f} seconds")
    
    if res.status_code == 200:
        data = res.json()
        print("\nAPI Response Summary:")
        print(f"Status: {data.get('status')}")
        print(f"Total Candidates: {data.get('total_candidates')}")
        print(f"Malformed Candidates: {data.get('malformed_candidates_count')}")
        print(f"Validation Errors: {data.get('validation_errors_count')}")
        
        results = data.get("results", [])
        print(f"Ranked Results Count: {len(results)}")
        
        if results:
            print("\nTop 5 Ranked Candidates:")
            for r in results[:5]:
                print(f"Rank {r['rank']}: {r['candidate_id']} | Score: {r['score']*100:.2f}% | Title: {r['title']}")
                
        reports = data.get("reports", {})
        print("\nGenerated Reports:")
        for report_key, text in reports.items():
            first_few_lines = "\n".join(text.splitlines()[:3])
            print(f"- {report_key} ({len(text)} chars):\n{first_few_lines}\n...")
            
    else:
        print("Error details:")
        print(res.text)
        
except Exception as e:
    print(f"Request failed: {e}")
