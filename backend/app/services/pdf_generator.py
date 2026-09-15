import os
import hashlib
import json
from io import BytesIO
from datetime import datetime
from sqlalchemy.orm import Session
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib import colors
from backend.app.models.models import Scan, RuleResult, ExtractedField
from backend.app.config import settings

def calculate_sha256(file_path: str) -> str:
    sha256_hash = hashlib.sha256()
    if not os.path.exists(file_path):
        return "File not found"
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def get_rule_details(rule_id: str) -> dict:
    profile_path = os.path.join(os.path.dirname(__file__), "../../../rules/profiles/2026.1/common.json")
    if os.path.exists(profile_path):
        with open(profile_path, "r") as f:
            data = json.load(f)
            for rule in data.get("rules", []):
                if rule.get("rule_id") == rule_id:
                    return rule
    # Check food profile
    food_path = os.path.join(os.path.dirname(__file__), "../../../rules/profiles/2026.1/food.json")
    if os.path.exists(food_path):
        with open(food_path, "r") as f:
            data = json.load(f)
            for rule in data.get("rules", []):
                if rule.get("rule_id") == rule_id:
                    return rule
    return {}

def draw_wrapped_text(c, text, x, y, max_width, line_height=14):
    """Draw text wrapped to max_width, returns the new y position."""
    words = text.split()
    line = ""
    for word in words:
        if c.stringWidth(line + word) < max_width:
            line += word + " "
        else:
            c.drawString(x, y, line.strip())
            y -= line_height
            line = word + " "
    if line:
        c.drawString(x, y, line.strip())
        y -= line_height
    return y

def generate_notice_pdf(scan_id: str, db: Session, inspector_name: str = "Officer Smith (ID: 942)") -> bytes:
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise ValueError(f"Scan with ID {scan_id} not found.")

    fields = db.query(ExtractedField).filter(ExtractedField.scan_id == scan_id).all()
    field_dict = {f.field_name: f.normalized_value for f in fields}

    product_name = field_dict.get("product_name", "Unknown Product")
    batch_number = field_dict.get("batch_number", "N/A")
    mfg = field_dict.get("manufacturer_or_packer", "Unknown Manufacturer")

    violations = db.query(RuleResult).filter(RuleResult.scan_id == scan_id, RuleResult.status == "POTENTIAL_NON_COMPLIANCE").all()

    image_path = os.path.join(settings.UPLOAD_DIR, os.path.basename(scan.image_path))
    image_hash = calculate_sha256(image_path)

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 1 * inch
    max_text_width = width - 2 * margin

    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, height - margin, "NOTICE UNDER SECTION 15")
    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin, height - 1.3 * inch, "LEGAL METROLOGY ACT, 2009")

    # Meta
    c.setFont("Helvetica", 10)
    c.drawString(margin, height - 1.8 * inch, f"Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    c.drawString(margin, height - 2.0 * inch, f"Notice Ref: {scan_id}")
    c.drawString(margin, height - 2.2 * inch, f"Issued by: {inspector_name}")

    # Product Details
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, height - 2.7 * inch, "1. Product Details")
    c.setFont("Helvetica", 10)
    c.drawString(margin + 0.2 * inch, height - 3.0 * inch, f"Product Name: {product_name}")
    c.drawString(margin + 0.2 * inch, height - 3.2 * inch, f"Manufacturer/Packer: {mfg}")
    c.drawString(margin + 0.2 * inch, height - 3.4 * inch, f"Batch Number: {batch_number}")

    # Violations
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, height - 3.9 * inch, "2. Details of Violation(s)")
    c.setFont("Helvetica", 10)
    
    y_pos = height - 4.2 * inch
    if not violations:
        c.drawString(margin + 0.2 * inch, y_pos, "No violations detected.")
        y_pos -= 0.3 * inch
    else:
        for v in violations:
            rule_info = get_rule_details(v.rule_id)
            legal_ref = rule_info.get("legal_reference", "Legal Metrology Rules")
            
            c.setFont("Helvetica-Bold", 10)
            y_pos = draw_wrapped_text(c, f"[{v.rule_id}] {v.rule_name}", margin + 0.2 * inch, y_pos, max_text_width - 0.2 * inch)
            
            c.setFont("Helvetica", 10)
            y_pos -= 4
            c.setFillColor(colors.darkblue)
            y_pos = draw_wrapped_text(c, f"Legal Ref: {legal_ref}", margin + 0.4 * inch, y_pos, max_text_width - 0.4 * inch)
            c.setFillColor(colors.black)
            y_pos -= 4
            y_pos = draw_wrapped_text(c, f"Reason for Flag: {v.reason}", margin + 0.4 * inch, y_pos, max_text_width - 0.4 * inch)
            
            y_pos -= 15
            if y_pos < margin:
                c.showPage()
                c.setFont("Helvetica", 10)
                y_pos = height - margin

    # Evidence
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y_pos - 0.2 * inch, "3. Digital Evidence Hash")
    c.setFont("Helvetica", 10)
    c.drawString(margin + 0.2 * inch, y_pos - 0.5 * inch, f"SHA-256 of Scan Image: {image_hash}")
    c.drawString(margin + 0.2 * inch, y_pos - 0.7 * inch, "This digital hash secures the original photograph submitted as evidence.")

    c.save()
    buffer.seek(0)
    return buffer.getvalue()
