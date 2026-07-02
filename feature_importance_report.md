# Feature Importance & Sensitivity Analysis Report

This report outlines the relative importance and contribution of different features to the final candidate ranking.

## Core Engine Feature Weights
The final ranking uses a multiplicative cascade score. The relevance component itself is weighted as follows:
- **Hybrid Retrieval Score (Dense + BM25)**: 40% of Relevance
- **Cross-Encoder Score (ms-marco-MiniLM)**: 40% of Relevance
- **Role-Specific Experience Depth**: 20% of Relevance

## Top 100 Feature Averages
Below are the average normalized values for key features across the top 100 candidates:

| Feature Dimension | Average Score in Top 100 |
| :--- | :--- |
| Overall Relevance Score | 0.4739 |
| Hybrid Retrieval Score | 0.4682 |
| Cross-Encoder Score | 0.4682 |
| Role-Specific Depth | 0.5846 |
| Hireability Probability | 0.8108 |
| Trust Score | 0.7593 |
| Risk Probability | 0.0123 |
| Core Skill Match Score | 0.0000 |
| Title Match Score | 0.9579 |
| Years of Experience Score | 0.9895 |
| Career Growth Score | 0.4234 |
| GitHub Activity Score | 0.4325 |

## Sensitivity Audit Insights
1. **Relevance Multipliers**: Relevance scores drive the base score, but notice period and activity decay quickly eliminate non-viable candidates.
2. **Fraud Detection**: The continuous Risk score successfully demotes high-risk keyword stuffers without hard-filtering valid outliers.