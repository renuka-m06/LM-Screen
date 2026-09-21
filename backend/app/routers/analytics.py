from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import datetime

from backend.app.database import get_db
from backend.app.models.models import (
    Scan, ProductCluster, ExtractedField, RuleResult,
    ConsistencyCheck, CitizenReport, OfficerReview, Product
)

from backend.app.services.ml.registry import ModelRegistry

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/system/health")
def get_system_health():
    """Returns the health and status of integrated ML models."""
    models = ModelRegistry.get_all_models()
    
    # We can also add other system metrics here if needed
    return {
        "status": "OPERATIONAL",
        "models": models
    }

@router.get("/overview")
def get_analytics_overview(
    days: int = Query(30, description="Date range in days"),
    db: Session = Depends(get_db)
):
    since_date = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    
    total_scans = db.query(Scan).filter(Scan.timestamp >= since_date).count()
    total_clusters = db.query(ProductCluster).filter(ProductCluster.created_at >= since_date).count()
    total_evidence = db.query(ExtractedField).filter(ExtractedField.created_at >= since_date).count()
    total_cases = db.query(ProductCluster).count() # Total all time
    
    total_reviews = db.query(OfficerReview).filter(OfficerReview.created_at >= since_date).count()
    total_observations = total_scans + db.query(CitizenReport).filter(CitizenReport.created_at >= since_date).count()
    
    cases_requiring_review = db.query(ProductCluster).filter(
        ProductCluster.status == "REVIEW_REQUIRED"
    ).count()
    
    cases_with_conflicts = db.query(ProductCluster).filter(
        ProductCluster.priority_class == "PRIORITY_REVIEW"
    ).count() # Proxy for major issues, or we could join ConsistencyCheck
    
    cases_with_insufficient_evidence = db.query(ProductCluster).filter(
        ProductCluster.actionability_state == "INSUFFICIENT_EVIDENCE"
    ).count()
    
    return {
        "total_scans": total_scans,
        "total_unique_product_clusters": total_clusters,
        "total_evidence_items": total_evidence,
        "total_cases": total_cases,
        "total_officer_reviewed_cases": total_reviews,
        "total_observations": total_observations,
        "cases_requiring_review": cases_requiring_review,
        "cases_with_evidence_conflicts": cases_with_conflicts,
        "cases_with_insufficient_evidence": cases_with_insufficient_evidence
    }

@router.get("/trends")
def get_analytics_trends(
    days: int = Query(30, description="Date range in days"),
    db: Session = Depends(get_db)
):
    since_date = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    
    # Simple grouping by date
    scans = db.query(
        func.date(Scan.timestamp).label('date'),
        func.count(Scan.id).label('count')
    ).filter(Scan.timestamp >= since_date).group_by(func.date(Scan.timestamp)).all()
    
    observations = db.query(
        func.date(CitizenReport.created_at).label('date'),
        func.count(CitizenReport.id).label('count')
    ).filter(CitizenReport.created_at >= since_date).group_by(func.date(CitizenReport.created_at)).all()
    
    # Merge them into a single timeline map
    timeline = {}
    for i in range(days):
        dt = (datetime.datetime.utcnow() - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        timeline[dt] = {"date": dt, "scans": 0, "observations": 0}
        
    for s in scans:
        if s.date in timeline: timeline[s.date]["scans"] = s.count
    for o in observations:
        if o.date in timeline: timeline[o.date]["observations"] = o.count
        
    return list(timeline.values())

@router.get("/categories")
def get_analytics_categories(
    days: int = Query(30, description="Date range in days"),
    db: Session = Depends(get_db)
):
    since_date = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    
    # Assuming category is stored on Product
    stats = db.query(
        Product.category,
        func.count(ProductCluster.id).label('clusters')
    ).join(ProductCluster, Product.id == ProductCluster.product_id)\
     .filter(ProductCluster.created_at >= since_date)\
     .group_by(Product.category).all()
     
    return [{"category": s.category or "Unknown", "clusters": s.clusters} for s in stats]

@router.get("/requirements")
def get_analytics_requirements(
    days: int = Query(30, description="Date range in days"),
    db: Session = Depends(get_db)
):
    since_date = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    
    stats = db.query(
        ExtractedField.field_name,
        ExtractedField.evidence_state,
        func.count(ExtractedField.id).label('count')
    ).filter(ExtractedField.created_at >= since_date)\
     .group_by(ExtractedField.field_name, ExtractedField.evidence_state).all()
    
    req_map = {}
    for field, state, count in stats:
        if field not in req_map:
            req_map[field] = {}
        req_map[field][state] = count
        
    res = []
    for field, states in req_map.items():
        res.append({
            "requirement": field,
            "states": states
        })
    return res

@router.get("/quality")
def get_analytics_quality(
    days: int = Query(30, description="Date range in days"),
    db: Session = Depends(get_db)
):
    since_date = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    
    stats = db.query(
        ExtractedField.evidence_state,
        func.count(ExtractedField.id).label('count')
    ).filter(ExtractedField.created_at >= since_date)\
     .group_by(ExtractedField.evidence_state).all()
     
    return [{"state": s.evidence_state, "count": s.count} for s in stats]

@router.get("/consistency")
def get_analytics_consistency(
    days: int = Query(30, description="Date range in days"),
    db: Session = Depends(get_db)
):
    since_date = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    
    stats = db.query(
        ConsistencyCheck.check_type,
        ConsistencyCheck.status,
        func.count(ConsistencyCheck.id).label('count')
    ).filter(ConsistencyCheck.created_at >= since_date)\
     .group_by(ConsistencyCheck.check_type, ConsistencyCheck.status).all()
     
    res = []
    for check_type, status, count in stats:
        res.append({
            "check_type": check_type,
            "status": status,
            "count": count
        })
    return res

@router.get("/prioritization")
def get_analytics_prioritization(
    days: int = Query(30, description="Date range in days"),
    db: Session = Depends(get_db)
):
    since_date = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    
    stats = db.query(
        ProductCluster.priority_class,
        func.count(ProductCluster.id).label('count')
    ).filter(ProductCluster.created_at >= since_date)\
     .group_by(ProductCluster.priority_class).all()
     
    return [{"priority_class": s.priority_class or "UNKNOWN", "count": s.count} for s in stats]
