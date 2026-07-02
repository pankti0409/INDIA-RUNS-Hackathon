# Honeypot & Risk Analysis Report

This report audits the continuous Risk Engine's performance on the candidate pool.

## Summary Metrics

- **Total top candidates analyzed**: 100
- **Candidates with High Risk (p >= 0.50)**: 0
- **Candidates with Medium Risk (0.25 <= p < 0.50)**: 3

## Risk Details for Flagged Candidates

| Candidate ID | Risk Prob | Risk Reasons | Final Score |
| :--- | :--- | :--- | :--- |
| CAND_0006557 | 0.2953 | work-education overlap of 3.0 yrs (p=0.30) | 0.7570 |
| CAND_0057563 | 0.2953 | work-education overlap of 3.0 yrs (p=0.30) | 0.7320 |
| CAND_0040200 | 0.2715 | completeness vs activity paradox (p=0.27) | 0.7244 |

## Risk Engine Justification
- Timeline inconsistencies are detected through career dates mismatch.
- Claimed expert skills with zero experience or low assessment scores trigger assessment risks.
- Title mismatches prevent non-technical profiles from keyword-stuffing their way to the top.