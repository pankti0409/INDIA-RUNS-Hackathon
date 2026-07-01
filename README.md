# Redrob Intelligent Candidate Discovery & Ranking System

## Overview

This system ranks 100,000 candidates for the **Senior AI/ML Engineer (Ranking & Retrieval)** role at Redrob, producing a top-100 ranked submission CSV that maximizes NDCG@10 and NDCG@50.

## Key Design Decisions

### Why Title is the #1 Signal
The job description explicitly states: *"A candidate who has all the AI keywords listed as skills but whose title is 'Marketing Manager' is not a fit."* This is the most important signal — we weight `title_score` at 28% and apply heavy penalties (88% reduction) for disqualifier titles.

### Honeypot Detection
The dataset contains ~80 honeypot candidates. Our detection flags:
1. **Keyword stuffers**: Non-technical title + 5+ AI skills = strong honeypot signal
2. **Impossible profiles**: Expert skill with 0 months duration
3. **Assessment contradictions**: Claims advanced, assessment score < 40
4. **Timeline errors**: Career duration mismatch > 12 months

### Behavioral Signals as Availability Multipliers
A perfect-on-paper candidate who hasn't logged in for 180+ days with a 5% recruiter response rate is not actually available. We model `availability_score` as a modifier that can boost or suppress scores.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Rank 100K candidates (< 5 min on CPU, 16GB RAM)
python rank.py --candidates ./candidates.jsonl --out ./submission.csv

# Validate the submission
python validate_submission.py submission.csv
```

## Project Structure

```
├── rank.py                          # Main CLI entry point
├── redrob_ranker/
│   ├── config.py                    # JD requirements, weights, skill taxonomy
│   ├── engines/
│   │   ├── feature_engine.py        # 50+ feature extraction
│   │   ├── honeypot_engine.py       # Trap candidate detection
│   │   ├── behavioral_engine.py     # 23 Redrob signal composite scores
│   │   └── ranking_engine.py        # Ensemble scoring
│   ├── utils/
│   │   ├── data_loader.py           # Efficient JSONL loading
│   │   └── explanation_engine.py    # Auto-reasoning generation
│   └── api/
│       └── main.py                  # FastAPI backend
├── requirements.txt
├── Dockerfile
└── submission_metadata.yaml
```

## Scoring Formula

```
final_score = (
    0.28 × title_score +          # JD: title is the decisive signal
    0.22 × core_skill_score +      # AI/retrieval skill match
    0.15 × experience_score +      # 5-9yr, product company background
    0.12 × behavioral_score +      # Availability + engagement
    0.07 × education_score +       # Institution tier + field relevance
    0.06 × assessment_score +      # Validated platform scores
    0.05 × location_score +        # India/preferred cities
    0.05 × github_score            # Open source activity
) × penalty_multipliers × bonus_multipliers
```

**Penalty multipliers**:
- Disqualifier title (HR, Marketing, Accountant, etc.): ×0.12
- Pure consulting background (entire career at TCS/Infosys/Wipro/etc.): ×0.45
- Honeypot (probability > 0.75): ×0.05

## Performance

| Stage | Time |
|-------|------|
| Load 100K candidates | ~21s |
| Score 100K candidates | ~55s |
| Sort + write CSV | <1s |
| **Total** | **~80s** |

Well within the 5-minute (300s) constraint.

## API Backend

```bash
# Start FastAPI server
uvicorn redrob_ranker.api.main:app --reload --port 8000
```

Available endpoints:
- `GET /api/health` — System health
- `GET /api/results` — Get top-100 ranking
- `POST /api/rank` — Rank uploaded candidates (≤500 for sandbox)
- `GET /api/candidate/{id}` — Candidate detail
- `GET /api/download` — Download submission CSV

## Reproducing the Submission

```bash
python rank.py --candidates ./candidates.jsonl --out ./submission.csv
```

Runtime: ~80 seconds on CPU. No GPU, no network calls, no external APIs.

## Compute Constraints Compliance

- ✅ CPU only (no GPU)
- ✅ ~500MB RAM peak (well within 16GB)
- ✅ ~80 seconds total (well within 5 minutes)
- ✅ No network calls during ranking
- ✅ Single command reproducibility
