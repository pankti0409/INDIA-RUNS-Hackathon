"""
schema_validator.py — Schema Validation Utility
Loads candidate_schema.json (if available) and validates candidate dictionary records.
Detects missing properties, type mismatches, and pattern violations without external libraries.
Generates schema_validation_report.md.
"""
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class SchemaValidator:
    def __init__(self, schema_path: Optional[str] = None):
        self.schema = None
        if schema_path is None:
            # Look for candidate_schema.json in default locations
            for p in ["./candidate_schema.json", "../candidate_schema.json"]:
                if Path(p).exists():
                    schema_path = p
                    break
        
        if schema_path and Path(schema_path).exists():
            try:
                with open(schema_path, "r", encoding="utf-8") as f:
                    self.schema = json.load(f)
                logger.info(f"Loaded validation schema from {schema_path}")
            except Exception as e:
                logger.warning(f"Failed to load schema from {schema_path}: {e}")
                
    def validate_candidate(self, candidate: dict) -> List[str]:
        """
        Validates a single candidate dictionary against the schema definition.
        Returns a list of error message strings. If empty, the candidate is valid.
        """
        if not self.schema:
            return []
            
        errors = []
        cid = candidate.get("candidate_id", "UNKNOWN")
        
        # 1. Validate required root properties
        required_root = self.schema.get("required", [])
        for req in required_root:
            if req not in candidate:
                errors.append(f"Missing root required field: '{req}'")
                
        properties = self.schema.get("properties", {})
        
        # 2. Type & Pattern checks
        for prop_name, prop_val in candidate.items():
            if prop_name not in properties:
                # Undefined properties are allowed, but logged
                continue
                
            schema_prop = properties[prop_name]
            prop_errors = self._validate_property(prop_val, schema_prop, prop_name)
            errors = errors + prop_errors
            
        return errors
        
    def _validate_property(self, val, schema_prop: dict, path: str) -> List[str]:
        errors = []
        expected_types = schema_prop.get("type")
        if not expected_types:
            return []
            
        if isinstance(expected_types, str):
            expected_types = [expected_types]
            
        # Check nullability
        is_null = val is None
        if is_null:
            if "null" in expected_types:
                return []
            else:
                return [f"'{path}' cannot be null (expected types: {expected_types})"]
                
        # Validate primary types
        matched_type = False
        for t in expected_types:
            if t == "string" and isinstance(val, str):
                matched_type = True
                # Pattern check (regex)
                if "pattern" in schema_prop:
                    pattern = schema_prop["pattern"]
                    if not re.match(pattern, val):
                        errors.append(f"'{path}' value '{val}' does not match pattern '{pattern}'")
            elif t == "number" and isinstance(val, (int, float)) and not isinstance(val, bool):
                matched_type = True
            elif t == "integer" and isinstance(val, int) and not isinstance(val, bool):
                matched_type = True
            elif t == "boolean" and isinstance(val, bool):
                matched_type = True
            elif t == "object" and isinstance(val, dict):
                matched_type = True
                # Validate sub-properties if defined
                req_fields = schema_prop.get("required", [])
                for req in req_fields:
                    if req not in val:
                        errors.append(f"Missing required field: '{path}.{req}'")
                sub_props = schema_prop.get("properties", {})
                for k, v in val.items():
                    if k in sub_props:
                        errors = errors + self._validate_property(v, sub_props[k], f"{path}.{k}")
            elif t == "array" and isinstance(val, list):
                matched_type = True
                items_schema = schema_prop.get("items", {})
                if items_schema:
                    for idx, item in enumerate(val):
                        errors = errors + self._validate_property(item, items_schema, f"{path}[{idx}]")
                        
        if not matched_type:
            errors.append(f"Type mismatch on '{path}': got '{type(val).__name__}', expected {expected_types}")
            
        return errors

def generate_schema_validation_report(
    errors_map: Dict[str, List[str]], 
    total_records: int, 
    output_path: str = "./schema_validation_report.md"
):
    """Generates a markdown schema validation report."""
    total_errors = sum(len(errs) for errs in errors_map.values())
    malformed_records = len(errors_map)
    valid_records = total_records - malformed_records
    valid_pct = (valid_records / max(1, total_records)) * 100.0
    
    lines = [
        "# Schema Validation Report",
        "",
        "This report outlines the structural alignment of the ingested candidate profiles with the expected system schema definition.",
        "",
        "## Summary Metrics",
        "",
        f"- **Total Candidate Profiles Ingested**: {total_records}",
        f"- **Valid Profiles**: {valid_records} ({valid_pct:.2f}%)",
        f"- **Malformed/Invalid Profiles**: {malformed_records} ({100.0 - valid_pct:.2f}%)",
        f"- **Total Validation Anomalies Identified**: {total_errors}",
        "",
        "## Schema Error Details",
        ""
    ]
    
    if not errors_map:
        lines.append("✓ **All candidate records conform 100% to the schema definition! No validation errors detected.**")
    else:
        lines.append("| Candidate ID | Number of Errors | Detailed Error Messages |")
        lines.append("| :--- | :--- | :--- |")
        # List top 50 candidates with validation errors
        for idx, (cid, errs) in enumerate(list(errors_map.items())[:50]):
            joined_errs = "; ".join(errs)
            if len(joined_errs) > 150:
                joined_errs = joined_errs[:147] + "..."
            lines.append(f"| {cid} | {len(errs)} | {joined_errs} |")
            
        if len(errors_map) > 50:
            lines.append(f"\n*Showing top 50 out of {len(errors_map)} invalid records.*")
            
    report_text = "\n".join(lines)
    Path(output_path).write_text(report_text, encoding="utf-8")
    logger.info(f"Schema validation report generated at {output_path}")
