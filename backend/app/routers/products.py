from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import datetime

from backend.app.database import get_db
from backend.app.models.models import Product, Scan, CitizenReport, ProductCluster, OfficerReview, RuleResult

router = APIRouter(prefix="/products", tags=["Product Intelligence"])


@router.get("/clusters/{cluster_id}")
def get_cluster(cluster_id: str, db: Session = Depends(get_db)):
    cluster = db.query(ProductCluster).filter(ProductCluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found.")
        
    scans = db.query(Scan).filter(Scan.cluster_id == cluster_id).all()
    reports = db.query(CitizenReport).filter(CitizenReport.scan_id.in_([s.id for s in scans]) | (CitizenReport.product_id == cluster.product_id)).all()
    reviews = db.query(OfficerReview).filter(OfficerReview.cluster_id == cluster_id).all()
    
    # MRP Consistency
    mrp_obs = {}
    for scan in scans:
        for ev in scan.extracted_fields:
            if ev.field_name == "mrp" and ev.normalized_value:
                mrp_obs[ev.normalized_value] = mrp_obs.get(ev.normalized_value, 0) + 1

    # Findings/Issues aggregation
    issues = {}
    for scan in scans:
        for r in scan.rule_results:
            if r.status in ["POTENTIAL_NON_COMPLIANCE", "NEEDS_REVIEW"]:
                issues[r.rule_name] = issues.get(r.rule_name, 0) + 1

    return {
        "cluster_id": cluster.id,
        "product_id": cluster.product_id,
        "gtin": cluster.gtin,
        "brand": cluster.brand,
        "product_name": cluster.product_name,
        "variant": cluster.variant,
        "net_quantity": cluster.net_quantity,
        "match_method": cluster.match_method,
        "match_strength": cluster.match_strength,
        "priority_class": cluster.priority_class,
        "priority_reasons": cluster.priority_reasons,
        "evidence_strength": cluster.evidence_strength,
        "actionability_state": cluster.actionability_state,
        "report_count": cluster.report_count,
        "status": cluster.status,
        "scans": [
            {
                "scan_id": s.id,
                "timestamp": s.timestamp.isoformat(),
                "status": s.status,
                "duplicate_of_scan_id": s.duplicate_of_scan_id
            } for s in scans
        ],
        "citizen_reports": [
            {
                "report_id": r.id,
                "issue_category": r.issue_category,
                "created_at": r.created_at.isoformat()
            } for r in reports
        ],
        "mrp_observations": [{"value": k, "count": v} for k, v in mrp_obs.items()],
        "potential_issues": [{"issue": k, "count": v} for k, v in issues.items()],
        "audit_trail": [
            {
                "review_id": rev.id,
                "decision": rev.decision,
                "rationale": rev.rationale,
                "timestamp": rev.created_at.isoformat()
            } for rev in reviews
        ]
    }

@router.get("/{product_id}/intelligence")
def get_product_intelligence(product_id: str, db: Session = Depends(get_db)):
    """
    Returns a unified Product Intelligence view:
    - Product metadata
    - Scan history (all screening results for this product)
    - Citizen signals/reports
    - AI-identified issue clusters
    - Officer review audit trail
    - Derived risk summary
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")

    # --- Scan History ---
    scans = db.query(Scan).filter(Scan.product_id == product_id).order_by(Scan.timestamp.desc()).limit(20).all()
    scan_history = []
    for s in scans:
        fields = {f.field_name: f.normalized_value for f in s.extracted_fields}
        rule_summary = []
        for r in s.rule_results:
            rule_summary.append({
                "rule_id": r.rule_id,
                "rule_name": r.rule_name,
                "status": r.status,
                "reason": r.reason,
                "confidence": r.confidence
            })
        scan_history.append({
            "scan_id": s.id,
            "timestamp": s.timestamp.isoformat(),
            "status": s.status,
            "public_label": s.public_label,
            "screening_confidence": s.screening_confidence,
            "quality_status": s.quality_status,
            "rule_version": s.rule_version,
            "extracted_fields": fields,
            "rule_results": rule_summary
        })

    # --- Citizen Signals ---
    reports = db.query(CitizenReport).filter(CitizenReport.product_id == product_id).order_by(CitizenReport.created_at.desc()).all()
    citizen_signals = []
    for r in reports:
        citizen_signals.append({
            "report_id": r.id,
            "issue_category": r.issue_category,
            "description": r.description or "",
            "location_city": r.location_city or "Unknown",
            "status": r.status,
            "created_at": r.created_at.isoformat()
        })

    # --- Issue Clusters & Officer Audit Trail ---
    clusters = db.query(ProductCluster).filter(ProductCluster.product_id == product_id).order_by(ProductCluster.priority_score.desc()).all()
    scan_ids = [s.id for s in scans]

    # Query all officer reviews for these scans or clusters
    reviews_query = db.query(OfficerReview)
    if clusters and scan_ids:
        all_reviews = reviews_query.filter((OfficerReview.cluster_id.in_([c.id for c in clusters])) | (OfficerReview.scan_id.in_(scan_ids))).order_by(OfficerReview.created_at.desc()).all()
    elif scan_ids:
        all_reviews = reviews_query.filter(OfficerReview.scan_id.in_(scan_ids)).order_by(OfficerReview.created_at.desc()).all()
    elif clusters:
        all_reviews = reviews_query.filter(OfficerReview.cluster_id.in_([c.id for c in clusters])).order_by(OfficerReview.created_at.desc()).all()
    else:
        all_reviews = []

    issue_clusters = []
    if clusters:
        for c in clusters:
            reviews = [r for r in all_reviews if r.cluster_id == c.id or (r.scan_id and r.scan_id in scan_ids)]
            audit_trail = [
                {
                    "review_id": rev.id,
                    "scan_id": rev.scan_id,
                    "decision": rev.decision,
                    "rationale": rev.rationale,
                    "previous_status": rev.previous_status,
                    "new_status": rev.new_status,
                    "officer_id": rev.officer_id,
                    "timestamp": rev.created_at.isoformat()
                }
                for rev in reviews
            ]
            issue_clusters.append({
                "cluster_id": c.id,
                "match_method": c.match_method,
                "priority_score": round(c.priority_score, 2),
                "citizen_reports": c.report_count,
                "ai_flags": c.ai_flag_count,
                "status": c.status,
                "updated_at": c.updated_at.isoformat(),
                "audit_trail": audit_trail
            })
    else:
        # Generate virtual cluster view for scan reviews if no cluster record exists yet
        audit_trail = [
            {
                "review_id": rev.id,
                "scan_id": rev.scan_id,
                "decision": rev.decision,
                "rationale": rev.rationale,
                "previous_status": rev.previous_status,
                "new_status": rev.new_status,
                "officer_id": rev.officer_id,
                "timestamp": rev.created_at.isoformat()
            }
            for rev in all_reviews
        ]
        issue_clusters.append({
            "cluster_id": f"cluster_{product.id[:8]}",
            "match_method": "VIRTUAL_CLUSTER",
            "priority_score": 0.85 if len(all_reviews) > 0 else 0.20,
            "citizen_reports": len(citizen_signals),
            "ai_flags": len(scans),
            "status": all_reviews[0].decision if all_reviews else "UNVERIFIED",
            "updated_at": product.created_at.isoformat(),
            "audit_trail": audit_trail
        })

    # --- Derived Risk Summary ---
    pass_count = sum(1 for s in scan_history if s["status"] == "PASS_SCREENING")
    potential_count = sum(1 for s in scan_history if s["status"] == "POTENTIAL_NON_COMPLIANCE")
    review_count = sum(1 for s in scan_history if s["status"] == "NEEDS_REVIEW")

    total_scans = len(scan_history)
    risk_level = "LOW"
    if potential_count > 0:
        risk_level = "ELEVATED"
    if potential_count >= 2 or any(c["priority_score"] > 7.0 for c in issue_clusters):
        risk_level = "HIGH"
    if len(citizen_signals) == 0 and potential_count == 0:
        risk_level = "LOW"

    # Compile most-seen issues from citizen reports
    issue_freq: dict = {}
    for r in citizen_signals:
        cat = r["issue_category"]
        issue_freq[cat] = issue_freq.get(cat, 0) + 1
    top_issues = sorted(issue_freq.items(), key=lambda x: -x[1])[:3]

    # Build evidence chain summary — the "WHY?" section
    evidence_chain = []
    if potential_count > 0:
        evidence_chain.append({
            "signal": "AI Screening",
            "observation": f"{potential_count} of {total_scans} scan(s) flagged as POTENTIAL_NON_COMPLIANCE.",
            "weight": "HIGH"
        })
    if len(citizen_signals) > 0:
        evidence_chain.append({
            "signal": "Citizen Reports",
            "observation": f"{len(citizen_signals)} citizen signal(s) filed. Most reported: {top_issues[0][0] if top_issues else 'N/A'}.",
            "weight": "MEDIUM"
        })
    if any(c["audit_trail"] for c in issue_clusters):
        confirmed = sum(1 for c in issue_clusters for rev in c["audit_trail"] if rev["decision"] == "CONFIRM")
        if confirmed > 0:
            evidence_chain.append({
                "signal": "Officer Review",
                "observation": f"{confirmed} officer review(s) confirmed issues.",
                "weight": "HIGH"
            })
    if not evidence_chain:
        evidence_chain.append({
            "signal": "No Issues Found",
            "observation": "No AI flags, citizen signals, or officer reviews indicate any compliance concern.",
            "weight": "NONE"
        })

    return {
        "product": {
            "product_id": product.id,
            "product_name": product.product_name,
            "gtin": product.gtin,
            "brand_name": product.brand_name,
            "manufacturer": product.manufacturer,
            "category": product.category,
            "registered_at": product.created_at.isoformat()
        },
        "risk_summary": {
            "risk_level": risk_level,
            "total_scans": total_scans,
            "pass_count": pass_count,
            "potential_count": potential_count,
            "review_count": review_count,
            "citizen_signal_count": len(citizen_signals),
            "active_clusters": len([c for c in issue_clusters if c["status"] not in ["CONFIRM", "REJECT"]]),
            "top_issues": [{"issue": k, "count": v} for k, v in top_issues]
        },
        "evidence_chain": evidence_chain,
        "scan_history": scan_history,
        "citizen_signals": citizen_signals,
        "issue_clusters": issue_clusters
    }


@router.get("/{product_id}/timeline")
def get_product_timeline(product_id: str, db: Session = Depends(get_db)):
    """
    Returns historical product timeline tracking changes in MRP, net quantity,
    manufacturer, and declarations over time across historical scans.
    Labels shifts as 'Change detected' requiring review without legal claims.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")

    scans = db.query(Scan).filter(Scan.product_id == product_id).order_by(Scan.timestamp.asc()).all()

    timeline_events = []
    prev_qty = None
    prev_mrp = None

    for idx, s in enumerate(scans):
        fields = {f.field_name: f.normalized_value or f.raw_value for f in s.extracted_fields}
        curr_qty = fields.get("net_quantity")
        curr_mrp = fields.get("mrp")

        changes = []
        if prev_qty and curr_qty and prev_qty != curr_qty:
            changes.append(f"Net quantity statement changed from '{prev_qty}' to '{curr_qty}'")
        if prev_mrp and curr_mrp and prev_mrp != curr_mrp:
            changes.append(f"MRP declaration changed from '{prev_mrp}' to '{curr_mrp}'")

        prev_qty = curr_qty or prev_qty
        prev_mrp = curr_mrp or prev_mrp

        timeline_events.append({
            "event_id": f"evt_{s.id[:8]}",
            "timestamp": s.timestamp.isoformat(),
            "scan_id": s.id,
            "net_quantity": curr_qty or "N/A",
            "mrp": curr_mrp or "N/A",
            "verdict": s.status,
            "has_changes": len(changes) > 0,
            "changes_detected": changes,
            "status_label": "Change detected — Requires Review" if len(changes) > 0 else "Consistent Declaration"
        })

    return {
        "product_id": product.id,
        "product_name": product.product_name,
        "gtin": product.gtin,
        "total_historical_events": len(timeline_events),
        "timeline": timeline_events,
        "disclaimer": "Historical changes are presented as objective observational differences for officer review. They do not automatically constitute legal non-compliance."
    }


@router.get("")
def list_products(db: Session = Depends(get_db)):
    """List all known products."""
    products = db.query(Product).order_by(Product.created_at.desc()).limit(50).all()
    return [
        {
            "product_id": p.id,
            "product_name": p.product_name,
            "gtin": p.gtin,
            "category": p.category,
            "created_at": p.created_at.isoformat()
        }
        for p in products
    ]


