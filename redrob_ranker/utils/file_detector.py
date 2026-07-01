"""
file_detector.py — Smart File Detector & Classifier
Automatically detects file types by inspecting extensions, byte signatures, and structured headers.
"""
import gzip
import io
import json
import re
import zipfile
from pathlib import Path
from typing import Dict

def detect_file_type(content: bytes, filename: str) -> Dict[str, any]:
    """
    Classifies a file based on filename, extension, and content byte headers.
    Returns a dict with:
      - type: "Candidate Dataset" | "Job Description" | "Schema Definition" | "Resume Collection" | "Submission File" | "Unknown File"
      - size_bytes: int
      - filename: str
      - error: Optional[str]
    """
    fn_lower = filename.lower()
    size_bytes = len(content)
    result = {
        "filename": filename,
        "size_bytes": size_bytes,
        "type": "Unknown File",
        "error": None
    }

    if size_bytes == 0:
        result["type"] = "Unknown File"
        result["error"] = "File is empty"
        return result

    # 1. Unpack GZIP if applicable
    decompressed_content = content
    is_gzipped = False
    if fn_lower.endswith(".gz"):
        try:
            decompressed_content = gzip.decompress(content)
            is_gzipped = True
            fn_lower = fn_lower[:-3]  # Strip .gz for downstream checks
        except Exception as e:
            result["error"] = f"Corrupted GZIP format: {e}"
            return result

    ext = Path(fn_lower).suffix

    # 2. Check ZIP archive
    if ext == ".zip":
        try:
            with zipfile.ZipFile(io.BytesIO(decompressed_content)) as z:
                names = z.namelist()
                if not names:
                    result["error"] = "Empty ZIP archive"
                    return result
                
                # Check what type of files are in the zip
                has_resumes = any(n.lower().endswith((".pdf", ".docx")) for n in names)
                has_datasets = any(n.lower().endswith((".jsonl", ".json", ".csv", ".xlsx")) for n in names)
                
                if has_resumes:
                    result["type"] = "Resume Collection"
                elif has_datasets:
                    result["type"] = "Candidate Dataset"
                else:
                    result["type"] = "Unknown File"
                    result["error"] = "No supported candidate datasets or resumes found in ZIP"
                return result
        except Exception as e:
            result["error"] = f"Corrupted ZIP archive: {e}"
            return result

    # 3. Check JSON / JSONL
    if ext in (".json", ".jsonl"):
        try:
            text = decompressed_content.decode("utf-8", errors="replace").strip()
            if ext == ".json":
                # Could be a Schema Definition or a Candidate Dataset JSON array
                try:
                    data = json.loads(text)
                    if isinstance(data, dict):
                        if "$schema" in data or "properties" in data:
                            result["type"] = "Schema Definition"
                            return result
                        # Single candidate wrap
                        if any(k in data for k in ["candidate_id", "profile", "skills"]):
                            result["type"] = "Candidate Dataset"
                            return result
                    elif isinstance(data, list) and len(data) > 0:
                        first = data[0]
                        if isinstance(first, dict) and any(k in first for k in ["candidate_id", "profile", "skills"]):
                            result["type"] = "Candidate Dataset"
                            return result
                except json.JSONDecodeError:
                    pass
            
            # Treat as JSONL
            first_line = text.split("\n")[0].strip()
            try:
                line_data = json.loads(first_line)
                if isinstance(line_data, dict):
                    if "$schema" in line_data or "properties" in line_data:
                        result["type"] = "Schema Definition"
                    elif any(k in line_data for k in ["candidate_id", "profile", "skills", "redrob_signals"]):
                        result["type"] = "Candidate Dataset"
                    else:
                        result["type"] = "Unknown File"
                else:
                    result["type"] = "Unknown File"
            except Exception:
                result["type"] = "Unknown File"
                result["error"] = "Invalid JSON/JSONL formatting"
            return result
        except Exception as e:
            result["error"] = f"Failed to read JSON/JSONL encoding: {e}"
            return result

    # 4. Check CSV / Excel
    if ext in (".csv", ".xlsx", ".xls"):
        # For CSV/Excel, inspect columns/headers
        try:
            if ext == ".csv":
                text = decompressed_content.decode("utf-8", errors="replace")
                first_line = text.split("\n")[0].lower()
                headers = [h.strip().replace('"', '').replace("'", "") for h in first_line.split(",")]
            else:
                # Excel file
                import pandas as pd
                df = pd.read_excel(io.BytesIO(decompressed_content), nrows=1)
                headers = [str(col).lower().strip() for col in df.columns]

            # Submission file headers check
            if "candidate_id" in headers and "rank" in headers and "score" in headers:
                result["type"] = "Submission File"
            elif any(col in headers for col in ["skills", "experience", "yoe", "current_title", "candidate_id", "name", "anonymized_name"]):
                result["type"] = "Candidate Dataset"
            else:
                result["type"] = "Unknown File"
                result["error"] = "Unrecognized CSV/Excel column structure"
            return result
        except Exception as e:
            result["error"] = f"Failed to parse tabular file: {e}"
            return result

    # 5. Check Markdown / PDF / Text
    if ext in (".md", ".txt", ".pdf", ".docx"):
        # Extract text content
        try:
            from redrob_ranker.engines.resume_ingestion_engine import read_file_to_text
            text_content = read_file_to_text(decompressed_content, filename)
            text_lower = text_content.lower()

            # Classifier heuristics for Job Description vs. Resume
            jd_keywords = ["job description", "requirements", "qualifications", "responsibilities", "nice to have", "experience range"]
            resume_keywords = ["education", "work experience", "projects", "phone", "email", "skills", "contact", "summary"]

            jd_hits = sum(1 for kw in jd_keywords if kw in text_lower)
            resume_hits = sum(1 for kw in resume_keywords if kw in text_lower)

            if jd_hits >= 2 or (ext == ".md" and jd_hits >= 1):
                result["type"] = "Job Description"
            elif resume_hits >= 2 or ext in (".pdf", ".docx"):
                result["type"] = "Resume Collection"
            else:
                result["type"] = "Unknown File"
            return result
        except Exception as e:
            result["error"] = f"Failed to extract document text: {e}"
            return result

    return result


