"""
cases.py -- Officer Case Management & Action Workflow Router

LM-Screen does not make statutory enforcement decisions. This router converts
evidence-backed screening signals into structured investigation cases that
authorized officers can inspect, verify, act upon, and fully audit.

Endpoints:
    POST   /api/v1/cases
    GET    /api/v1/cases
    GET    /api/v1/cases/{case_id}
    PATCH  /api/v1/cases/{case_id}/status
    POST   /api/v1/cases/{case_id}/assign
    POST   /api/v1/cases/{case_id}/notes
    POST   /api/v1/cases/{case_id}/evidence
    POST   /api/v1/cases/{case_id}/inspection
    GET    /api/v1/cases/{case_id}/audit
    POST   /api/v1/cases/{case_id}/close
    POST   /api/v1/cases/{case_id}/reopen
    POST   /api/v1/cases/{case_id}/finding
    POST   /api/v1/cases/{case_id}/duplicate
"""

import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.database import get_db
from backend.app.models.models import (
    Investigation, CaseNote, CaseInspection, CaseAuditEvent,
    ProductCluster, Scan, ExtractedField, RuleResult,
    ConsistencyCheck, User, Product, CitizenReport,
)

router = APIRouter(prefix="/cases", tags=["Case Management"])

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_TRANSITIONS = {
    "REVIEW_REQUIRED":       {"UNDER_REVIEW", "DISMISSED", "DUPLICATE"},
    "UNDER_REVIEW":          {"EVIDENCE_VERIFIED", "ACTION_REQUIRED", "EVIDENCE_INSUFFICIENT", "DISMISSED"},
    "EVIDENCE_VERIFIED":     {"ACTION_REQUIRED", "DISMISSED"},
    "ACTION_REQUIRED":       {"INSPECTION_ASSIGNED", "RESOLVED"},
    "INSPECTION_ASSIGNED":   {"RESOLVED"},
    "RESOLVED":              {"UNDER_REVIEW"},
    "CLOSED":                {"UNDER_REVIEW"},
    "EVIDENCE_INSUFFICIENT": {"UNDER_REVIEW"},
    "DISMISSED":             {"UNDER_REVIEW"},
    "DUPLICATE":             set(),
}

TERMINAL_STATUSES = {"CLOSED", "DUPLICATE"}
REOPEN_STATUSES   = {"RESOLVED", "CLOSED", "DISMISSED", "EVIDENCE_INSUFFICIENT"}

VALID_TRIGGERS = {
    "CROSS_EVIDENCE_CONFLICT",
    "POTENTIAL_NON_COMPLIANCE",
    "REPEATED_OBSERVATION",
    "OFFICER_CREATED",
    "CITIZEN_OBSERVATION",
    "EVIDENCE_PATTERN",
    "PRIORITIZATION_SIGNAL",
}

VALID_FINDINGS = {
    "EVIDENCE_VERIFIED",
    "ISSUE_NOT_CONFIRMED",
    "MORE_EVIDENCE_REQUIRED",
    "INSPECTION_REQUIRED",
    "DUPLICATE_CASE",
    "RESOLVED",
}

VALID_CLOSURE_OUTCOMES = {
    "EVIDENCE_INSUFFICIENT",
    "ISSUE_NOT_CONFIRMED",
    "DUPLICATE",
    "RESOLVED_AFTER_VERIFICATION",
    "INSPECTION_COMPLETED",
}

CASE_DISCLAIMER = (
    "LM-Screen does not make statutory enforcement decisions. "
    "This case represents an evidence-backed screening signal for authorized officer review. "
    "All enforcement actions remain with authorized Legal Metrology officers following "
    "applicable departmental procedures."
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_officer(db: Session, x_user_role: Optional[str]) -> User:
    if x_user_role and x_user_role.upper() not in ("OFFICER", "ADMIN"):
        raise HTTPException(status_code=403, detail="Officer authorization required.")
    officer = db.query(User).filter(User.role == "OFFICER").first()
    if not officer:
        officer = User(
            email="officer@legalmetrology.gov.in",
            hashed_password="hashed_placeholder",
            full_name="Inspector R. K. Sharma",
            role="OFFICER",
            badge_number="LM-OFFICER-1082"
        )
        db.add(officer)
        db.flush()
    return officer


def _generate_case_number(db: Session) -> str:
    year = datetime.datetime.utcnow().year
    count = db.query(func.count(Investigation.id)).scalar() or 0
    return f"LM-{year}-{str(count + 1).zfill(5)}"


def _add_audit_event(
    db: Session,
    case_id: str,
    action: str,
    actor_id: Optional[str] = None,
    old_status: Optional[str] = None,
    new_status: Optional[str] = None,
    reason: Optional[str] = None,
    detail: Optional[dict] = None,
):
    event = CaseAuditEvent(
        case_id=case_id,
        actor_id=actor_id,
        action=action,
        old_status=old_status,
        new_status=new_status,
        reason=reason,
        detail=detail or {},
    )
    db.add(event)


def _transition_status(case: Investigation, new_status: str):
    current = case.status
    allowed = VALID_TRANSITIONS.get(current, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Invalid status transition: {current} -> {new_status}. "
                f"Allowed from {current}: {sorted(allowed) or 'none (terminal state)'}."
            )
        )


