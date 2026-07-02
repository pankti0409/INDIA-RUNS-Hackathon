FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY redrob_ranker/ ./redrob_ranker/
COPY rank.py .
COPY candidates.jsonl .

# Run ranking
CMD ["python", "rank.py", "--candidates", "./candidates.jsonl", "--out", "./submission.csv"]
