import os
import io
import time
import hashlib
import numpy as np
from PIL import Image
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from typing import Optional

from backend.app.database import get_db
from backend.app.config import settings
from backend.app.models.models import Scan, OCRResult, ExtractedField, RuleResult, DecisionTrace, Product
from backend.app.schemas.schemas import ScanResponse

from ai.quality import ImageQualityGate
from ai.detection import PackageDetector
from ai.ocr_engine import OCREngine
from ai.field_extractor import FieldExtractor
from ai.context_classifier import ContextClassifier
from ai.barcode_engine import BarcodeEngine
from ai.consistency import ConsistencyScreening
from rules.engine import DeterministicRuleEngine
from rules.verdict import VerdictAggregator

router = APIRouter(prefix="/scans", tags=["Scans"])

quality_gate = ImageQualityGate()
panel_detector = PackageDetector()
ocr_engine = OCREngine()
field_extractor = FieldExtractor()
context_classifier = ContextClassifier()
barcode_engine = BarcodeEngine()
consistency = ConsistencyScreening()
rule_engine = DeterministicRuleEngine()
verdict_aggregator = VerdictAggregator()


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

    # ── Step 2: Image Quality Gate ─────────────────────────────────────────────
    q_result = quality_gate.assess_quality(image_np)
    decision_trace.append({
        "stage": "IMAGE_QUALITY",
        "status": q_result.get("status", "UNKNOWN"),
        "detail": q_result.get("quality_label", "") + f" | blur={q_result.get('blur_score', 0):.1f} brightness={q_result.get('brightness_score', 0):.1f}"
    })

    # ── Step 3: Panel Detection ────────────────────────────────────────────────
    panel_result = panel_detector.detect_panel(image_np)
    decision_trace.append({"stage": "PANEL_DETECTION", "status": "OK", "detail": str(panel_result)})

    # ── Step 4: OCR Token Extraction ───────────────────────────────────────────
    ocr_tokens = ocr_engine.extract_tokens(image_np)
    decision_trace.append({
        "stage": "OCR",
        "status": "OK" if ocr_tokens else "NO_TOKENS",
        "detail": f"{len(ocr_tokens)} tokens detected"
    })

    # ── Step 4b: OCR-informed quality refinement ───────────────────────────────
    q_result = quality_gate.upgrade_with_ocr(q_result, ocr_tokens)
    decision_trace.append({
        "stage": "QUALITY_REFINEMENT",
        "status": q_result.get("status", "UNKNOWN"),
        "detail": f"Revised quality after OCR feedback: {q_result.get('status')}"
    })

    # ── Step 5: Barcode Detection ──────────────────────────────────────────────
    barcode_status = barcode_engine.decode_and_validate(image_np)
    decision_trace.append({
        "stage": "BARCODE",
        "status": barcode_status.get("status", "BARCODE_NOT_FOUND"),
        "detail": f"GTIN={barcode_status.get('gtin', 'N/A')} | {barcode_status.get('reasons', [''])[0]}"
    })

    # ── Step 6: Field Extraction ───────────────────────────────────────────────
    scale = barcode_status.get("scale_mm_per_pixel")
    extracted_fields = field_extractor.extract_fields(ocr_tokens, scale_mm_per_pixel=scale)
    decision_trace.append({
        "stage": "FIELD_EXTRACTION",
        "status": "OK",
        "detail": f"Fields extracted: {', '.join(extracted_fields.keys()) or 'none'}"
    })

    # ── Step 7: Context Classification ────────────────────────────────────────
    context = context_classifier.classify_context(ocr_tokens)
    # Augment context with physical measurement data for rule engine (LM007)
    context["scale_mm_per_pixel"] = scale
    if panel_result.get("detected"):
        context["pdp_crop_box"] = panel_result.get("crop_box")
        
    decision_trace.append({
        "stage": "CONTEXT_CLASSIFICATION",
        "status": "OK",
        "detail": f"Category: {context.get('product_category')} | Origin: {context.get('origin')} | Confidence: {context.get('context_confidence')}"
    })

    # ── Step 8: Identity Consistency Check ────────────────────────────────────
    # IMAGE IS PRIMARY EVIDENCE — user input is metadata/hint only
    ocr_product_name = extracted_fields.get("product_name", {}).get("normalized_value") if "product_name" in extracted_fields else None
    ocr_gtin = extracted_fields.get("gtin", {}).get("normalized_value") if "gtin" in extracted_fields else None
    barcode_gtin = barcode_status.get("gtin")

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

    # ── Step 9: Rule Engine Evaluation ────────────────────────────────────────
    rule_traces = rule_engine.evaluate(extracted_fields, context, q_result)
    decision_trace.append({
        "stage": "RULE_EVALUATION",
        "status": "OK",
        "detail": f"{len(rule_traces)} rules evaluated | " + " | ".join(f"{r['rule_id']}:{r['status']}" for r in rule_traces if r.get('applicable', True))
    })

    # ── Step 10: Verdict Aggregation ──────────────────────────────────────────
    verdict = verdict_aggregator.aggregate(rule_traces, q_result, barcode_status, context, identity_warnings)
    decision_trace.append({
        "stage": "VERDICT",
        "status": verdict.get("status"),
        "detail": f"Confidence: {verdict.get('screening_confidence')} | {verdict.get('public_label')}"
    })

    duration_ms = (time.time() - start_time) * 1000

    print(
        f"[Pipeline] Scan: {filename} | "
        f"Quality: {q_result.get('status')} ({q_result.get('quality_label')}) | "
        f"Tokens: {len(ocr_tokens)} | "
        f"Fields: {list(extracted_fields.keys())} | "
        f"IdentityWarnings: {len(identity_warnings)} | "
        f"Category: {context.get('product_category')} | "
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

    if not db_product and (lookup_gtin or product_name):
        # Create product record using image evidence first, then user hint as fallback
        image_name = ocr_product_name or product_name or "Scanned Commodity"
        db_product = Product(
            gtin=lookup_gtin,
            product_name=image_name,
            category=context.get("product_category", "general")
        )
        db.add(db_product)
        db.commit()
        db.refresh(db_product)

    scan_db = Scan(
        product_id=db_product.id if db_product else None,
        image_hash=image_hash,
        image_path=filepath,
        quality_status=q_result["status"],
        blur_score=q_result["blur_score"],
        brightness_score=q_result["brightness_score"],
        glare_ratio=q_result["glare_ratio"],
        status=verdict["status"],
        public_label=verdict["public_label"],
        screening_confidence=verdict["screening_confidence"],
        rule_version=verdict["rule_version"]
    )
    db.add(scan_db)
    db.commit()
    db.refresh(scan_db)

    # Save OCR Tokens
    for tok in ocr_tokens:
        db_ocr = OCRResult(
            scan_id=scan_db.id,
            token_id=tok["id"],
            text=tok["text"],
            polygon=tok["polygon"],
            confidence=tok["confidence"],
            language=tok.get("language", "en")
        )
        db.add(db_ocr)

    # Save Extracted Fields
    for f_key, f_val in extracted_fields.items():
        db_field = ExtractedField(
            scan_id=scan_db.id,
            field_name=f_val["field_name"],
            raw_value=f_val["raw_value"],
            normalized_value=f_val["normalized_value"],
            confidence=f_val["confidence"],
            ocr_evidence_ids=f_val.get("ocr_evidence_ids", []),
            extraction_method=f_val["extraction_method"]
        )
        db.add(db_field)

    # Save Rule Results
    for trace in rule_traces:
        if trace.get("applicable", True):
            db_rule = RuleResult(
                scan_id=scan_db.id,
                rule_id=trace["rule_id"],
                rule_name=trace.get("rule_name", trace["rule_id"]),
                status=trace["status"],
                confidence=trace["confidence"],
                reason=trace["reason"]
            )
            db.add(db_rule)

    db.commit()

    # Save Decision Trace
    db_trace = DecisionTrace(
        scan_id=scan_db.id,
        stage="pipeline_complete",
        duration_ms=duration_ms,
        output_summary={"verdict": verdict["status"], "confidence": verdict["screening_confidence"]}
    )
    db.add(db_trace)
    db.commit()

    return ScanResponse(
        scan_id=scan_db.id,
        product_id=db_product.id if db_product else None,
        status=verdict["status"],
        public_label=verdict["public_label"],
        screening_confidence=verdict["screening_confidence"],
        quality=q_result,
        ocr_tokens=ocr_tokens,
        extracted_fields=extracted_fields,
        checks_performed=verdict["checks_performed"],
        checks_not_performed=verdict["checks_not_performed"],
        rule_version=verdict["rule_version"],
        review_reasons=verdict["review_reasons"],
        identity_warnings=identity_warnings,
        decision_trace=decision_trace,
        processing_time_ms=round(duration_ms, 1),
        ocr_token_count=len(ocr_tokens),
        disclaimer=verdict["disclaimer"]
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
    return ScanResponse(
        scan_id=scan.id,
        product_id=scan.product_id,
        status=scan.status,
        public_label=scan.public_label,
        screening_confidence=scan.screening_confidence,
        quality={
            "status": scan.quality_status,
            "blur_score": scan.blur_score,
            "brightness_score": scan.brightness_score,
            "glare_ratio": scan.glare_ratio
        },
        ocr_tokens=ocr_tokens,
        extracted_fields=extracted_fields,
        checks_performed=checks_performed,
        checks_not_performed=[],
        rule_version=scan.rule_version,
        review_reasons=[w["explanation"] for w in identity_warnings] if identity_warnings else [],
        identity_warnings=identity_warnings,
        decision_trace=traces,
        image_hash=scan.image_hash,
        disclaimer=VerdictAggregator.MANDATORY_DISCLAIMER
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