def _serialize_case_summary(case: Investigation, db: Session) -> dict:
    cluster = db.query(ProductCluster).filter(ProductCluster.id == case.cluster_id).first() if case.cluster_id else None
    identity = case.product_identity_snapshot or {}
    officer = db.query(User).filter(User.id == case.assigned_officer).first() if case.assigned_officer else None

    product_display = (
        identity.get("product_name") or
        (cluster.product_name if cluster else None) or
        "Unknown Product"
    )
    if identity.get("brand"):
        product_display = f"{identity['brand']} {product_display}"

    source_ids = case.source_scan_ids or ([case.scan_id] if case.scan_id else [])
    evidence_count = (
        db.query(func.count(ExtractedField.id))
        .filter(ExtractedField.scan_id.in_(source_ids))
        .scalar()
    ) if source_ids else 0

    conflict_count = (
        db.query(func.count(ConsistencyCheck.id))
        .filter(
            ConsistencyCheck.scan_id.in_(source_ids),
            ConsistencyCheck.status == "REVIEW_REQUIRED"
        )
        .scalar()
    ) if source_ids else 0

    return {
        "case_id": case.id,
        "case_number": case.case_number,
        "product": {
            "name": product_display,
            "brand": identity.get("brand"),
            "gtin": identity.get("gtin"),
            "category": identity.get("category"),
            "net_quantity": identity.get("net_quantity"),
        },
        "trigger_type": case.trigger_type,
        "trigger_description": case.trigger_description,
        "priority": case.priority,
        "status": case.status,
        "finding": case.finding,
        "assigned_officer": {
            "id": officer.id,
            "name": officer.full_name,
            "badge": officer.badge_number
        } if officer else None,
        "evidence_count": evidence_count,
        "conflict_count": conflict_count,
        "cluster_id": case.cluster_id,
        "created_at": case.created_at.isoformat(),
        "updated_at": case.updated_at.isoformat(),
    }


