"""
data_loader.py — Fast JSONL loading for 100K candidate profiles
Uses standard json for compatibility, Polars for analysis.
"""
import json
import logging
import time
from pathlib import Path
from typing import Iterator, List, Optional

logger = logging.getLogger(__name__)


def load_candidates_streaming(jsonl_path: str) -> Iterator[dict]:
    """
    Stream candidates line by line from JSONL file, or load as JSON array if formatted as such.
    Memory efficient for JSONL, loads all at once for JSON arrays.
    """
    path = Path(jsonl_path)
    if not path.exists():
        raise FileNotFoundError(f"Candidates file not found: {jsonl_path}")

    logger.info(f"Streaming candidates from {path}")
    
    # Peek at first character to check if it's a JSON array
    is_array = False
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line_stripped = line.strip()
                if line_stripped:
                    if line_stripped.startswith("["):
                        is_array = True
                    break
    except Exception:
        pass

    if is_array:
        logger.info(f"Detected JSON array format for {path}, loading all at once...")
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                candidates = json.load(f)
                if isinstance(candidates, list):
                    for c in candidates:
                        yield c
                else:
                    yield candidates
            return
        except Exception as e:
            logger.warning(f"Failed to load JSON array from {path}: {e}. Falling back to line-by-line.")

    count = 0
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                candidate = json.loads(line)
                count += 1
                yield candidate
            except json.JSONDecodeError as e:
                logger.warning(f"Skipping malformed line {count}: {e}")
    logger.info(f"Streamed {count} candidates")


def load_candidates_batch(jsonl_path: str, batch_size: int = 5000) -> Iterator[List[dict]]:
    """
    Load candidates in batches for memory-efficient processing.
    """
    batch = []
    for candidate in load_candidates_streaming(jsonl_path):
        batch.append(candidate)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def load_all_candidates(jsonl_path: str) -> List[dict]:
    """
    Load all candidates into memory. ~465MB for 100K candidates.
    Works within 16GB constraint.
    """
    t0 = time.time()
    logger.info(f"Loading all candidates from {jsonl_path}...")
    candidates = list(load_candidates_streaming(jsonl_path))
    elapsed = time.time() - t0
    logger.info(f"Loaded {len(candidates)} candidates in {elapsed:.1f}s")
    return candidates


def load_sample(jsonl_path: str, n: int = 100) -> List[dict]:
    """Load first n candidates for testing."""
    candidates = []
    for c in load_candidates_streaming(jsonl_path):
        candidates.append(c)
        if len(candidates) >= n:
            break
    return candidates
