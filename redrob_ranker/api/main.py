"""
main.py — FastAPI application for Redrob Ranker
Provides REST API for the ranking system.
"""
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from redrob_ranker.config import TOP_N_OUTPUT, TOP_CANDIDATES

logger = logging.getLogger(__name__)

# Global state for cached results
_cached_results: Optional[list] = None
_submission_path = Path("./submission.csv")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: Load pre-computed results if available."""
    global _cached_results
    if _submission_path.exists():
        logger.info(f"Pre-computed results found at {_submission_path}")
    yield


app = FastAPI(
    title="Redrob Candidate Ranking API",
    description="Intelligent Candidate Discovery & Ranking for the Redrob ML Engineer JD",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "submission_ready": _submission_path.exists(),
    }


@app.get("/api/results")
def get_results():
    """Return the current top-100 ranking from submission.csv."""
    if not _submission_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Submission CSV not found. Run rank.py first.",
        )

    import csv
    results = []
    with open(_submission_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            results.append({
                "candidate_id": row["candidate_id"],
                "rank": int(row["rank"]),
                "score": float(row["score"]),
                "reasoning": row["reasoning"],
            })

    return {
        "total": len(results),
        "results": results,
    }


@app.get("/api/candidate/{candidate_id}")
def get_candidate(candidate_id: str):
    """Get details for a specific candidate by ID."""
    candidates_path = Path("./candidates.jsonl")
    if not candidates_path.exists():
        raise HTTPException(status_code=404, detail="Candidates file not found")

    with open(candidates_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                c = json.loads(line)
                if c.get("candidate_id") == candidate_id:
                    return c
            except json.JSONDecodeError:
                continue

    raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found")


@app.get("/api/metrics")
def get_metrics():
    """Return system metrics including real candidate counts (no dummy padding)."""
    submission_exists = _submission_path.exists()
    
    real_ranked = 0
    if submission_exists:
        import csv
        with open(_submission_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Exclude dummy padding candidates from the count
                if not row.get("candidate_id", "").startswith("CAND_9990"):
                    real_ranked += 1

    # Count total pool size from candidates.jsonl (fast line count)
    pool_size = 0
    candidates_path = Path("./candidates.jsonl")
    if candidates_path.exists():
        with open(candidates_path, "r", encoding="utf-8") as f:
            pool_size = sum(1 for line in f if line.strip())

    return {
        "submission_ready": submission_exists,
        "ranked_candidates": real_ranked,
        "total_pool_size": pool_size,
        "max_output": TOP_N_OUTPUT,
    }


@app.post("/api/rank")
async def rank_uploaded(file: UploadFile = File(...)):
    """
    Rank candidates from an uploaded CSV, JSON, JSONL, XLSX, or ZIP file.
    Runs ranking on all candidates in the uploaded dataset.
    """
    from redrob_ranker.engines.ranking_engine import rank_candidates
    from redrob_ranker.utils.explanation_engine import generate_reasoning
    from redrob_ranker.utils.data_ingestion import stream_candidates_from_bytes

    content = await file.read()
    try:
        candidates = list(stream_candidates_from_bytes(content, file.filename or "candidates.jsonl"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse candidate dataset: {str(e)}")

    if not candidates:
        raise HTTPException(status_code=400, detail="No valid candidates found in upload")

    if len(candidates) > 100000:
        raise HTTPException(
            status_code=400,
            detail="API accepts candidate datasets containing ≤100,000 profiles.",
        )

    # Rank ALL candidates in the uploaded dataset
    top_n = len(candidates)
    ranked = rank_candidates(candidates, top_n=top_n)

    results = []
    for idx, (c, feat, score) in enumerate(ranked):
        rank = idx + 1
        reasoning = generate_reasoning(c, feat, score, rank)
        results.append({
            "candidate_id": c.get("candidate_id"),
            "rank": rank,
            "score": round(score, 6),
            "reasoning": reasoning,
            "name": c.get("profile", {}).get("anonymized_name", "Unknown"),
            "title": c.get("profile", {}).get("current_title", ""),
            "score_breakdown": {
                "title_score": round(feat.get("combined_title_score", 0), 4),
                "skill_score": round(feat.get("core_skill_score", 0), 4),
                "experience_score": round(feat.get("yoe_score", 0), 4),
                "behavioral_score": round(feat.get("availability_score", 0), 4),
                "education_score": round(feat.get("education_score", 0), 4),
                "github_score": round(feat.get("github_score", 0), 4),
                "honeypot_probability": round(feat.get("honeypot_probability", 0), 4),
            },
        })

    return {"total": len(results), "results": results}


@app.get("/api/download")
def download_submission():
    """Download the submission CSV."""
    if not _submission_path.exists():
        raise HTTPException(status_code=404, detail="Submission not ready yet")
    return FileResponse(
        _submission_path,
        media_type="text/csv",
        filename="submission.csv",
    )


# ─────────────────────────────────────────────────────────────
# MODULE 14 — Resume Ingestion API
# ─────────────────────────────────────────────────────────────

@app.post("/api/resume/upload")
async def upload_resume(
    file: UploadFile = File(...),
    use_llm: bool = False,
):
    """
    Module 14: Upload a single resume (PDF/DOCX/TXT/CSV/XLSX/JSON).
    Returns: parsed candidate schema + ranking score.
    """
    from redrob_ranker.engines.resume_ingestion_engine import ingest_resume
    from redrob_ranker.engines.ranking_engine import rank_candidates

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    candidate = ingest_resume(content, file.filename or "resume.pdf", use_llm=use_llm)
    if not candidate:
        raise HTTPException(status_code=422, detail="Could not extract candidate data from file")

    # Rank this candidate against the JD
    ranked = rank_candidates([candidate], top_n=1)
    score = ranked[0][2] if ranked else 0.0
    features = ranked[0][1] if ranked else {}

    return {
        "candidate_id": candidate["candidate_id"],
        "extracted_profile": candidate["profile"],
        "extracted_skills": [s["name"] for s in candidate.get("skills", [])],
        "ranking_score": round(score, 4),
        "score_pct": f"{score * 100:.1f}%",
        "schema": candidate,
    }


@app.post("/api/resume/bulk-upload")
async def bulk_upload_resumes(
    files: List[UploadFile] = File(...),
    use_llm: bool = False,
):
    """
    Module 14: Bulk upload multiple resumes.
    Returns ranked results for all uploaded candidates.
    """
    from redrob_ranker.engines.resume_ingestion_engine import ingest_resume
    from redrob_ranker.engines.ranking_engine import rank_candidates
    from redrob_ranker.utils.explanation_engine import generate_reasoning

    if len(files) > 50:
        raise HTTPException(status_code=400, detail="Max 50 files per bulk upload")

    candidates = []
    errors = []
    for f in files:
        try:
            content = await f.read()
            c = ingest_resume(content, f.filename or "resume", use_llm=use_llm)
            if c:
                candidates.append(c)
            else:
                errors.append(f"{f.filename}: extraction failed")
        except Exception as e:
            errors.append(f"{f.filename}: {str(e)}")

    if not candidates:
        raise HTTPException(status_code=422, detail="No candidates could be extracted")

    ranked = rank_candidates(candidates, top_n=len(candidates))
    results = []
    for idx, (c, feat, score) in enumerate(ranked):
        reasoning = generate_reasoning(c, feat, score, idx + 1)
        results.append({
            "rank": idx + 1,
            "candidate_id": c.get("candidate_id"),
            "name": c.get("profile", {}).get("name", "Unknown"),
            "title": c.get("profile", {}).get("current_title", ""),
            "score": round(score, 4),
            "score_pct": f"{score * 100:.1f}%",
            "reasoning": reasoning,
            "source_file": c.get("source_file", ""),
        })

    return {
        "total_uploaded": len(files),
        "successfully_parsed": len(candidates),
        "errors": errors,
        "results": results,
    }


# ─────────────────────────────────────────────────────────────
# MODULE 15 — JD Ingestion + Re-ranking API
# ─────────────────────────────────────────────────────────────

@app.post("/api/jd/parse")
async def parse_jd(
    file: Optional[UploadFile] = File(None),
    jd_text: str = "",
    use_llm: bool = False,
):
    """
    Module 15: Parse a job description from text or file.
    Returns structured JD requirements.
    """
    from redrob_ranker.engines.jd_ingestion_engine import ingest_jd

    if file:
        content = await file.read()
        jd = ingest_jd(file_bytes=content, filename=file.filename or "jd.pdf", use_llm=use_llm)
    elif jd_text:
        jd = ingest_jd(text=jd_text, use_llm=use_llm)
    else:
        raise HTTPException(status_code=400, detail="Provide either jd_text or file")

    if not jd:
        raise HTTPException(status_code=422, detail="Could not parse JD")

    return jd


# ─────────────────────────────────────────────────────────────
# MODULE 16 — Gap Analysis API
# ─────────────────────────────────────────────────────────────

@app.get("/api/gap-analysis/{candidate_id}")
def get_gap_analysis(candidate_id: str, use_llm: bool = False):
    """
    Module 16: Get gap analysis for a specific ranked candidate.
    Uses the precomputed submission.csv to find rank/score.
    """
    import csv
    from redrob_ranker.engines.feature_engine import extract_features
    from redrob_ranker.engines.gap_analysis_engine import analyze_candidate_gap

    # Load submission rank/score
    rank, score = None, None
    if _submission_path.exists():
        with open(_submission_path, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["candidate_id"] == candidate_id:
                    rank = int(row["rank"])
                    score = float(row["score"])
                    break

    if rank is None:
        raise HTTPException(status_code=404, detail=f"{candidate_id} not in top-100 ranking")

    # Load candidate
    candidates_path = Path("./candidates.jsonl")
    candidate = None
    if candidates_path.exists():
        with open(candidates_path, "r") as f:
            for line in f:
                try:
                    c = json.loads(line.strip())
                    if c.get("candidate_id") == candidate_id:
                        candidate = c
                        break
                except Exception:
                    pass

    if not candidate:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found")

    features = extract_features(candidate)
    gap = analyze_candidate_gap(candidate, features, rank, score, use_llm=use_llm)
    return gap


# ─────────────────────────────────────────────────────────────
# MODULE 17 — Resume Quality API
# ─────────────────────────────────────────────────────────────

@app.get("/api/resume-quality/{candidate_id}")
def get_resume_quality(candidate_id: str, use_llm: bool = False):
    """
    Module 17: Get resume quality analysis for a candidate.
    """
    from redrob_ranker.engines.resume_quality_engine import analyze_resume_quality
    from redrob_ranker.config import REQUIRED_SKILLS

    candidates_path = Path("./candidates.jsonl")
    if not candidates_path.exists():
        raise HTTPException(status_code=404, detail="Candidates file not found")

    candidate = None
    with open(candidates_path, "r") as f:
        for line in f:
            try:
                c = json.loads(line.strip())
                if c.get("candidate_id") == candidate_id:
                    candidate = c
                    break
            except Exception:
                pass

    if not candidate:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found")

    quality = analyze_resume_quality(candidate, jd_required_skills=REQUIRED_SKILLS, use_llm=use_llm)
    return quality


@app.post("/api/resume-quality/upload")
async def resume_quality_from_upload(
    file: UploadFile = File(...),
    use_llm: bool = False,
):
    """
    Module 17: Upload a resume file and get quality analysis.
    No need to have it in candidates.jsonl.
    """
    from redrob_ranker.engines.resume_ingestion_engine import ingest_resume
    from redrob_ranker.engines.resume_quality_engine import analyze_resume_quality
    from redrob_ranker.config import REQUIRED_SKILLS

    content = await file.read()
    candidate = ingest_resume(content, file.filename or "resume.pdf", use_llm=use_llm)
    if not candidate:
        raise HTTPException(status_code=422, detail="Could not extract candidate from file")

    quality = analyze_resume_quality(candidate, jd_required_skills=REQUIRED_SKILLS, use_llm=use_llm)
    return {**quality, "extracted_profile": candidate["profile"]}


@app.post("/api/hackathon/validate-file")
async def validate_file(file: UploadFile = File(...)):
    """
    Validate and detect uploaded file type, returning detailed metadata and statistics.
    Also saves the file in its canonical place (candidates.jsonl, job_description.md, candidate_schema.json)
    if it matches one of these expected types.
    """
    from redrob_ranker.utils.file_detector import detect_file_type, profile_file_metadata
    from redrob_ranker.utils.data_ingestion import stream_candidates_from_bytes
    
    try:
        content = await file.read()
        detected = detect_file_type(content, file.filename)
        
        if detected.get("error"):
            return {
                "status": "error",
                "filename": file.filename,
                "error": detected["error"],
                "type": "Unknown File",
                "size_bytes": len(content)
            }
            
        detected_type = detected["type"]
        
        # Profile metadata
        metadata = profile_file_metadata(content, file.filename, detected_type)
        if metadata.get("error"):
            return {
                "status": "error",
                "filename": file.filename,
                "error": metadata["error"],
                "type": detected_type,
                "size_bytes": len(content)
            }
            
        # Write canonical files if valid
        if detected_type == "Candidate Dataset":
            candidates = list(stream_candidates_from_bytes(content, file.filename))
            with open("./uploaded_candidates.jsonl", "w", encoding="utf-8") as f:
                for c in candidates:
                    f.write(json.dumps(c) + "\n")
        elif detected_type == "Job Description":
            if file.filename.lower().endswith((".docx", ".pdf")):
                from redrob_ranker.engines.resume_ingestion_engine import read_file_to_text
                text_content = read_file_to_text(content, file.filename)
                with open("./job_description.md", "w", encoding="utf-8") as f:
                    f.write(text_content)
            else:
                with open("./job_description.md", "wb") as f:
                    f.write(content)
        elif detected_type == "Schema Definition":
            with open("./candidate_schema.json", "wb") as f:
                f.write(content)
                
        return {
            "status": "success",
            "filename": file.filename,
            "size_bytes": len(content),
            "type": detected_type,
            "metadata": metadata
        }
    except Exception as e:
        logger.error(f"Error during file validation: {e}", exc_info=True)
        return {
            "status": "error",
            "filename": file.filename,
            "error": f"Failed to validate file: {str(e)}",
            "type": "Unknown File",
            "size_bytes": 0
        }


@app.post("/api/hackathon/rank")
async def hackathon_rank(
    use_uploaded: bool = False,
    candidates_file: Optional[UploadFile] = File(None),
    job_description_file: Optional[UploadFile] = File(None),
    schema_file: Optional[UploadFile] = File(None),
):
    """
    Dedicated "Redrob Hackathon Mode" one-click endpoint:
    1. Ingest job description & override configurations (or use default fallbacks)
    2. Stream & validate candidate profiles
    3. Generate submission CSV & 6 reports
    4. Return results and report contents
    5. Support custom user datasets via uploaded_candidates.jsonl
    """
    import json
    from pathlib import Path

    # ── Step 0: Save Schema if uploaded ─────────────────────────────
    if schema_file is not None:
        try:
            schema_bytes = await schema_file.read()
            with open("./candidate_schema.json", "wb") as f:
                f.write(schema_bytes)
        except Exception as e:
            logger.warning(f"Failed to save uploaded schema file: {e}")
            
    # ── Step 1: Read and ingest Job Description ─────────────────────
    jd_text = ""
    if job_description_file is not None:
        try:
            jd_bytes = await job_description_file.read()
            jd_text = jd_bytes.decode("utf-8", errors="replace")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to read Job Description file: {e}")
    else:
        # Fallback to local job_description.md
        local_jd = Path("./job_description.md")
        if local_jd.exists():
            jd_text = local_jd.read_text(encoding="utf-8")
        else:
            # Fallback to the default JD text in the semantic engine
            from redrob_ranker.engines.semantic_engine import JD_TEXT as fallback_jd
            jd_text = fallback_jd
        
    if not jd_text.strip():
        raise HTTPException(status_code=400, detail="Job description is empty")
        
    try:
        from redrob_ranker.engines.jd_ingestion_engine import ingest_jd, jd_to_config_override
        jd_data = ingest_jd(text=jd_text, use_llm=False)
        overrides = jd_to_config_override(jd_data)
        
        # Override configuration settings in-memory
        import redrob_ranker.config as cfg
        cfg.REQUIRED_SKILLS.clear()
        cfg.REQUIRED_SKILLS.update(overrides.get("REQUIRED_SKILLS", set()))
        cfg.PREFERRED_SKILLS.clear()
        cfg.PREFERRED_SKILLS.update(overrides.get("PREFERRED_SKILLS", set()))
        cfg.JD_EXPERIENCE_RANGE = (overrides.get("YOE_IDEAL_MIN", 5), overrides.get("YOE_IDEAL_MAX", 9))
        cfg.JD_ROLE = overrides.get("JD_TITLE", "")
        cfg.PREFERRED_CITIES.clear()
        cfg.PREFERRED_CITIES.update([overrides.get("JD_LOCATION", "India").lower()])
        
        # Override semantic engine values
        import redrob_ranker.engines.semantic_engine as se
        se.JD_TEXT = jd_text
        se.JD_TOKENS = list(overrides.get("REQUIRED_SKILLS", set()))
    except Exception as e:
        logger.error(f"JD parsing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to parse and apply Job Description: {e}")
        
    # ── Step 2: Stream candidates from bytes or local file ──────────
    candidates = []
    if candidates_file is not None:
        try:
            cand_bytes = await candidates_file.read()
            from redrob_ranker.utils.data_ingestion import stream_candidates_from_bytes
            candidates = list(stream_candidates_from_bytes(cand_bytes, candidates_file.filename or "candidates.jsonl"))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to ingest candidate dataset: {e}")
    else:
        # Fallback to local files
        uploaded_jsonl = Path("./uploaded_candidates.jsonl")
        local_jsonl = Path("./candidates.jsonl")
        local_json = Path("./sample_candidates.json")
        
        if use_uploaded and uploaded_jsonl.exists():
            from redrob_ranker.utils.data_loader import load_all_candidates
            candidates = load_all_candidates(str(uploaded_jsonl))
        elif local_jsonl.exists():
            from redrob_ranker.utils.data_loader import load_all_candidates
            candidates = load_all_candidates(str(local_jsonl))
        elif local_json.exists():
            from redrob_ranker.utils.data_loader import load_all_candidates
            candidates = load_all_candidates(str(local_json))
        else:
            raise HTTPException(status_code=400, detail="No candidate file uploaded and no default candidates file found")
        
    if not candidates:
        raise HTTPException(status_code=400, detail="No valid candidate profiles could be extracted from dataset")
        
    # ── Step 3: Schema Validation ──────────────────────────────────
    try:
        from redrob_ranker.utils.schema_validator import SchemaValidator, generate_schema_validation_report
        validator = SchemaValidator()
        errors_map = {}
        for c in candidates:
            cid = c.get("candidate_id", "UNKNOWN")
            errs = validator.validate_candidate(c)
            if errs:
                errors_map[cid] = errs
        generate_schema_validation_report(errors_map, len(candidates), "./schema_validation_report.md")
    except Exception as e:
        logger.error(f"Schema validation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Validation error: {e}")
        
    # ── Step 4: Execute Reranking Cascade ───────────────────────────
    try:
        from redrob_ranker.engines.ranking_engine import rank_candidates
        # Rank up to TOP_CANDIDATES real candidates (never more than we have).
        # Padding to exactly 100 rows for submission compliance happens inside
        # write_submission via pad_to_submission_size() — NOT here — so that
        # top_ranked always contains only real analyzed candidates.
        top_n = min(TOP_CANDIDATES, len(candidates))
        top_ranked = rank_candidates(candidates, top_n=top_n)
    except Exception as e:
        logger.error(f"Ranking execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Ranking engine failed: {e}")
        
    # ── Step 5: Write Submission CSV (padded to 100 for compliance) ──
    try:
        from rank import write_submission
        # write_submission pads to exactly 100 rows via pad_to_submission_size().
        # top_ranked is NOT modified — only the on-disk CSV gets dummy rows.
        write_submission(top_ranked, "./submission.csv")
    except Exception as e:
        logger.warning(f"Writing submission CSV failed: {e}")

    # ── Step 6: Generate remaining Validation Reports ────────────────
    try:
        from redrob_ranker.utils.report_generator import generate_validation_reports
        generate_validation_reports(top_ranked, len(candidates))
    except Exception as e:
        logger.warning(f"Failed to generate validation reports: {e}")

    # ── Step 7: Load report contents for the response ───────────────
    reports = {}
    for report_key, file_name in [
        ("schema_validation", "schema_validation_report.md"),
        ("ranking_audit", "ranking_audit_report.md"),
        ("honeypot_analysis", "honeypot_report.md"),
        ("distribution", "score_distribution_report.md"),
        ("hireability", "hireability_analysis_report.md"),
        ("feature_importance", "feature_contribution_report.md"),
        ("ranking_diagnostics", "ranking_diagnostics_report.md"),
    ]:
        report_path = Path(file_name)
        if report_path.exists():
            reports[report_key] = report_path.read_text(encoding="utf-8")
        else:
            reports[report_key] = f"Report {file_name} was not generated."

    # Format results — top_ranked contains ONLY real candidates (no dummy padding)
    from redrob_ranker.utils.explanation_engine import generate_reasoning

    results = []
    for idx, (c, feat, score) in enumerate(top_ranked):
        cid = c.get("candidate_id", "UNKNOWN")
        rank = idx + 1
        reasoning = generate_reasoning(c, feat, score, rank)
        
        # Build SHAP/rule-based explanation if available
        explanation = feat.get("explanation", None)
        explanation_summary = ""
        if explanation:
            explanation_summary = explanation.get("summary", "")

        results.append({
            "candidate_id": cid,
            "rank": rank,
            "score": round(score, 6),
            "name": c.get("profile", {}).get("anonymized_name", "Unknown"),
            "title": c.get("profile", {}).get("current_title", ""),
            "reasoning": reasoning,
            "explanation_summary": explanation_summary,
            "explanation": explanation,
            "ltr_score": round(feat.get("ltr_score", -1.0), 4),
            "ltr_blended_score": round(feat.get("ltr_blended_score", score), 6),
            "score_breakdown": {
                "title_score": round(feat.get("combined_title_score", 0), 4),
                "skill_score": round(feat.get("core_skill_score", 0), 4),
                "experience_score": round(feat.get("yoe_score", 0), 4),
                "behavioral_score": round(feat.get("availability_score", 0), 4),
                "education_score": round(feat.get("education_score", 0), 4),
                "github_score": round(feat.get("github_score", 0), 4),
                "honeypot_probability": round(feat.get("honeypot_probability", 0), 4),
                # New primitive features
                "evidence_density": round(feat.get("evidence_density_score", 0), 4),
                "skill_cluster_coverage": round(feat.get("skill_cluster_coverage", 0), 4),
                "resp_depth_score": round(feat.get("resp_depth_score", 0), 4),
                "architecture_exp": round(feat.get("architecture_exp_score", 0), 4),
                "feature_confidence": round(feat.get("feature_confidence_score", 0), 4),
            },
        })
        
    return {
        "status": "success",
        "total_candidates": len(candidates),
        "validation_errors_count": sum(len(errs) for errs in errors_map.values()),
        "malformed_candidates_count": len(errors_map),
        "results": results,
        "reports": reports,
    }


@app.post("/api/ltr/train")
async def train_ltr_model(file: UploadFile = File(...)):
    """
    Train a LightGBM LambdaMART model from a ranked candidates JSON file.

    Accepts the same candidate JSON format as /api/rank.
    Uses the current heuristic scores as training labels, then persists the model.
    Future /api/rank calls will blend LTR scores (70%) with heuristic scores (30%).

    Returns: training metadata dict.
    """
    try:
        from redrob_ranker.engines.ltr_engine import get_ltr_engine
        from redrob_ranker.engines.ranking_engine import rank_candidates
    except ImportError as e:
        raise HTTPException(status_code=503, detail=f"LTR engine or ranking engine unavailable: {e}")

    content = await file.read()
    try:
        payload = json.loads(content.decode("utf-8"))
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    candidates = payload if isinstance(payload, list) else payload.get("candidates", [])
    if not candidates:
        raise HTTPException(status_code=400, detail="No candidates provided")

    # Run the ranking engine to get the full feature dicts and heuristic scores
    try:
        ranked_results = rank_candidates(candidates, top_n=len(candidates))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ranking execution failed during training preparation: {e}")

    feature_dicts = [feat for _, feat, _ in ranked_results]
    final_scores = [score for _, _, score in ranked_results]

    ltr_engine = get_ltr_engine()
    result = ltr_engine.train(feature_dicts, final_scores=final_scores)

    if result.get("status") == "failed":
        raise HTTPException(status_code=500, detail=f"LTR training failed: {result.get('error')}")

    return {
        "status": result.get("status", "unknown"),
        "n_candidates": result.get("n_candidates", 0),
        "n_features": result.get("n_features", 0),
        "trained_at": result.get("trained_at", ""),
        "message": "Model trained and saved with balanced labels. Future ranking calls will use LTR blending.",
    }



@app.get("/api/ltr/status")
def ltr_status():
    """Return current LTR model status and metadata."""
    try:
        from redrob_ranker.engines.ltr_engine import get_ltr_engine
        engine = get_ltr_engine()
        meta = engine.metadata()
        return {
            "model_trained": engine.is_trained(),
            "metadata": meta,
            "n_features": len(engine.feature_names),
            "message": "LTR model ready" if engine.is_trained() else "No trained model — using heuristic scoring",
        }
    except Exception as e:
        return {"model_trained": False, "error": str(e)}


@app.get("/api/ltr/importance")
def ltr_feature_importance():
    """Return feature importance from the trained LTR model."""
    try:
        from redrob_ranker.engines.ltr_engine import get_ltr_engine
        engine = get_ltr_engine()
        if not engine.is_trained():
            return {"model_trained": False, "importance": {}}
        gain = engine.get_feature_importance("gain")
        split = engine.get_feature_importance("split")
        top_features = sorted(gain.items(), key=lambda x: x[1], reverse=True)[:30]
        return {
            "model_trained": True,
            "top_features_by_gain": [
                {"feature": fn, "gain_pct": round(gv * 100, 2), "split_pct": round(split.get(fn, 0) * 100, 2)}
                for fn, gv in top_features
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