def _serialize_case_detail(case: Investigation, db: Session) -> dict:
    summary = _serialize_case_summary(case, db)
    source_ids = case.source_scan_ids or ([case.scan_id] if case.scan_id else [])

    # Evidence chain
    evidence_items = []
    if source_ids:
        fields = db.query(ExtractedField).filter(ExtractedField.scan_id.in_(source_ids)).all()
        for f in fields:
            corrections = [
                {
                    "original_value": c.original_value,
                    "corrected_value": c.corrected_value,
                    "reason": c.reason,
                    "corrected_at": c.created_at.isoformat()
                }
                for c in (f.corrections or [])
            ]
            evidence_items.append({
                "evidence_id": f.id,
                "scan_id": f.scan_id,
                "field_name": f.field_name,
                "raw_value": f.raw_value,
                "normalized_value": f.normalized_value,
                "evidence_state": f.evidence_state,
                "confidence": f.confidence,
                "source_type": f.source_type,
                "source_image_id": f.source_image_id,
                "source_bbox": f.source_bbox,
                "extraction_method": f.extraction_method,
                "corrections": corrections,
                "quality_reasons": f.quality_reasons or [],
            })

    # Applicable requirements
    rule_results = []
    if source_ids:
        rrs = db.query(RuleResult).filter(RuleResult.scan_id.in_(source_ids)).all()
        for r in rrs:
            rule_results.append({
                "rule_id": r.rule_id,
                "rule_name": r.rule_name,
                "status": r.status,
                "applicability": r.applicability,
                "reason": r.reason,
                "confidence": r.confidence,
                "evaluated_at": r.evaluated_at.isoformat(),
            })

    # Consistency checks
    consistency_checks = []
    if source_ids:
        ccs = db.query(ConsistencyCheck).filter(ConsistencyCheck.scan_id.in_(source_ids)).all()
        for c in ccs:
            consistency_checks.append({
                "check_id": c.id,
                "check_type": c.check_type,
                "status": c.status,
                "observed_values": c.observed_values,
                "calculated_value": c.calculated_value,
                "explanation": c.explanation,
                "evidence_ids": c.evidence_ids or [],
                "created_at": c.created_at.isoformat(),
            })

    # Cluster / related observations
    cluster = db.query(ProductCluster).filter(ProductCluster.id == case.cluster_id).first() if case.cluster_id else None
    cluster_info = None
    if cluster:
        cluster_scans = db.query(Scan).filter(Scan.cluster_id == cluster.id).all()
        cluster_info = {
            "cluster_id": cluster.id,
            "observation_count": cluster.report_count,
            "ai_flag_count": cluster.ai_flag_count,
            "match_method": cluster.match_method,
            "match_strength": cluster.match_strength,
            "priority_class": cluster.priority_class,
            "priority_reasons": cluster.priority_reasons or [],
            "evidence_strength": cluster.evidence_strength,
            "actionability_state": cluster.actionability_state,
            "related_scan_count": len(cluster_scans),
            "related_scan_ids": [s.id for s in cluster_scans],
        }

    notes = [
        {
            "note_id": n.id,
            "author": n.author.full_name if n.author else "Unknown Officer",
            "note": n.note,
            "created_at": n.created_at.isoformat()
        }
        for n in case.notes
    ]

    inspections = [
        {
            "inspection_id": i.id,
            "assigned_to": i.assignee.full_name if i.assignee else None,
            "assigned_by": i.assigner.full_name if i.assigner else None,
            "status": i.status,
            "location_hint": i.location_hint,
            "scheduled_at": i.scheduled_at.isoformat() if i.scheduled_at else None,
            "notes": i.notes,
            "inspection_notes": i.inspection_notes,
            "completed_at": i.completed_at.isoformat() if i.completed_at else None,
            "assigned_at": i.assigned_at.isoformat(),
        }
        for i in case.inspections
    ]

    audit_trail = [
        {
            "event_id": e.id,
            "action": e.action,
            "actor": e.actor.full_name if e.actor else "System",
            "old_status": e.old_status,
            "new_status": e.new_status,
            "reason": e.reason,
            "detail": e.detail or {},
            "timestamp": e.created_at.isoformat()
        }
        for e in sorted(case.audit_events, key=lambda x: x.created_at)
    ]

    return {
        **summary,
        "reason": case.reason,
        "product_identity_snapshot": case.product_identity_snapshot,
        "source_scan_ids": case.source_scan_ids,
        "finding": case.finding,
        "finding_notes": case.finding_notes,
        "finding_recorded_at": case.finding_recorded_at.isoformat() if case.finding_recorded_at else None,
        "closure_outcome": case.closure_outcome,
        "closure_reason": case.closure_reason,
        "closed_at": case.closed_at.isoformat() if case.closed_at else None,
        "duplicate_of_case_id": case.duplicate_of_case_id,
        "evidence": evidence_items,
        "rule_results": rule_results,
        "consistency_checks": consistency_checks,
        "cluster": cluster_info,
        "notes": notes,
        "inspections": inspections,
        "audit_trail": audit_trail,
        "disclaimer": CASE_DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# Trigger validation
# ---------------------------------------------------------------------------

def _validate_trigger(trigger_type: str, scan_id: Optional[str], cluster_id: Optional[str], db: Session) -> dict:
    """Raw OCR alone does NOT qualify for case creation."""
    if trigger_type == "OFFICER_CREATED":
        return {"valid": True, "reason": "Officer-initiated case."}

    if trigger_type == "CROSS_EVIDENCE_CONFLICT":
        scan_ids = [scan_id] if scan_id else []
        if cluster_id:
            rows = db.query(Scan.id).filter(Scan.cluster_id == cluster_id).all()
            scan_ids += [r[0] for r in rows]
        if scan_ids:
            conflict = db.query(ConsistencyCheck).filter(
                ConsistencyCheck.scan_id.in_(scan_ids),
                ConsistencyCheck.status == "REVIEW_REQUIRED"
            ).first()
            if conflict:
                return {"valid": True, "reason": f"Cross-evidence conflict detected: {conflict.explanation}"}
        return {
            "valid": False,
            "reason": "CROSS_EVIDENCE_CONFLICT requires at least one ConsistencyCheck with REVIEW_REQUIRED status."
        }

    if trigger_type == "POTENTIAL_NON_COMPLIANCE":
        if scan_id:
            issue = db.query(RuleResult).filter(
                RuleResult.scan_id == scan_id,
                RuleResult.status.in_(["POTENTIAL_NON_COMPLIANCE", "NEEDS_REVIEW"])
            ).first()
            if issue:
                return {"valid": True, "reason": f"Rule issue identified: {issue.rule_name}"}
        return {
            "valid": False,
            "reason": "POTENTIAL_NON_COMPLIANCE requires a rule result flagging a potential issue."
        }

    if trigger_type == "REPEATED_OBSERVATION":
        if cluster_id:
            cluster = db.query(ProductCluster).filter(ProductCluster.id == cluster_id).first()
            if cluster and cluster.report_count >= 2:
                return {"valid": True, "reason": f"Product observed {cluster.report_count} times."}
        return {"valid": False, "reason": "REPEATED_OBSERVATION requires a cluster with >= 2 observations."}

    if trigger_type in ("CITIZEN_OBSERVATION", "EVIDENCE_PATTERN", "PRIORITIZATION_SIGNAL"):
        if cluster_id or scan_id:
            return {"valid": True, "reason": f"Officer-reviewed {trigger_type} trigger."}
        return {"valid": False, "reason": f"{trigger_type} requires a cluster_id or scan_id."}

    return {"valid": False, "reason": f"Unknown trigger type: {trigger_type}"}


# ===========================================================================
# ROUTES
# ===========================================================================

@router.post("")
def create_case(
    payload: dict,
    db: Session = Depends(get_db),
    x_user_role: Optional[str] = Header(None)
):
    """Create a case from a meaningful screening signal. Raw OCR alone is rejected."""
    officer = _get_officer(db, x_user_role)

    trigger_type = payload.get("trigger_type", "OFFICER_CREATED")
    if trigger_type not in VALID_TRIGGERS:
        raise HTTPException(status_code=400, detail=f"Invalid trigger_type. Valid: {sorted(VALID_TRIGGERS)}")

    scan_id    = payload.get("scan_id")
    cluster_id = payload.get("cluster_id")
    product_id = payload.get("product_id")

    # Resolve cluster from scan
    if scan_id and not cluster_id:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if scan:
            cluster_id = cluster_id or scan.cluster_id
            product_id = product_id or scan.product_id

    # Resolve product from cluster
    if cluster_id and not product_id:
        cluster = db.query(ProductCluster).filter(ProductCluster.id == cluster_id).first()
        if cluster:
            product_id = product_id or cluster.product_id

    # Validate trigger has evidence backing
    validation = _validate_trigger(trigger_type, scan_id, cluster_id, db)
    if not validation["valid"]:
        raise HTTPException(
            status_code=422,
            detail=f"Case creation blocked: {validation['reason']} A case must be based on actual screening signals."
        )

    # Build product identity snapshot
    identity_snapshot = {}
    cluster = db.query(ProductCluster).filter(ProductCluster.id == cluster_id).first() if cluster_id else None
    product = db.query(Product).filter(Product.id == product_id).first() if product_id else None
    if cluster:
        identity_snapshot = {
            "brand": cluster.brand,
            "product_name": cluster.product_name,
            "variant": cluster.variant,
            "gtin": cluster.gtin,
            "net_quantity": cluster.net_quantity,
        }
    elif product:
        identity_snapshot = {
            "brand": product.brand_name,
            "product_name": product.product_name,
            "gtin": product.gtin,
            "category": product.category,
        }

    for field in ("brand", "product_name", "variant", "gtin", "category", "net_quantity"):
        if payload.get(field):
            identity_snapshot[field] = payload[field]

    source_scan_ids = payload.get("source_scan_ids", [])
    if scan_id and scan_id not in source_scan_ids:
        source_scan_ids = [scan_id] + source_scan_ids

    priority = payload.get("priority", "MEDIUM")
    if cluster:
        priority_map = {"PRIORITY_REVIEW": "HIGH", "STANDARD_REVIEW": "MEDIUM", "EVIDENCE_INSUFFICIENT": "LOW"}
        priority = priority_map.get(cluster.priority_class, "MEDIUM")

    try:
        case = Investigation(
            case_number=_generate_case_number(db),
            product_id=product_id,
            cluster_id=cluster_id,
            scan_id=scan_id,
            source_scan_ids=source_scan_ids,
            trigger_type=trigger_type,
            trigger_description=validation["reason"],
            product_identity_snapshot=identity_snapshot,
            priority=priority,
            status="REVIEW_REQUIRED",
            assigned_officer=officer.id,
            reason=payload.get("reason", f"Case created from {trigger_type} trigger."),
        )
        db.add(case)
        db.flush()

        _add_audit_event(
            db, case.id,
            action="CASE_CREATED",
            actor_id=officer.id,
            new_status="REVIEW_REQUIRED",
            reason=f"Trigger: {trigger_type}. {validation['reason']}",
            detail={"trigger_type": trigger_type, "source_scan_ids": source_scan_ids}
        )

        if cluster and cluster.status == "REVIEW_REQUIRED":
            cluster.status = "UNDER_REVIEW"

        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create case: {str(e)}")

    return {
        "case_id": case.id,
        "case_number": case.case_number,
        "status": case.status,
        "trigger_type": case.trigger_type,
        "priority": case.priority,
        "product": identity_snapshot,
        "message": "Case created. Officer review is now open.",
        "disclaimer": CASE_DISCLAIMER,
    }


@router.get("")
def list_cases(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    trigger_type: Optional[str] = Query(None),
    cluster_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("updated_at"),
    sort_dir: str = Query("desc"),
    db: Session = Depends(get_db),
    x_user_role: Optional[str] = Header(None)
):
    """List cases with filtering, sorting and pagination."""
    if x_user_role and x_user_role.upper() not in ("OFFICER", "ADMIN"):
        raise HTTPException(status_code=403, detail="Officer authorization required.")

    q = db.query(Investigation)
    if status:
        q = q.filter(Investigation.status == status)
    if priority:
        q = q.filter(Investigation.priority == priority)
    if trigger_type:
        q = q.filter(Investigation.trigger_type == trigger_type)
    if cluster_id:
        q = q.filter(Investigation.cluster_id == cluster_id)

    sort_col = getattr(Investigation, sort_by, Investigation.updated_at)
    q = q.order_by(sort_col.asc() if sort_dir == "asc" else sort_col.desc())

    total = q.count()
    cases = q.offset((page - 1) * page_size).limit(page_size).all()

    results = []
    for case in cases:
        summary = _serialize_case_summary(case, db)
        if search:
            needle = search.lower()
            name_match = needle in (summary["product"]["name"] or "").lower()
            num_match  = needle in (case.case_number or "").lower()
            if not name_match and not num_match:
                continue
        results.append(summary)

    status_counts = {}
    for st in ["REVIEW_REQUIRED","UNDER_REVIEW","EVIDENCE_VERIFIED","ACTION_REQUIRED",
               "INSPECTION_ASSIGNED","RESOLVED","CLOSED","DISMISSED","EVIDENCE_INSUFFICIENT","DUPLICATE"]:
        status_counts[st] = db.query(func.count(Investigation.id)).filter(Investigation.status == st).scalar()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "cases": results,
        "status_counts": status_counts,
    }