def profile_file_metadata(content: bytes, filename: str, file_type: str) -> dict:
    """
    Profiles a classified file and returns detailed metadata for preview and validation.
    """
    import json
    import gzip
    from redrob_ranker.utils.data_ingestion import stream_candidates_from_bytes
    from redrob_ranker.engines.jd_ingestion_engine import ingest_jd
    from redrob_ranker.utils.schema_validator import SchemaValidator
    
    metadata = {}
    
    # Unpack GZIP if it was compressed
    decompressed_content = content
    if filename.lower().endswith(".gz"):
        try:
            decompressed_content = gzip.decompress(content)
        except Exception:
            pass
            
    if file_type == "Candidate Dataset":
        try:
            # ── Fast streaming preview: only read up to PROFILE_LIMIT records ──
            PROFILE_LIMIT = 500
            SAMPLE_LIMIT = 10

            sample_records = []
            schema_keys = set()
            field_counts = {}
            standard_keys = ["candidate_id", "profile", "career_history", "skills", "redrob_signals"]
            missing_counts = {k: 0 for k in standard_keys}
            scanned = 0

            for c in stream_candidates_from_bytes(content, filename):
                if scanned < SAMPLE_LIMIT:
                    sample_records.append(c)
                for k in c.keys():
                    schema_keys.add(k)
                    field_counts[k] = field_counts.get(k, 0) + 1
                for k in standard_keys:
                    if k not in c or not c[k]:
                        missing_counts[k] += 1
                scanned += 1
                if scanned >= PROFILE_LIMIT:
                    break

            # Estimate total_records from file size when we capped the scan
            capped = scanned >= PROFILE_LIMIT
            if capped:
                # Rough estimate: bytes_per_record * total_file_size
                decompressed_size = len(decompressed_content)
                avg_record_size = max(1, decompressed_size // max(1, scanned))
                total_records = decompressed_size // avg_record_size
            else:
                total_records = scanned

            field_dist = {k: round(v / max(1, scanned), 4) for k, v in field_counts.items()}

            # Skip full schema validation during preview for performance
            malformed_count = 0

            metadata = {
                "total_records": total_records,
                "sample_records": sample_records,
                "schema_preview": sorted(list(schema_keys)),
                "field_distribution": field_dist,
                "missing_field_analysis": missing_counts,
                "malformed_records_count": malformed_count,
                "profiling_note": f"Stats based on first {scanned} records" + (f" (est. {total_records} total)" if capped else "")
            }
        except Exception as e:
            metadata["error"] = f"Candidate Dataset profiling failed: {e}"
            
    elif file_type == "Job Description":
        try:
            text = decompressed_content.decode("utf-8", errors="replace")
            jd_data = ingest_jd(text=text, use_llm=False)
            metadata = {
                "job_title": jd_data.get("job_title", "Unknown"),
                "seniority": jd_data.get("seniority", "Unknown"),
                "yoe_min": jd_data.get("years_of_experience_min", 3),
                "yoe_max": jd_data.get("years_of_experience_max", 10),
                "location": jd_data.get("location", "India"),
                "work_mode": jd_data.get("work_mode", "hybrid"),
                "required_skills": jd_data.get("required_skills", []),
                "nice_to_have_skills": jd_data.get("nice_to_have_skills", [])
            }
        except Exception as e:
            metadata["error"] = f"Job Description profiling failed: {e}"
            
    elif file_type == "Schema Definition":
        try:
            text = decompressed_content.decode("utf-8", errors="replace")
            schema_data = json.loads(text)
            properties = schema_data.get("properties", {})
            metadata = {
                "title": schema_data.get("title", "Candidate Schema"),
                "properties_count": len(properties),
                "required_fields": schema_data.get("required", []),
                "properties": sorted(list(properties.keys()))
            }
        except Exception as e:
            metadata["error"] = f"Schema Definition profiling failed: {e}"
            
    elif file_type == "Submission File":
        try:
            text = decompressed_content.decode("utf-8", errors="replace")
            lines = [l for l in text.split("\n") if l.strip()]
            metadata = {
                "rows_count": max(0, len(lines) - 1)  # Subtract header row
            }
        except Exception as e:
            metadata["error"] = f"Submission profiling failed: {e}"
            
    return metadata
