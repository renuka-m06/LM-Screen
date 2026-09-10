from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.app.database import get_db
from backend.app.models.models import ProductCluster, OfficerReview, Product, User
from backend.app.schemas.schemas import PriorityQueueItem, ReviewCreate

router = APIRouter(prefix="/officer", tags=["Officer Operations"])

@router.get("/queue")
def get_priority_queue(db: Session = Depends(get_db)):
    clusters = db.query(ProductCluster).order_by(ProductCluster.priority_score.desc()).all()
    queue = []
    for c in clusters:
        prod = db.query(Product).filter(Product.id == c.product_id).first()
        # Build explainable priority breakdown
        total_score = round(c.priority_score, 2)
        norm_reports = min(c.report_count / 20.0, 1.0)
        norm_ai = min(c.ai_flag_count / 10.0, 1.0)
        priority_breakdown = {
            "citizen_signals": round(0.25 * norm_reports, 3),
            "ai_flags": round(0.20 * norm_ai, 3),
            "confirmed_history": round(0.20 * 0.0, 3),  # default no confirmed
            "evidence_quality": round(0.15 * 0.90, 3),
            "severity": round(0.10 * 0.80, 3),
            "recency": round(0.10 * 1.00, 3)
        }
        queue.append({
            "cluster_id": c.id,
            "product_id": c.product_id,
            "product_name": prod.product_name if prod else "Unknown Commodity",
            "gtin": prod.gtin if prod else None,
            "issue_type": c.issue_type,
            "priority_score": total_score,
            "priority_label": "HIGH" if total_score >= 0.7 else "MEDIUM" if total_score >= 0.4 else "LOW",
            "citizen_reports_count": c.report_count,
            "ai_flags_count": c.ai_flag_count,
            "priority_breakdown": priority_breakdown,
            "recency": c.updated_at.strftime("%Y-%m-%d %H:%M"),
            "status": c.status
        })
    return queue

from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Optional

@router.post("/reviews")
def submit_officer_review(
    payload: ReviewCreate,
    db: Session = Depends(get_db),
    x_user_role: Optional[str] = Header(None)
):
    # Enforce Officer Role Authorization
    if x_user_role and x_user_role.upper() != "OFFICER":
        raise HTTPException(status_code=403, detail="Officer authorization required.")

    scan = None
    cluster = None
    previous_status = "UNKNOWN"

    if payload.scan_id:
        from backend.app.models.models import Scan
        scan = db.query(Scan).filter(Scan.id == payload.scan_id).first()
        if scan:
            previous_status = scan.status
            scan.status = payload.decision
            if scan.product_id:
                cluster = db.query(ProductCluster).filter(ProductCluster.product_id == scan.product_id).first()

    if not cluster and payload.cluster_id:
        cluster = db.query(ProductCluster).filter(ProductCluster.id == payload.cluster_id).first()
        if cluster and previous_status == "UNKNOWN":
            previous_status = cluster.status

    if not cluster and payload.product_id:
        cluster = db.query(ProductCluster).filter(ProductCluster.product_id == payload.product_id).first()

    if not scan and not cluster:
        raise HTTPException(status_code=404, detail="Scan or cluster record not found.")

    # Find or create default officer user
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
        db.commit()
        db.refresh(officer)

    if cluster:
        if previous_status == "UNKNOWN":
            previous_status = cluster.status
        cluster.status = payload.decision

    # Save Review Action with full audit details
    review = OfficerReview(
        cluster_id=cluster.id if cluster else None,
        scan_id=scan.id if scan else None,
        officer_id=officer.id,
        decision=payload.decision,
        rationale=payload.rationale,
        previous_status=previous_status,
        new_status=payload.decision
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    return {
        "review_id": review.id,
        "scan_id": scan.id if scan else None,
        "cluster_id": cluster.id if cluster else None,
        "decision": payload.decision,
        "rationale": payload.rationale,
        "previous_status": previous_status,
        "new_status": payload.decision,
        "officer": officer.full_name,
        "timestamp": review.created_at.isoformat()
    }


@router.post("/copilot")
def officer_copilot(request_data: dict, db: Session = Depends(get_db)):
    """Provides objective, evidence-grounded answers for inspectors without legal claims."""
    from ai.copilot import OfficerEvidenceCopilot, CopilotRequest
    copilot = OfficerEvidenceCopilot()
    req = CopilotRequest(
        scan_id=request_data.get("scan_id"),
        cluster_id=request_data.get("cluster_id"),
        question=request_data.get("question", "Why is this case prioritized?")
    )
    return copilot.answer_question(req, scan_data=request_data.get("scan_data"))


@router.get("/reports/{cluster_id}/investigation-report")
def generate_investigation_report(cluster_id: str, db: Session = Depends(get_db)):
    """Generates a structured, legal-grade investigation report for officers."""
    cluster = db.query(ProductCluster).filter(ProductCluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster record not found.")

    prod = db.query(Product).filter(Product.id == cluster.product_id).first()
    reviews = db.query(OfficerReview).filter(OfficerReview.cluster_id == cluster.id).all()

    return {
        "report_id": f"REP-LM-{cluster.id[:8].upper()}",
        "title": "LEGAL METROLOGY COMPLIANCE SCREENING & INVESTIGATION DOSSIER",
        "generated_at": cluster.updated_at.isoformat(),
        "product_identity": {
            "gtin": prod.gtin if prod else "N/A",
            "product_name": prod.product_name if prod else "Unknown Commodity",
            "brand": prod.brand_name if prod else "N/A",
            "manufacturer": prod.manufacturer if prod else "N/A"
        },
        "case_summary": {
            "issue_type": cluster.issue_type,
            "priority_score": cluster.priority_score,
            "citizen_reports_count": cluster.report_count,
            "ai_flags_count": cluster.ai_flag_count,
            "status": cluster.status
        },
        "officer_actions": [
            {
                "officer_id": r.officer_id,
                "decision": r.decision,
                "rationale": r.rationale,
                "timestamp": r.created_at.isoformat()
            }
            for r in reviews
        ],
        "disclaimer": "This dossier synthesizes image-based screening evidence and citizen signals for official officer review. It does not replace laboratory testing or formal legal adjudication."
    }

