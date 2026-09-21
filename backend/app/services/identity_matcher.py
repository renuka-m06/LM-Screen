from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from backend.app.models.models import ProductCluster, Scan, CitizenReport

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
                return cluster
        
        # 4. No Match - Create New Cluster
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
        return cluster
