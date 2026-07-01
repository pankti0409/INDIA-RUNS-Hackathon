import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Load first 5 candidates from the full dataset
with open('candidates.jsonl', 'r', encoding='utf-8') as f:
    lines = [f.readline() for _ in range(10)]

titles_seen = set()
for i, line in enumerate(lines):
    c = json.loads(line)
    title = c["profile"]["current_title"]
    yoe = c["profile"]["years_of_experience"]
    country = c["profile"]["country"]
    skills = [s["name"] for s in c["skills"]]
    sig = c["redrob_signals"]
    
    print(f"=== Candidate {i+1}: {c['candidate_id']} ===")
    print(f"  Title: {title}, YoE: {yoe}, Country: {country}")
    print(f"  Skills ({len(skills)}): {skills[:8]}")
    print(f"  open_to_work: {sig['open_to_work_flag']}, last_active: {sig['last_active_date']}")
    print(f"  response_rate: {sig['recruiter_response_rate']}, github_score: {sig['github_activity_score']}")
    print(f"  profile_completeness: {sig['profile_completeness_score']}")
    print(f"  assessment_scores: {sig['skill_assessment_scores']}")
    print()

# Count lines
print("Counting total lines...")
with open('candidates.jsonl', 'r') as f:
    count = sum(1 for line in f if line.strip())
print(f"Total candidates: {count}")
