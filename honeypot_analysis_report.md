# Honeypot & Risk Analysis Report

This report audits the continuous Risk Engine's performance on the candidate pool.

## Summary Metrics

- **Total top candidates analyzed**: 100
- **Candidates with High Risk (p >= 0.50)**: 0
- **Candidates with Medium Risk (0.25 <= p < 0.50)**: 3

## Risk Details for Flagged Candidates

| Candidate ID | Risk Prob | Risk Reasons | Final Score |
| :--- | :--- | :--- | :--- |
| CAND_0057563 | 0.2953 | work-education overlap of 3.0 yrs (p=0.30) | 0.4182 |
| CAND_0006557 | 0.2953 | work-education overlap of 3.0 yrs (p=0.30) | 0.3428 |
| CAND_0007009 | 0.2954 | work-education overlap of 3.0 yrs (p=0.30) | 0.3233 |

## Risk Engine Justification
- Timeline inconsistencies are detected through career dates mismatch.
- Claimed expert skills with zero experience or low assessment scores trigger assessment risks.
- Title mismatches prevent non-technical profiles from keyword-stuffing their way to the top.