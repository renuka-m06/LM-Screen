import os
import io
import time
import hashlib
import numpy as np
from PIL import Image
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form, Header
from sqlalchemy.orm import Session
from typing import Optional

from backend.app.database import get_db
from backend.app.config import settings
from backend.app.models.models import (
    Scan, OCRResult, ExtractedField, RuleResult, DecisionTrace, Product,
    ProductImage, ImageQuality, Detection, ProductClassification,
    RuleResultEvidence, ReviewFactor
)
from backend.app.schemas.schemas import ScanResponse

from backend.app.services.ml.screening_service import ScreeningService
from ai.consistency import ConsistencyScreening

router = APIRouter(prefix="/scans", tags=["Scans"])

screening_service = ScreeningService()
consistency = ConsistencyScreening()


MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/bmp", "image/tiff"}

@router.post("", response_model=ScanResponse)
async def process_scan(
    file: UploadFile = File(...),
    product_name: Optional[str] = Form(None),
    gtin: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    start_time = time.time()
    decision_trace = []  # Step-by-step pipeline trace

    # ── Step 1: File validation ─────────────────────────────────────────────────
    # Check MIME type
    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{file.content_type}'. Accepted: JPEG, PNG, WebP, BMP, TIFF."
        )

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Check file size
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({len(contents)//1024}KB). Maximum allowed: 10MB."
        )

    try:
        pil_image = Image.open(io.BytesIO(contents)).convert("RGB")
        image_np = np.array(pil_image)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image format: {str(e)}")

    image_hash = hashlib.sha256(contents).hexdigest()
    decision_trace.append({"stage": "IMAGE_LOAD", "status": "OK", "detail": f"Image loaded: {image_np.shape[1]}x{image_np.shape[0]}px"})

    # Save uploaded image locally
    filename = f"scan_{int(time.time()*1000)}_{file.filename}"
    filepath = os.path.join(settings.UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(contents)

    # ── Step 2: Screening Service Pipeline ─────────────────────────────────────
    user_hints = {"product_name": product_name, "gtin": gtin}
    pipeline_result = screening_service.process_image(image_np, user_hints)
    
    q_result = pipeline_result["image_quality"]
    panel_result = pipeline_result["detections"][0] if pipeline_result["detections"] else {}
    ocr_tokens = pipeline_result["ocr"]
    barcode_status = pipeline_result["barcode"]
    evidence_list = pipeline_result["evidence"]
    context = pipeline_result["product_context"]
    rule_traces = pipeline_result["rule_results"]
    verdict = pipeline_result["verdict"]
    duration_ms = pipeline_result["processing_time_ms"]
    
    # Merge pipeline traces with the existing decision_trace
    decision_trace.extend(pipeline_result["decision_trace"])
    
    # Map back to old extracted_fields format for DB save compatibility temporarily
    extracted_fields = {e["field"]: {"field_name": e["field"], "raw_value": e["source"]["raw_text"], "normalized_value": e["value"], "confidence": e["confidence"], "extraction_method": e["method"], "evidence_state": "PRESENT" if e["found"] else "ABSENT_FROM_EVIDENCE"} for e in evidence_list}

    # ── Step 3: Identity Consistency Check ────────────────────────────────────
    ocr_product_name = extracted_fields.get("product_name", {}).get("normalized_value") if "product_name" in extracted_fields else None
    ocr_gtin = extracted_fields.get("gtin", {}).get("normalized_value") if "gtin" in extracted_fields else None
    barcode_gtin = barcode_status.get("value")

    identity_check = consistency.check_identity_consistency(
        user_product_name=product_name,
        ocr_product_name=ocr_product_name,
        user_gtin=gtin,
        ocr_gtin=ocr_gtin,
        barcode_gtin=barcode_gtin
    )
    identity_warnings = identity_check.get("warnings", [])
    has_identity_mismatch = identity_check.get("has_warnings", False)

    decision_trace.append({
        "stage": "IDENTITY_CHECK",
        "status": "MISMATCH_DETECTED" if has_identity_mismatch else "CONSISTENT",
        "detail": f"{len(identity_warnings)} warning(s): {'; '.join(w['type'] for w in identity_warnings)}" if identity_warnings else "No identity conflicts detected"
    })

    print(
        f"[Pipeline] Scan: {filename} | "
        f"Quality: {q_result.get('usable')} | "
        f"Tokens: {len(ocr_tokens)} | "
        f"Fields: {list(extracted_fields.keys())} | "
        f"Category: {context.get('category')} | "
        f"Verdict: {verdict.get('status')} ({verdict.get('screening_confidence')})"
    )

    # ── Save to Database ───────────────────────────────────────────────────────
    # Product lookup: prefer GTIN match, then name match
    # IMAGE IS PRIMARY — user input is a lookup hint, not authoritative identity
    db_product = None
    lookup_gtin = barcode_gtin or ocr_gtin or gtin  # prefer decoded barcode > OCR > user hint
    if lookup_gtin:
        db_product = db.query(Product).filter(Product.gtin == lookup_gtin).first()
    if not db_product and product_name:
        db_product = db.query(Product).filter(Product.product_name == product_name).first()

    try:
        if not db_product and (lookup_gtin or product_name):
            # Create product record using image evidence first, then user hint as fallback
            image_name = ocr_product_name or product_name or "Scanned Commodity"
            db_product = Product(
                gtin=lookup_gtin,
                product_name=image_name,
                category=context.get("product_category", "general")
            )
            db.add(db_product)
            db.flush()

        # 1. Product Image
        db_image = ProductImage(
            product_id=db_product.id if db_product else None,
            file_path=filepath,
            original_filename=file.filename,
            mime_type=file.content_type,
            file_size=len(contents),
            image_width=image_np.shape[1],
            image_height=image_np.shape[0],
            capture_source="API_UPLOAD"
        )
        db.add(db_image)
        db.flush()

        # 2. Image Quality
        raw_q = q_result.get("raw_metrics", {})
        db_quality = ImageQuality(
            image_id=db_image.id,
            usable=q_result.get("usable", True),
            quality_score=q_result.get("quality_score"),
            blur_score=raw_q.get("blur_score"),
            brightness_score=raw_q.get("brightness_score"),
            resolution_score=raw_q.get("resolution_score"),
            issues=q_result.get("issues", []),
            method=q_result.get("method")
        )
        db.add(db_quality)

        # 3. Detections
        det_map = {} # Maps crop_box or some identifier to Detection.id if possible, or we just save them
        for det in pipeline_result["detections"]:
            db_det = Detection(
                image_id=db_image.id,
                object_type=det.get("type", "package"),
                confidence=det.get("confidence", 1.0)
            )
            if "crop_box" in det:
                x, y, w, h = det["crop_box"]
                db_det.x, db_det.y, db_det.width, db_det.height = x, y, w, h
            db.add(db_det)
            db.flush()
            det_map["primary"] = db_det.id # Just store the last/first one as primary for now

        # 4. Scan
        scan_db = Scan(
            product_id=db_product.id if db_product else None,
            image_id=db_image.id,
            image_hash=image_hash,
            image_path=filepath,
            # Legacy quality fields (optional, but keep for compat)
            quality_status=raw_q.get("status", "UNKNOWN"),
            blur_score=raw_q.get("blur_score", 0.0),
            brightness_score=raw_q.get("brightness_score", 0.0),
            glare_ratio=raw_q.get("glare_ratio", 0.0),
            
            status=verdict["status"],
            public_label=verdict["public_label"],
            screening_confidence=verdict["screening_confidence"],
            category=context.get("product_category"),
            rule_version=verdict.get("rule_version", "2026.1")
        )
        db.add(scan_db)
        db.flush()

        # 5. Product Classification
        if context:
            db_class = ProductClassification(
                scan_id=scan_db.id,
                category=context.get("product_category", "general"),
                subcategory=context.get("product_subcategory"),
                confidence=context.get("confidence", 1.0)
            )
            db.add(db_class)

        # 6. Save OCR Tokens
        for tok in ocr_tokens:
            db_ocr = OCRResult(
                scan_id=scan_db.id,
                detection_id=det_map.get("primary"),
                token_id=tok["id"],
                text=tok["text"],
                polygon=tok.get("polygon"),
                bbox=tok.get("bbox"),
                confidence=tok["confidence"],
                language=tok.get("language", "en"),
                ocr_engine=tok.get("engine"),
                ocr_version=tok.get("ocr_version")
            )
            db.add(db_ocr)

        # 7. Save Extracted Fields (Evidence)
        field_id_map = {}
        for ev in evidence_list:
            db_field = ExtractedField(
                scan_id=scan_db.id,
                field_name=ev["field"],
                raw_value=ev.get("source", {}).get("raw_text"),
                raw_text=ev.get("source", {}).get("raw_text"),
                normalized_value=ev["value"],
                found=ev["found"],
                confidence=ev["confidence"],
                evidence_state=ev.get("evidence_state", "UNCERTAIN"),
                quality_reasons=ev.get("quality_reasons", []),
                source_type=ev.get("source", {}).get("type"),
                source_image_id=db_image.id,
                source_detection_id=det_map.get("primary"),
                source_panel=ev.get("source", {}).get("panel"),
                source_bbox=ev.get("source", {}).get("bbox"),
                extraction_method=ev.get("method", "UNKNOWN")
            )
            db.add(db_field)
            db.flush()
            field_id_map[ev["field"]] = db_field.id

        # 8. Save Rule Results & Evidence Link
        for trace_item in rule_traces:
            db_rule = RuleResult(
                scan_id=scan_db.id,
                rule_id=trace_item.get("rule_id", "UNKNOWN"),
                rule_name=trace_item.get("field", "general"),
                status=trace_item.get("status", "UNKNOWN"),
                applicability=trace_item.get("applicability", "REQUIRED"),
                confidence=trace_item.get("confidence", 1.0),
                reason=trace_item.get("reason", "N/A")
            )
            db.add(db_rule)
            db.flush()
                
                
            # Link evidence explicitly from the engine's field
            f_id = field_id_map.get(trace_item.get("field"))
            if f_id:
                link = RuleResultEvidence(
                    rule_result_id=db_rule.id,
                    evidence_id=f_id
                )
                db.add(link)
                
        # 8b. Save Consistency Checks
        for cc in pipeline_result.get("consistency_checks", []):
            db_cc = ConsistencyCheck(
                scan_id=scan_db.id,
                check_type=cc["check_type"],
                status=cc["status"],
                observed_values=cc.get("observed_values"),
                calculated_value=cc.get("calculated_value"),
                explanation=cc["explanation"],
                evidence_ids=cc.get("evidence_ids", [])
            )
            db.add(db_cc)

        # 9. Save Review Factors
        for rr in verdict.get("review_reasons", []):
            db_rf = ReviewFactor(
                scan_id=scan_db.id,
                factor_type="RULE_REVIEW",
                description=rr
            )
            db.add(db_rf)
            
        for iw in identity_warnings:
            db_rf = ReviewFactor(
                scan_id=scan_db.id,
                factor_type=iw.get("type", "IDENTITY_MISMATCH"),
                severity=iw.get("severity"),
                description=iw.get("explanation")
            )
            db.add(db_rf)

        # 10. Save Decision Trace
        for t in decision_trace:
            db_trace_step = DecisionTrace(
                scan_id=scan_db.id,
                stage=t.get("stage", "UNKNOWN"),
                output_summary={"status": t.get("status"), "detail": t.get("detail")},
                duration_ms=0.0
            )
            db.add(db_trace_step)

        # Final overarching trace step
        db_trace_final = DecisionTrace(
            scan_id=scan_db.id,
            stage="pipeline_complete",
            duration_ms=duration_ms,
            output_summary={"verdict": verdict["status"], "confidence": verdict["screening_confidence"]}
        )
        db.add(db_trace_final)

        db.commit()
        
        # 11. Post-process Clustering
        from backend.app.services.identity_matcher import IdentityMatcher
        matcher = IdentityMatcher(db)
        cluster = matcher.process_scan(scan_db.id)
        if cluster:
            print(f"Assigned Scan {scan_db.id} to Cluster {cluster.id} (Match: {cluster.match_method})")

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database transaction failed: {str(e)}")

    evidence_summary = {
        "applicable_fields": len(evidence_list),
        "supported": sum(1 for e in evidence_list if e.get("evidence_state") in ["VERIFIED", "SUPPORTED", "MANUALLY_VERIFIED"]),
        "uncertain": sum(1 for e in evidence_list if e.get("evidence_state") == "UNCERTAIN"),
        "conflicting": sum(1 for e in evidence_list if e.get("evidence_state") == "CONFLICTING"),
        "unreadable": sum(1 for e in evidence_list if e.get("evidence_state") == "UNREADABLE"),
        "not_detected": sum(1 for e in evidence_list if e.get("evidence_state") == "NOT_DETECTED"),
        "not_applicable": sum(1 for e in evidence_list if e.get("evidence_state") == "NOT_APPLICABLE")
    }

    return ScanResponse(
        screening_id=scan_db.id,
        product_id=db_product.id if db_product else None,
        status=verdict["status"],
        image_quality=q_result,
        detections=[panel_result] if panel_result.get("detected") else [],
        ocr=ocr_tokens,
        barcode=barcode_status,
        product_context=context,
        evidence=evidence_list,
        rule_results=verdict.get("checks_performed", []),
        consistency_checks=pipeline_result.get("consistency_checks", []),
        review_factors=[{"reason": r} for r in verdict.get("review_reasons", [])] + identity_warnings,
        decision_trace=decision_trace,
        evidence_summary=evidence_summary,
        
        # Legacy
        public_label=verdict["public_label"],
        screening_confidence=verdict["screening_confidence"],
        disclaimer=verdict["disclaimer"],
        rule_version=verdict["rule_version"],
        image_hash=image_hash,
        processing_time_ms=round(duration_ms, 1)
    )


@router.get("/{scan_id}/decision-trace")
def get_scan_decision_trace(scan_id: str, db: Session = Depends(get_db)):
    """Returns the step-by-step decision trace for a scan. Supports evidence-graph explainability."""
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan record not found.")

    rule_results = [
        {
            "rule_id": r.rule_id,
            "rule_name": r.rule_name,
            "status": r.status,
            "confidence": r.confidence,
            "reason": r.reason,
            "version": r.version
        }
        for r in scan.rule_results
    ]

    db_trace = scan.decision_traces[0] if scan.decision_traces else None
    processing_time = db_trace.duration_ms if db_trace else None

    return {
        "scan_id": scan_id,
        "verdict": scan.status,
        "public_label": scan.public_label,
        "screening_confidence": scan.screening_confidence,
        "rule_version": scan.rule_version,
        "quality_status": scan.quality_status,
        "ocr_token_count": len(scan.ocr_results),
        "extracted_field_count": len(scan.extracted_fields),
        "rule_results": rule_results,
        "processing_time_ms": round(processing_time, 1) if processing_time else None,
        "scan_timestamp": scan.timestamp.isoformat()
    }


@router.get("/{scan_id}/evidence")
def get_scan_evidence(scan_id: str, db: Session = Depends(get_db)):
    """Returns the full evidence graph for a scan: image → OCR tokens → fields → rules → verdict."""
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan record not found.")

    ocr_tokens = [
        {
            "token_id": tok.token_id,
            "text": tok.text,
            "polygon": tok.polygon,
            "confidence": tok.confidence,
            "language": tok.language,
            "model_version": tok.model_version
        }
        for tok in scan.ocr_results
    ]

    extracted_fields = [
        {
            "field_name": f.field_name,
            "raw_value": f.raw_value,
            "normalized_value": f.normalized_value,
            "confidence": f.confidence,
            "ocr_evidence_ids": f.ocr_evidence_ids or [],
            "extraction_method": f.extraction_method,
            # Link forward to rules that used this field
            "rules_evaluated": [
                r.rule_id for r in scan.rule_results
                if f.field_name in (r.reason or "")
            ]
        }
        for f in scan.extracted_fields
    ]

    rule_traces = [
        {
            "rule_id": r.rule_id,
            "rule_name": r.rule_name,
            "status": r.status,
            "reason": r.reason,
            "confidence": r.confidence,
            "version": r.version
        }
        for r in scan.rule_results
    ]

    return {
        "scan_id": scan_id,
        "image_path": scan.image_path,
        "image_hash": scan.image_hash,
        "evidence_graph": {
            "image": {
                "width": None,
                "height": None,
                "quality_status": scan.quality_status,
                "blur_score": scan.blur_score,
                "brightness_score": scan.brightness_score,
                "glare_ratio": scan.glare_ratio
            },
            "ocr_tokens": ocr_tokens,
            "extracted_fields": extracted_fields,
            "rule_traces": rule_traces,
            "verdict": {
                "status": scan.status,
                "public_label": scan.public_label,
                "screening_confidence": scan.screening_confidence,
                "rule_version": scan.rule_version
            }
        }
    }


@router.get("/{scan_id}/findings")
def get_scan_findings(scan_id: str, db: Session = Depends(get_db)):
    """Returns all findings (Rule Results + Evidence) with explanations for a scan."""
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan record not found.")

    findings = []
    
    # Map extracted fields for easy lookup
    fields_map = {f.field_name: f for f in scan.extracted_fields}

    for idx, rule_result in enumerate(scan.rule_results):
        # Determine the primary field this rule applies to.
        # This uses the reason text or a direct mapping.
        primary_field = None
        for field_name in fields_map.keys():
            if rule_result.reason and field_name in rule_result.reason:
                primary_field = field_name
                break
        
        # Fallbacks for specific rules if reason doesn't explicitly mention the field
        if not primary_field:
            if "MRP" in rule_result.rule_name.upper(): primary_field = "mrp"
            elif "NET QTY" in rule_result.rule_name.upper(): primary_field = "net_quantity"
            elif "FSSAI" in rule_result.rule_name.upper(): primary_field = "fssai_license"
            elif "MFG" in rule_result.rule_name.upper(): primary_field = "mfg_date"

        extracted_field = fields_map.get(primary_field) if primary_field else None

        # Build Explanation
        if rule_result.status == "PASS":
            explanation = f"Compliance verified for {primary_field or 'rule'}.\n\n"
        else:
            explanation = f"Potential issue detected for {primary_field or 'rule'}.\n\n"
            
        if extracted_field and extracted_field.raw_value:
            explanation += f"Observed evidence:\n\"{extracted_field.raw_value}\"\n\n"
        else:
            explanation += "Observed evidence:\n[No evidence detected]\n\n"

        explanation += f"Applicable requirement:\n{rule_result.rule_name}\n\n"
        explanation += f"Evidence source:\n{extracted_field.source_type if extracted_field else 'OCR'}\n\n"
        explanation += "Officer verification:\nPending"

        findings.append({
            "finding_id": rule_result.id,
            "scan_id": scan_id,
            "field": primary_field or "general",
            "applicability": rule_result.applicability,
            "observed_value": extracted_field.normalized_value if extracted_field else None,
            "rule_reference": rule_result.rule_name,
            "status": rule_result.status,
            "explanation": explanation,
            "evidence_ids": [extracted_field.id] if extracted_field else [],
            "created_at": rule_result.evaluated_at.isoformat()
        })

    evidence_list = [
        {
            "field_name": f.field_name,
            "raw_value": f.raw_value,
            "normalized_value": f.normalized_value,
            "confidence": f.confidence,
            "evidence_state": f.evidence_state,
            "quality_reasons": f.quality_reasons,
            "ocr_evidence_ids": f.ocr_evidence_ids or [],
            "extraction_method": f.extraction_method
        }
        for f in scan.extracted_fields
    ]
    
    evidence_summary = {
        "applicable_fields": len(evidence_list),
        "supported": sum(1 for e in evidence_list if e.get("evidence_state") in ["VERIFIED", "SUPPORTED", "MANUALLY_VERIFIED"]),
        "uncertain": sum(1 for e in evidence_list if e.get("evidence_state") == "UNCERTAIN"),
        "conflicting": sum(1 for e in evidence_list if e.get("evidence_state") == "CONFLICTING"),
        "unreadable": sum(1 for e in evidence_list if e.get("evidence_state") == "UNREADABLE"),
        "not_detected": sum(1 for e in evidence_list if e.get("evidence_state") == "NOT_DETECTED"),
        "not_applicable": sum(1 for e in evidence_list if e.get("evidence_state") == "NOT_APPLICABLE")
    }

    return {"findings": findings, "evidence": evidence_list, "evidence_summary": evidence_summary}


@router.get("/{scan_id}/evidence-graph")
def get_scan_evidence_graph(scan_id: str, db: Session = Depends(get_db)):
    """Returns the explicit Node-Edge Evidence Graph for a scan."""
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan record not found.")

    ocr_tokens = [
        {
            "token_id": tok.token_id,
            "text": tok.text,
            "polygon": tok.polygon,
            "confidence": tok.confidence,
            "language": tok.language,
            "model_version": tok.model_version
        }
        for tok in scan.ocr_results
    ]

    extracted_fields = {
        f.field_name: {
            "field_name": f.field_name,
            "raw_value": f.raw_value,
            "normalized_value": f.normalized_value,
            "confidence": f.confidence,
            "ocr_evidence_ids": f.ocr_evidence_ids or [],
            "extraction_method": f.extraction_method
        }
        for f in scan.extracted_fields
    }

    checks_performed = [
        {
            "rule_id": r.rule_id,
            "rule_name": r.rule_name,
            "status": r.status,
            "reason": r.reason,
            "confidence": r.confidence
        }
        for r in scan.rule_results
    ]

    scan_data = {
        "scan_id": scan_id,
        "status": scan.status,
        "public_label": scan.public_label,
        "screening_confidence": scan.screening_confidence,
        "rule_version": scan.rule_version,
        "quality": {
            "status": scan.quality_status,
            "blur_score": scan.blur_score,
            "brightness_score": scan.brightness_score,
            "glare_ratio": scan.glare_ratio
        },
        "ocr_tokens": ocr_tokens,
        "extracted_fields": extracted_fields,
        "checks_performed": checks_performed,
        "disclaimer": scan.public_label
    }

    from ai.evidence_graph import EvidenceGraphBuilder
    builder = EvidenceGraphBuilder()
    return builder.build_graph(scan_data)


@router.get("/{scan_id}/evidence-passport")
def get_scan_evidence_passport(scan_id: str, db: Session = Depends(get_db)):
    """Returns a reproducible, cryptographically signed Evidence Passport for a scan."""
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan record not found.")

    extracted_fields = {
        f.field_name: {
            "raw_value": f.raw_value,
            "normalized_value": f.normalized_value,
            "confidence": f.confidence
        }
        for f in scan.extracted_fields
    }

    scan_data = {
        "scan_id": scan.id,
        "image_hash": scan.image_hash or "0" * 64,
        "status": scan.status,
        "public_label": scan.public_label,
        "screening_confidence": scan.screening_confidence,
        "rule_version": scan.rule_version,
        "quality": {
            "status": scan.quality_status,
            "blur_score": scan.blur_score
        },
        "extracted_fields": extracted_fields,
        "contradictions": []
    }

    from ai.evidence_passport import EvidencePassportGenerator
    generator = EvidencePassportGenerator()
    return generator.generate_passport(scan_data)


@router.get("/{scan_id}/decision-replay")
def get_scan_decision_replay(scan_id: str, db: Session = Depends(get_db)):
    """Provides a step-by-step 'Why This Result?' decision replay for officer explanation."""
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan record not found.")

    db_trace = scan.decision_traces[0] if scan.decision_traces else None
    stages = db_trace.trace_payload if db_trace else []

    return {
        "scan_id": scan.id,
        "verdict": scan.status,
        "public_label": scan.public_label,
        "replay_steps": stages or [
            {"stage": "IMAGE_QUALITY", "status": scan.quality_status, "detail": f"Blur score: {scan.blur_score}"},
            {"stage": "OCR", "status": "OK", "detail": f"Extracted {len(scan.ocr_results)} OCR tokens"},
            {"stage": "FIELD_EXTRACTION", "status": "OK", "detail": f"Extracted {len(scan.extracted_fields)} statutory fields"},
            {"stage": "RULE_ENGINE", "status": "OK", "detail": f"Evaluated {len(scan.rule_results)} rule profiles"},
            {"stage": "VERDICT", "status": scan.status, "detail": scan.public_label}
        ],
        "disclaimer": "Decision Replay provides step-by-step pipeline execution transparency."
    }
@router.get("/{scan_id}", response_model=ScanResponse)
def get_scan(scan_id: str, db: Session = Depends(get_db)):
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan record not found.")

    ocr_tokens = [
        {
            "id": tok.token_id,
            "text": tok.text,
            "polygon": tok.polygon,
            "confidence": tok.confidence,
            "language": tok.language,
            "model_version": tok.ocr_version
        }
        for tok in scan.ocr_results
    ]

    extracted_fields = {
        f.field_name: {
            "field_name": f.field_name,
            "raw_value": f.raw_value,
            "normalized_value": f.normalized_value,
            "confidence": f.confidence,
            "ocr_evidence_ids": f.ocr_evidence_ids,
            "extraction_method": f.extraction_method
        }
        for f in scan.extracted_fields
    }

    checks_performed = [
        {
            "rule_id": r.rule_id,
            "rule_name": r.rule_name,
            "status": r.status,
            "reason": r.reason
        }
        for r in scan.rule_results
    ]

    traces = [
        {
            "stage": t.stage,
            "status": t.output_summary.get("status") if isinstance(t.output_summary, dict) and "status" in t.output_summary else "OK",
            "detail": t.output_summary.get("detail") if isinstance(t.output_summary, dict) and "detail" in t.output_summary else str(t.output_summary or "")
        }
        for t in scan.decision_traces
    ]

    # Evaluate identity warnings if product link or trace exists
    identity_warnings = []
    ocr_product = extracted_fields.get("product_name", {}).get("normalized_value")
    if scan.product and ocr_product and scan.product.product_name != ocr_product:
        identity_warnings.append({
            "type": "PRODUCT_IDENTITY_MISMATCH",
            "severity": "NEEDS_REVIEW",
            "user_provided": scan.product.product_name,
            "image_evidence": ocr_product,
            "explanation": "The supplied product name does not match the product identity visible in the uploaded image. Please verify the correct product and re-upload if needed."
        })

    from rules.verdict import VerdictAggregator
    evidence_list = [
        {
            "field": f["field_name"],
            "value": f["normalized_value"],
            "found": True,
            "confidence": f["confidence"],
            "source": {
                "type": "OCR",
                "panel": "declaration_label",
                "bbox": [],
                "raw_text": f["raw_value"]
            },
            "method": f["extraction_method"]
        }
        for f in extracted_fields.values()
    ]

    return ScanResponse(
        screening_id=scan.id,
        product_id=scan.product_id,
        status=scan.status,
        image_quality={
            "status": scan.quality_status,
            "blur_score": scan.blur_score,
            "brightness_score": scan.brightness_score,
            "glare_ratio": scan.glare_ratio
        },
        detections=[],
        ocr=ocr_tokens,
        barcode={},
        product_context={},
        evidence=evidence_list,
        rule_results=checks_performed,
        consistency_checks=[{
            "check_id": c.id,
            "scan_id": c.scan_id,
            "check_type": c.check_type,
            "status": c.status,
            "observed_values": c.observed_values,
            "calculated_value": c.calculated_value,
            "explanation": c.explanation,
            "evidence_ids": c.evidence_ids,
            "created_at": c.created_at.isoformat()
        } for c in scan.consistency_checks] if hasattr(scan, 'consistency_checks') else [],
        review_factors=[{"reason": w["explanation"]} for w in identity_warnings],
        decision_trace=traces,
        
        # Legacy
        public_label=scan.public_label,
        screening_confidence=scan.screening_confidence,
        disclaimer=VerdictAggregator.MANDATORY_DISCLAIMER,
        rule_version=scan.rule_version,
        image_hash=scan.image_hash,
        processing_time_ms=0.0
    )

from fastapi.responses import Response
from backend.app.services.pdf_generator import generate_notice_pdf

@router.get("/{scan_id}/notice")
async def get_scan_notice(
    scan_id: str,
    db: Session = Depends(get_db)
):
    try:
        # Mock inspector name since we don't have auth currently wired
        inspector_name = "Inspector User (ID: 942)"
        pdf_bytes = generate_notice_pdf(scan_id, db, inspector_name)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="Notice_Section15_{scan_id}.pdf"'
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{scan_id}/evidence/{evidence_id}/correct")
def correct_evidence(
    scan_id: str,
    evidence_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    x_user_role: Optional[str] = Header(None)
):
    if x_user_role and x_user_role.upper() != "OFFICER":
        raise HTTPException(status_code=403, detail="Officer authorization required.")

    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
        
    evidence = db.query(ExtractedField).filter(ExtractedField.id == evidence_id, ExtractedField.scan_id == scan_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")

    from backend.app.models.models import EvidenceCorrection, DecisionTrace, User, ConsistencyCheck, RuleResult
    from ai.consistency_engine import ConsistencyEngine
    from ai.evidence_quality import EvidenceQualityEvaluator
    from rules.engine import DeterministicRuleEngine
    from rules.verdict import VerdictAggregator
    import datetime
    
    officer = db.query(User).filter(User.role == "OFFICER").first()
    if not officer:
        officer = User(
            email="officer@legalmetrology.gov.in",
            hashed_password="hashed",
            full_name="Inspector R. K. Sharma",
            role="OFFICER"
        )
        db.add(officer)
        db.flush()

    try:
        correction = EvidenceCorrection(
            evidence_id=evidence_id,
            original_value=evidence.normalized_value,
            corrected_value=payload.get("corrected_value"),
            reason=payload.get("reason", "Manual officer override"),
            corrected_by=officer.id
        )
        db.add(correction)
        
        evidence.normalized_value = payload.get("corrected_value")
        evidence.evidence_state = "MANUALLY_VERIFIED"
        evidence.quality_reasons = ["Officer manually verified and corrected this evidence."]
        
        trace = DecisionTrace(
            scan_id=scan_id,
            stage="OFFICER_CORRECTION",
            input_summary={"field": evidence.field_name, "old": correction.original_value},
            output_summary={"status": "CORRECTED", "detail": f"Field '{evidence.field_name}' corrected to '{correction.corrected_value}' by Officer"},
            duration_ms=0.0
        )
        db.add(trace)
        
        # --- RECALCULATION ---
        context = {
            "product_category": scan.classifications[0].category if getattr(scan, "classifications", None) and len(scan.classifications) > 0 else "general",
        }
        
        evidence_list = []
        for ev in scan.extracted_fields:
            evidence_list.append({
                "field": ev.field_name,
                "value": ev.normalized_value,
                "found": ev.found,
                "confidence": ev.confidence,
                "evidence_state": ev.evidence_state,
                "quality_reasons": ev.quality_reasons,
                "ocr_evidence_ids": ev.ocr_evidence_ids,
                "extraction_method": ev.extraction_method,
            })
            
        ocr_tokens = [{"id": t.token_id, "confidence": t.confidence, "text": t.text} for t in scan.ocr_results]
        q_result = {"usable": True, "status": scan.quality_status, "raw_metrics": {}}
        barcode_result = {}
        
        # 1. Consistency
        ce = ConsistencyEngine()
        consistency_checks = ce.evaluate(evidence_list, barcode_result, context)
        
        # 2. Quality (will preserve MANUALLY_VERIFIED)
        eq = EvidenceQualityEvaluator()
        evidence_list = eq.evaluate_evidence(evidence_list, ocr_tokens, q_result, consistency_checks, barcode_result)
        
        for ev_dict in evidence_list:
            db_ev = next((e for e in scan.extracted_fields if e.field_name == ev_dict["field"]), None)
            if db_ev:
                db_ev.evidence_state = ev_dict["evidence_state"]
                db_ev.quality_reasons = ev_dict["quality_reasons"]
                
        # 3. Rule Engine
        extracted_fields_legacy = { e["field"]: e for e in evidence_list }
        re = DeterministicRuleEngine()
        rule_traces = re.evaluate(extracted_fields_legacy, context, q_result)
        
        # 4. Verdict
        va = VerdictAggregator()
        verdict = va.aggregate(rule_traces, {}, {}, context, [])
        scan.status = verdict.get("status", scan.status)
        scan.screening_confidence = verdict.get("screening_confidence", scan.screening_confidence)
        scan.public_label = verdict.get("public_label", scan.public_label)
        
        # Cleanup old checks and rules
        db.query(ConsistencyCheck).filter(ConsistencyCheck.scan_id == scan_id).delete()
        db.query(RuleResult).filter(RuleResult.scan_id == scan_id).delete()
        
        for c in consistency_checks:
            db.add(ConsistencyCheck(scan_id=scan_id, check_type=c["check_type"], status=c["status"], explanation=c["explanation"], observed_values=c.get("observed_values", {})))
            
        for rt in rule_traces:
            db.add(RuleResult(
                scan_id=scan_id, 
                rule_id=rt["rule_id"], 
                rule_name=rt["rule_id"], 
                status=rt["status"], 
                reason=rt["reason"], 
                applicability=rt["applicability"], 
                evaluated_at=datetime.datetime.utcnow()
            ))

        trace_recalc = DecisionTrace(
            scan_id=scan_id,
            stage="RECALCULATION",
            input_summary={"corrected_field": evidence.field_name},
            output_summary={"status": scan.status, "detail": "Re-evaluated consistency and rules based on officer correction."},
            duration_ms=0.0
        )
        db.add(trace_recalc)
        
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
        
    return {"status": "success", "correction_id": correction.id}
