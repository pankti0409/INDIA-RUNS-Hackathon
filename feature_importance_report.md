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
| Overall Relevance Score | 0.6093 |
| Hybrid Retrieval Score | 0.8469 |
| Cross-Encoder Score | 0.6506 |
| Role-Specific Depth | 0.6455 |
| Hireability Probability | 0.8213 |
| Trust Score | 0.7770 |
| Risk Probability | 0.0112 |
| Core Skill Match Score | 0.3138 |
| Title Match Score | 0.9551 |
| Years of Experience Score | 0.9460 |
| Career Growth Score | 0.4340 |
| GitHub Activity Score | 0.4896 |

## Sensitivity Audit Insights
1. **Relevance Multipliers**: Relevance scores drive the base score, but notice period and activity decay quickly eliminate non-viable candidates.
2. **Fraud Detection**: The continuous Risk score successfully demotes high-risk keyword stuffers without hard-filtering valid outliers.