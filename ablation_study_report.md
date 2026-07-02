# Automated Ablation Study & Subsystem Evaluation Report

This report measures the impact of removing different candidate intelligence subsystems on ranking quality.

| Ranking Configuration | NDCG@10 | NDCG@20 | MRR | Description |
| :--- | :--- | :--- | :--- | :--- |
| Full Blended System | 0.9997 | 0.9998 | 1.0000 | Baseline configuration |
| Ablation: No Cross-Encoder | 0.9898 | 0.9905 | 1.0000 | Set cross-encoder score to hybrid similarity |
| Ablation: No Candidate Intelligence | 0.9873 | 0.9831 | 1.0000 | Set maturity and project complexity to defaults |
| Ablation: No Company Intelligence | 0.9865 | 0.9846 | 1.0000 | Set industry relevance and company quality to defaults |
| Ablation: No Behavioral Boosters | 0.9785 | 0.9813 | 1.0000 | Disable hireability and active recently flags |
| Ablation: No LTR Blending | 1.0000 | 1.0000 | 1.0000 | Disable LightGBM model prediction |