@router.get("/{case_id}")
def get_case(
    case_id: str,
    db: Session = Depends(get_db),
    x_user_role: Optional[str] = Header(None)
):
    """Full case detail with evidence chain, consistency checks, notes, audit trail."""
    if x_user_role and x_user_role.upper() not in ("OFFICER", "ADMIN"):
        raise HTTPException(status_code=403, detail="Officer authorization required.")
    case = db.query(Investigation).filter(Investigation.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    return _serialize_case_detail(case, db)


@router.patch("/{case_id}/status")
def transition_status(
    case_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    x_user_role: Optional[str] = Header(None)
):
    """Transition case status. Server validates the transition."""
    officer = _get_officer(db, x_user_role)
    case = db.query(Investigation).filter(Investigation.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")

    new_status = payload.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail="'status' field required.")

    _transition_status(case, new_status)
    old_status = case.status
    case.status = new_status

    _add_audit_event(db, case_id, "STATUS_CHANGED", actor_id=officer.id,
                     old_status=old_status, new_status=new_status,
                     reason=payload.get("reason"))
    db.commit()

    return {
        "case_id": case_id,
        "case_number": case.case_number,
        "old_status": old_status,
        "new_status": new_status,
    }


@router.post("/{case_id}/assign")
def assign_case(
    case_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    x_user_role: Optional[str] = Header(None)
):
    """Assign or reassign case to an authorized officer."""
    officer = _get_officer(db, x_user_role)
    case = db.query(Investigation).filter(Investigation.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    if case.status in TERMINAL_STATUSES:
        raise HTTPException(status_code=422, detail=f"Cannot reassign a {case.status} case.")

    assignee_id = payload.get("officer_id", officer.id)
    assignee = db.query(User).filter(User.id == assignee_id, User.role == "OFFICER").first()
    if not assignee:
        raise HTTPException(status_code=404, detail="Assignee officer not found.")

    old_assignee = case.assigned_officer
    case.assigned_officer = assignee.id

    if case.status == "REVIEW_REQUIRED":
        case.status = "UNDER_REVIEW"
        _add_audit_event(db, case_id, "STATUS_CHANGED", actor_id=officer.id,
                         old_status="REVIEW_REQUIRED", new_status="UNDER_REVIEW",
                         reason="Auto-transitioned on assignment.")

    _add_audit_event(db, case_id, "ASSIGNED", actor_id=officer.id,
                     reason=payload.get("reason"),
                     detail={"from_officer": old_assignee, "to_officer": assignee.id,
                             "to_officer_name": assignee.full_name})
    db.commit()

    return {
        "case_id": case_id,
        "case_number": case.case_number,
        "assigned_to": assignee.full_name,
        "badge": assignee.badge_number,
        "status": case.status,
    }


@router.post("/{case_id}/notes")
def add_note(
    case_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    x_user_role: Optional[str] = Header(None)
):
    """Officer adds a note. Citizens cannot write officer notes."""
    officer = _get_officer(db, x_user_role)
    case = db.query(Investigation).filter(Investigation.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")

    note_text = (payload.get("note") or "").strip()
    if not note_text:
        raise HTTPException(status_code=400, detail="Note text is required.")

    note = CaseNote(case_id=case_id, author_id=officer.id, note=note_text)
    db.add(note)

    _add_audit_event(db, case_id, "NOTE_ADDED", actor_id=officer.id,
                     detail={"note_length": len(note_text)})
    db.commit()

    return {
        "note_id": note.id,
        "case_id": case_id,
        "author": officer.full_name,
        "note": note.note,
        "created_at": note.created_at.isoformat(),
    }


@router.post("/{case_id}/evidence")
def link_evidence(
    case_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    x_user_role: Optional[str] = Header(None)
):
    """Link additional scan evidence. Scan must exist in Evidence Graph."""
    officer = _get_officer(db, x_user_role)
    case = db.query(Investigation).filter(Investigation.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    if case.status in TERMINAL_STATUSES:
        raise HTTPException(status_code=422, detail=f"Cannot add evidence to a {case.status} case.")

    additional_scan_id = payload.get("scan_id")
    if not additional_scan_id:
        raise HTTPException(status_code=400, detail="scan_id is required.")

    scan = db.query(Scan).filter(Scan.id == additional_scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found in system.")

    existing = case.source_scan_ids or []
    if additional_scan_id in existing:
        return {"message": "Scan already linked.", "case_id": case_id}

    case.source_scan_ids = existing + [additional_scan_id]

    _add_audit_event(db, case_id, "EVIDENCE_LINKED", actor_id=officer.id,
                     reason=payload.get("reason", "Additional evidence linked."),
                     detail={"scan_id": additional_scan_id})
    db.commit()

    return {
        "case_id": case_id,
        "case_number": case.case_number,
        "linked_scan_id": additional_scan_id,
        "total_source_scans": len(case.source_scan_ids),
    }


@router.post("/{case_id}/inspection")
def create_inspection(
    case_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    x_user_role: Optional[str] = Header(None)
):
    """Create a field inspection assignment. Case must be in ACTION_REQUIRED or compatible state."""
    officer = _get_officer(db, x_user_role)
    case = db.query(Investigation).filter(Investigation.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    if case.status in TERMINAL_STATUSES:
        raise HTTPException(status_code=422, detail=f"Cannot assign inspection to a {case.status} case.")

    if case.status not in {"ACTION_REQUIRED", "UNDER_REVIEW", "EVIDENCE_VERIFIED"}:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Inspection requires ACTION_REQUIRED, EVIDENCE_VERIFIED, or UNDER_REVIEW status. "
                f"Current: {case.status}."
            )
        )

    scheduled_at = None
    if payload.get("scheduled_at"):
        try:
            scheduled_at = datetime.datetime.fromisoformat(payload["scheduled_at"])
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid scheduled_at. Use ISO 8601.")

    inspection = CaseInspection(
        case_id=case_id,
        assigned_to=payload.get("assigned_to", officer.id),
        assigned_by=officer.id,
        location_hint=payload.get("location_hint"),
        scheduled_at=scheduled_at,
        notes=payload.get("notes"),
        status="PENDING",
    )
    db.add(inspection)
    db.flush()

    old_status = case.status
    case.status = "INSPECTION_ASSIGNED"

    _add_audit_event(db, case_id, "INSPECTION_ASSIGNED", actor_id=officer.id,
                     old_status=old_status, new_status="INSPECTION_ASSIGNED",
                     reason=payload.get("notes", "Field inspection assigned."),
                     detail={"inspection_id": inspection.id,
                             "location_hint": payload.get("location_hint")})
    db.commit()

    return {
        "inspection_id": inspection.id,
        "case_id": case_id,
        "case_number": case.case_number,
        "case_status": case.status,
        "message": (
            "Inspection assignment recorded in LM-Screen. "
            "Ready for integration with departmental workflow."
        ),
    }


@router.get("/{case_id}/audit")
def get_case_audit(
    case_id: str,
    db: Session = Depends(get_db),
    x_user_role: Optional[str] = Header(None)
):
    """Return the complete, immutable audit trail for a case."""
    if x_user_role and x_user_role.upper() not in ("OFFICER", "ADMIN"):
        raise HTTPException(status_code=403, detail="Officer authorization required.")
    case = db.query(Investigation).filter(Investigation.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")

    events = sorted(case.audit_events, key=lambda e: e.created_at)
    return {
        "case_id": case_id,
        "case_number": case.case_number,
        "audit_trail": [
            {
                "event_id": e.id,
                "action": e.action,
                "actor": e.actor.full_name if e.actor else "System",
                "actor_id": e.actor_id,
                "old_status": e.old_status,
                "new_status": e.new_status,
                "reason": e.reason,
                "detail": e.detail or {},
                "timestamp": e.created_at.isoformat(),
            }
            for e in events
        ],
        "event_count": len(events),
    }


@router.post("/{case_id}/finding")
def record_finding(
    case_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    x_user_role: Optional[str] = Header(None)
):
    """Record officer's formal finding. Auto-transitions status based on finding type."""
    officer = _get_officer(db, x_user_role)
    case = db.query(Investigation).filter(Investigation.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    if case.status in TERMINAL_STATUSES:
        raise HTTPException(status_code=422, detail=f"Cannot record finding on a {case.status} case.")

    finding = payload.get("finding")
    if not finding or finding not in VALID_FINDINGS:
        raise HTTPException(status_code=400, detail=f"Invalid finding. Valid: {sorted(VALID_FINDINGS)}")

    case.finding = finding
    case.finding_notes = (payload.get("notes") or "").strip()
    case.finding_recorded_at = datetime.datetime.utcnow()
    case.finding_recorded_by = officer.id

    # Auto-transition
    old_status = case.status
    if finding == "MORE_EVIDENCE_REQUIRED":
        if "EVIDENCE_INSUFFICIENT" in VALID_TRANSITIONS.get(case.status, set()):
            case.status = "EVIDENCE_INSUFFICIENT"
            _add_audit_event(db, case_id, "STATUS_CHANGED", actor_id=officer.id,
                             old_status=old_status, new_status="EVIDENCE_INSUFFICIENT")
    elif finding == "INSPECTION_REQUIRED":
        if "ACTION_REQUIRED" in VALID_TRANSITIONS.get(case.status, set()):
            case.status = "ACTION_REQUIRED"
            _add_audit_event(db, case_id, "STATUS_CHANGED", actor_id=officer.id,
                             old_status=old_status, new_status="ACTION_REQUIRED")
    elif finding == "ISSUE_NOT_CONFIRMED":
        if "DISMISSED" in VALID_TRANSITIONS.get(case.status, set()):
            case.status = "DISMISSED"
            _add_audit_event(db, case_id, "STATUS_CHANGED", actor_id=officer.id,
                             old_status=old_status, new_status="DISMISSED",
                             reason="Officer confirmed issue not substantiated.")

    _add_audit_event(db, case_id, "FINDING_RECORDED", actor_id=officer.id,
                     detail={"finding": finding, "notes": case.finding_notes},
                     reason=f"Officer finding: {finding}")
    db.commit()

    return {
        "case_id": case_id,
        "case_number": case.case_number,
        "finding": case.finding,
        "finding_notes": case.finding_notes,
        "status": case.status,
    }


@router.post("/{case_id}/close")
def close_case(
    case_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    x_user_role: Optional[str] = Header(None)
):
    """Close case. Requires structured outcome + reason. No silent closures."""
    officer = _get_officer(db, x_user_role)
    case = db.query(Investigation).filter(Investigation.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    if case.status == "CLOSED":
        raise HTTPException(status_code=422, detail="Case is already closed.")
    if case.status == "DUPLICATE":
        raise HTTPException(status_code=422, detail="Duplicate cases cannot be independently closed.")

    outcome = payload.get("closure_outcome")
    if not outcome or outcome not in VALID_CLOSURE_OUTCOMES:
        raise HTTPException(status_code=400,
                            detail=f"closure_outcome required. Valid: {sorted(VALID_CLOSURE_OUTCOMES)}")

    closure_reason = (payload.get("reason") or "").strip()
    if not closure_reason:
        raise HTTPException(status_code=400, detail="A closure reason is required.")

    old_status = case.status
    case.status = "CLOSED"
    case.closure_outcome = outcome
    case.closure_reason = closure_reason
    case.closed_at = datetime.datetime.utcnow()
    case.closed_by = officer.id

    _add_audit_event(db, case_id, "CASE_CLOSED", actor_id=officer.id,
                     old_status=old_status, new_status="CLOSED",
                     reason=closure_reason, detail={"closure_outcome": outcome})
    db.commit()

    return {
        "case_id": case_id,
        "case_number": case.case_number,
        "status": "CLOSED",
        "closure_outcome": outcome,
        "closure_reason": closure_reason,
        "closed_at": case.closed_at.isoformat(),
    }


@router.post("/{case_id}/reopen")
def reopen_case(
    case_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    x_user_role: Optional[str] = Header(None)
):
    """Reopen closed/resolved/dismissed case. Original closure events preserved in audit trail."""
    officer = _get_officer(db, x_user_role)
    case = db.query(Investigation).filter(Investigation.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    if case.status not in REOPEN_STATUSES:
        raise HTTPException(status_code=422,
                            detail=f"Status {case.status} cannot be reopened. Reopenable: {sorted(REOPEN_STATUSES)}")

    reason = (payload.get("reason") or "").strip()
    if not reason:
        raise HTTPException(status_code=400, detail="A reopen reason is required.")

    old_status = case.status
    case.status = "UNDER_REVIEW"

    _add_audit_event(db, case_id, "CASE_REOPENED", actor_id=officer.id,
                     old_status=old_status, new_status="UNDER_REVIEW", reason=reason)
    db.commit()

    return {
        "case_id": case_id,
        "case_number": case.case_number,
        "previous_status": old_status,
        "new_status": "UNDER_REVIEW",
        "message": "Case reopened. Original closure events preserved in audit trail.",
    }


@router.post("/{case_id}/duplicate")
def mark_duplicate(
    case_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    x_user_role: Optional[str] = Header(None)
):
    """Mark this case as a duplicate of another existing case."""
    officer = _get_officer(db, x_user_role)
    case = db.query(Investigation).filter(Investigation.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    if case.status in TERMINAL_STATUSES:
        raise HTTPException(status_code=422, detail=f"Case already in terminal state: {case.status}")

    canonical_id = payload.get("duplicate_of_case_id")
    if not canonical_id:
        raise HTTPException(status_code=400, detail="duplicate_of_case_id required.")
    if canonical_id == case_id:
        raise HTTPException(status_code=400, detail="A case cannot be a duplicate of itself.")

    canonical = db.query(Investigation).filter(Investigation.id == canonical_id).first()
    if not canonical:
        raise HTTPException(status_code=404, detail="Canonical case not found.")

    old_status = case.status
    case.status = "DUPLICATE"
    case.duplicate_of_case_id = canonical_id

    _add_audit_event(db, case_id, "MARKED_DUPLICATE", actor_id=officer.id,
                     old_status=old_status, new_status="DUPLICATE",
                     reason=payload.get("reason", "Marked as duplicate investigation."),
                     detail={"duplicate_of_case_id": canonical_id,
                             "canonical_case_number": canonical.case_number})
    db.commit()

    return {
        "case_id": case_id,
        "case_number": case.case_number,
        "status": "DUPLICATE",
        "duplicate_of_case_id": canonical_id,
        "canonical_case_number": canonical.case_number,
    }
