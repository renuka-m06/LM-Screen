from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from backend.app.models.models import ProductCluster, Scan, CitizenReport
from backend.app.services.prioritization import EvidencePrioritizationEngine

class IdentityMatcher:
    def __init__(self, db: Session):
        self.db = db

    def process_scan(self, scan_id: str) -> ProductCluster:
        """
        Process a scan to find or create its deterministic identity cluster.
        Updates the scan's cluster_id and returns the cluster.
        """
        scan = self.db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            return None

        # Gather extracted fields to determine identity
        extracted = {f.field_name: f.normalized_value or f.raw_text for f in scan.extracted_fields if f.found}
        
        gtin = extracted.get("gtin")
        brand = extracted.get("brand_name")
        product_name = extracted.get("product_name")
        variant = extracted.get("variant")
        net_quantity = extracted.get("net_quantity")

        # Fallback to product identity if available
        if not gtin and scan.product and scan.product.gtin:
            gtin = scan.product.gtin
        if not brand and scan.product and scan.product.brand_name:
            brand = scan.product.brand_name
        if not product_name and scan.product and scan.product.product_name:
            product_name = scan.product.product_name

        # 1. Exact Image Duplicate Check (deduplication)
        # Assuming another scan with same image_hash exists
        duplicate_scan = self.db.query(Scan).filter(
            Scan.image_hash == scan.image_hash, 
            Scan.id != scan.id
        ).first()

        if duplicate_scan and duplicate_scan.cluster_id:
            scan.duplicate_of_scan_id = duplicate_scan.id
            scan.cluster_id = duplicate_scan.cluster_id
            self.db.commit()
            
            # Update report counts
            cluster = self.db.query(ProductCluster).filter(ProductCluster.id == scan.cluster_id).first()
            if cluster:
                cluster.report_count += 1
                self.db.commit()
                self.recalculate_priority(cluster)
                return cluster

        # 2. Strong GTIN Match
        if gtin:
            cluster = self.db.query(ProductCluster).filter(ProductCluster.gtin == gtin).first()
            if cluster:
                scan.cluster_id = cluster.id
                cluster.report_count += 1
                if not cluster.match_method or cluster.match_method == "INITIAL":
                    cluster.match_method = "GTIN_MATCH"
                    cluster.match_strength = "STRONG_MATCH"
                self.db.commit()
                self.recalculate_priority(cluster)
                return cluster
        
        # 3. Deterministic Identity Match (Brand + Product Name)
        if brand and product_name:
            # Look for a cluster with same brand and product
            query = self.db.query(ProductCluster).filter(
                ProductCluster.brand == brand,
                ProductCluster.product_name == product_name
            )
            if variant:
                query = query.filter(ProductCluster.variant == variant)
            else:
                query = query.filter(or_(ProductCluster.variant.is_(None), ProductCluster.variant == ""))
                
            if net_quantity:
                query = query.filter(ProductCluster.net_quantity == net_quantity)
            else:
                query = query.filter(or_(ProductCluster.net_quantity.is_(None), ProductCluster.net_quantity == ""))
                
            cluster = query.first()
            if cluster:
                scan.cluster_id = cluster.id
                cluster.report_count += 1
                if not cluster.match_method or cluster.match_method == "INITIAL":
                    cluster.match_method = "BRAND_PRODUCT_MATCH"
                    cluster.match_strength = "POSSIBLE_MATCH"
                self.db.commit()
                self.recalculate_priority(cluster)
                return cluster
        
        # 4. Optional ML Product Matcher Extension Point
        ml_match_id = self._ml_product_matcher(scan, gtin, brand, product_name)
        if ml_match_id:
            cluster = self.db.query(ProductCluster).filter(ProductCluster.id == ml_match_id).first()
            if cluster:
                scan.cluster_id = cluster.id
                cluster.report_count += 1
                if not cluster.match_method or cluster.match_method == "INITIAL":
                    cluster.match_method = "ML_PRODUCT_MATCHER"
                    cluster.match_strength = "POSSIBLE_MATCH"
                self.db.commit()
                self.recalculate_priority(cluster)
                return cluster
        
        # 5. No Match - Create New Cluster
        cluster = ProductCluster(
            product_id=scan.product_id,
            gtin=gtin,
            brand=brand,
            product_name=product_name,
            variant=variant,
            net_quantity=net_quantity,
            match_method="INITIAL",
            match_strength="NO_MATCH",
            report_count=1,
            ai_flag_count=0 if scan.status == "PASS_SCREENING" else 1,
            status="REVIEW_REQUIRED" if scan.status != "PASS_SCREENING" else "UNVERIFIED"
        )
        self.db.add(cluster)
        self.db.commit()
        self.db.refresh(cluster)

        scan.cluster_id = cluster.id
        self.db.commit()
        
        # Recalculate Prioritization
        self.recalculate_priority(cluster)
        
        return cluster

    def _ml_product_matcher(self, scan, gtin, brand, product_name) -> str:
        """
        Extension point for future ML-assisted product matching.
        Does not fake similarity scores. Currently deterministic matching is authoritative.
        """
        # Future implementation might use embeddings, visual features, OCR identity, etc.
        return None

    def recalculate_priority(self, cluster: ProductCluster):
        engine = EvidencePrioritizationEngine()
        
        scans = self.db.query(Scan).filter(Scan.cluster_id == cluster.id).all()
        # Ensure relationships are loaded for scans to avoid detached instances or N+1 issues
        # Actually, evaluate_cluster just needs scan.quality_status, decision_traces
        
        reports = self.db.query(CitizenReport).filter(CitizenReport.scan_id.in_([s.id for s in scans]) | (CitizenReport.product_id == cluster.product_id)).all()
        
        from backend.app.models.models import RuleResult, ConsistencyCheck, ExtractedField
        
        rule_results = []
        consistency_checks = []
        evidence = []
        for s in scans:
            rule_results.extend(self.db.query(RuleResult).filter(RuleResult.scan_id == s.id).all())
            consistency_checks.extend(self.db.query(ConsistencyCheck).filter(ConsistencyCheck.scan_id == s.id).all())
            evidence.extend(self.db.query(ExtractedField).filter(ExtractedField.scan_id == s.id).all())
            
        result = engine.evaluate_cluster(cluster, scans, reports, rule_results, consistency_checks, evidence)
        
        cluster.priority_class = result["priority_class"]
        cluster.priority_reasons = result["priority_reasons"]
        cluster.evidence_strength = result["evidence_strength"]
        cluster.actionability_state = result["actionability_state"]
        cluster.prioritization_version = result["prioritization_version"]
        
        # Keep legacy score for compatibility during transition if needed
        score_map = {"PRIORITY_REVIEW": 0.9, "STANDARD_REVIEW": 0.5, "EVIDENCE_INSUFFICIENT": 0.1}
        cluster.priority_score = score_map.get(result["priority_class"], 0.5)
        
        self.db.commit()

