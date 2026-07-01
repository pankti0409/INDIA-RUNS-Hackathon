# Honeypot & Risk Analysis Report

This report audits the continuous Risk Engine's performance on the candidate pool.

## Summary Metrics

- **Total top candidates analyzed**: 50
- **Candidates with High Risk (p >= 0.50)**: 7
- **Candidates with Medium Risk (0.25 <= p < 0.50)**: 3

## Risk Details for Flagged Candidates

| Candidate ID | Risk Prob | Risk Reasons | Final Score |
| :--- | :--- | :--- | :--- |
| CAND_0000027 | 0.3317 | 1 assessment contradictions (p=0.33) | 0.2017 |
| CAND_0000001 | 0.3561 | 1 assessment contradictions (p=0.33) | 0.1614 |
| CAND_0000045 | 0.7596 | work-education overlap of 6.0 yrs (p=0.75) | 0.0384 |
| CAND_0000011 | 0.3438 | 1 assessment contradictions (p=0.33) | 0.0010 |
| CAND_0000017 | 0.8782 | work-education overlap of 8.0 yrs (p=0.88) | 0.0010 |
| CAND_0000030 | 0.5139 | work-education overlap of 4.0 yrs (p=0.50) | 0.0010 |
| CAND_0000037 | 0.5098 | work-education overlap of 4.0 yrs (p=0.50) | 0.0010 |
| CAND_0000041 | 0.7408 | completeness vs activity paradox (p=0.25); work-education overlap of 5.0 yrs (p=0.65) | 0.0010 |
| CAND_0000049 | 0.6579 | work-education overlap of 5.0 yrs (p=0.65) | 0.0010 |
| CAND_0000050 | 0.6617 | work-education overlap of 5.0 yrs (p=0.65) | 0.0010 |

## Risk Engine Justification
- Timeline inconsistencies are detected through career dates mismatch.
- Claimed expert skills with zero experience or low assessment scores trigger assessment risks.
- Title mismatches prevent non-technical profiles from keyword-stuffing their way to the top.