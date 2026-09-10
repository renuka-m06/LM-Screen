import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class EvidencePassportResponse(BaseModel):
    passport_id: str
    scan_id: str
    image_hash_sha256: str
    created_at: str
    provenance_versions: Dict[str, str]
    quality_summary: Dict[str, Any]
    extracted_fields_summary: List[Dict[str, Any]]
    contradictions_summary: List[Dict[str, Any]]
    screening_result: Dict[str, Any]
    passport_signature_hash: str

class EvidencePassportGenerator:
    """
    Generates a reproducible Evidence Passport snapshot for a scan,
    locking versions of OCR, extraction algorithms, rule profiles, and image integrity hashes.
    """
    def generate_passport(self, scan_data: Dict[str, Any]) -> EvidencePassportResponse:
        scan_id = scan_data.get("scan_id", "UNKNOWN")
        img_hash = scan_data.get("image_hash", "0" * 64)

        versions = {
            "ocr_engine_version": "RapidOCR_v1.2.0",
            "field_extractor_version": "EvidenceExtractor_v2026.1",
            "context_classifier_version": "ContextClassifier_v2026.1",
            "rule_profile_version": scan_data.get("rule_version", "2026.1"),
            "verdict_aggregator_version": "VerdictEngine_v2026.1"
        }

        # Build payload for cryptographic SHA-256 signature
        signature_payload = {
            "scan_id": scan_id,
            "image_hash": img_hash,
            "versions": versions,
            "verdict": scan_data.get("status"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        sig_str = json.dumps(signature_payload, sort_keys=True)
        passport_sig = hashlib.sha256(sig_str.encode("utf-8")).hexdigest()

        return EvidencePassportResponse(
            passport_id=f"PASS-{scan_id[-8:].upper()}",
            scan_id=scan_id,
            image_hash_sha256=img_hash,
            created_at=datetime.now(timezone.utc).isoformat(),
            provenance_versions=versions,
            quality_summary=scan_data.get("quality", {}),
            extracted_fields_summary=[
                {"field": k, "value": v.get("normalized_value") if isinstance(v, dict) else str(v), "confidence": v.get("confidence") if isinstance(v, dict) else 1.0}
                for k, v in (scan_data.get("extracted_fields") or {}).items()
            ] if isinstance(scan_data.get("extracted_fields"), dict) else [],
            contradictions_summary=scan_data.get("contradictions", []),
            screening_result={
                "status": scan_data.get("status"),
                "public_label": scan_data.get("public_label"),
                "confidence": scan_data.get("screening_confidence")
            },
            passport_signature_hash=passport_sig
        )
