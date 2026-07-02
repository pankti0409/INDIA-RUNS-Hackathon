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
| Overall Relevance Score | 0.1329 |
| Hybrid Retrieval Score | 0.6875 |
| Cross-Encoder Score | 0.0366 |
| Role-Specific Depth | 0.1990 |
| Hireability Probability | 0.7365 |
| Trust Score | 0.5576 |
| Risk Probability | 0.1331 |
| Core Skill Match Score | 0.0178 |
| Title Match Score | 0.1983 |
| Years of Experience Score | 0.7814 |
| Career Growth Score | 0.2843 |
| GitHub Activity Score | 0.2397 |

## Sensitivity Audit Insights
1. **Relevance Multipliers**: Relevance scores drive the base score, but notice period and activity decay quickly eliminate non-viable candidates.
2. **Fraud Detection**: The continuous Risk score successfully demotes high-risk keyword stuffers without hard-filtering valid outliers.