import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from io import BytesIO
from PIL import Image, ImageDraw

client = TestClient(app)

def test_officer_review_authorization_failure():
    """Verify CITIZEN role cannot perform officer reviews (403 Forbidden)."""
    response = client.post(
        "/api/v1/officer/reviews",
        headers={"X-User-Role": "CITIZEN"},
        json={
            "scan_id": "non_existent_scan",
            "decision": "CONFIRM",
            "rationale": "Unauthorized review attempt"
        }
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Officer authorization required."

def test_officer_review_all_actions_and_audit_persistence():
    """
    NEEDS_REVIEW scan -> Investigate -> same scan_id -> same evidence -> officer action -> persisted status -> audit trail
    Tests all officer actions: CONFIRM, REJECT, MARK_UNDER_INVESTIGATION, REQUEST_MORE_EVIDENCE
    """
    # 1. Create a synthetic image for identity mismatch scan
    img = Image.new('RGB', (640, 640), color='#fff8f0')
    draw = ImageDraw.Draw(img)
    draw.rectangle([16, 16, 624, 624], outline='#e8c8a0', width=4)
    draw.text((45, 60), 'Premium Choco-Chip Biscuits', fill='#1a1a2e')
    draw.text((45, 130), 'Net Quantity: 250 g', fill='#1a1a2e')
    draw.text((45, 190), 'MRP: Rs. 150.00', fill='#1a1a2e')

    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)

    # 2. Upload scan with user product mismatch
    scan_resp = client.post(
        "/api/v1/scans",
        files={"file": ("mismatch_pkg.png", buf, "image/png")},
        data={"product_name": "PureHarvest Atta 5kg"}
    )
    assert scan_resp.status_code == 200
    scan_data = scan_resp.json()
    scan_id = scan_data["scan_id"]
    product_id = scan_data["product_id"]
    assert scan_data["status"] == "NEEDS_REVIEW"
    assert len(scan_data["identity_warnings"]) > 0

    # 3. Test Action 1: MARK_UNDER_INVESTIGATION
    res1 = client.post(
        "/api/v1/officer/reviews",
        headers={"X-User-Role": "OFFICER"},
        json={
            "scan_id": scan_id,
            "product_id": product_id,
            "decision": "MARK_UNDER_INVESTIGATION",
            "rationale": "Product identity conflicts with submitted product name."
        }
    )
    assert res1.status_code == 200
    d1 = res1.json()
    assert d1["previous_status"] == "NEEDS_REVIEW"
    assert d1["new_status"] == "MARK_UNDER_INVESTIGATION"
    assert d1["decision"] == "MARK_UNDER_INVESTIGATION"
    assert d1["officer"] == "Inspector R. K. Sharma"
    assert "timestamp" in d1

    # Simulate page refresh: verify persisted state via GET scan
    get_scan1 = client.get(f"/api/v1/scans/{scan_id}")
    assert get_scan1.status_code == 200
    assert get_scan1.json()["status"] == "MARK_UNDER_INVESTIGATION"

    # 4. Test Action 2: REQUEST_MORE_EVIDENCE
    res2 = client.post(
        "/api/v1/officer/reviews",
        headers={"X-User-Role": "OFFICER"},
        json={
            "scan_id": scan_id,
            "product_id": product_id,
            "decision": "REQUEST_MORE_EVIDENCE",
            "rationale": "Please upload a clearer image showing the complete product identity and declaration panel."
        }
    )
    assert res2.status_code == 200
    d2 = res2.json()
    assert d2["previous_status"] == "MARK_UNDER_INVESTIGATION"
    assert d2["new_status"] == "REQUEST_MORE_EVIDENCE"

    # 5. Test Action 3: CONFIRM
    res3 = client.post(
        "/api/v1/officer/reviews",
        headers={"X-User-Role": "OFFICER"},
        json={
            "scan_id": scan_id,
            "product_id": product_id,
            "decision": "CONFIRM",
            "rationale": "Non-compliance confirmed after officer physical inspection."
        }
    )
    assert res3.status_code == 200
    d3 = res3.json()
    assert d3["previous_status"] == "REQUEST_MORE_EVIDENCE"
    assert d3["new_status"] == "CONFIRM"

    # 6. Test Action 4: REJECT
    res4 = client.post(
        "/api/v1/officer/reviews",
        headers={"X-User-Role": "OFFICER"},
        json={
            "scan_id": scan_id,
            "product_id": product_id,
            "decision": "REJECT",
            "rationale": "Product verified compliant upon physical verification."
        }
    )
    assert res4.status_code == 200
    d4 = res4.json()
    assert d4["previous_status"] == "CONFIRM"
    assert d4["new_status"] == "REJECT"

    # 7. Simulate page refresh: verify product intelligence audit trail contains all 4 audit events
    if product_id:
        intel_res = client.get(f"/api/v1/products/{product_id}/intelligence")
        assert intel_res.status_code == 200
        intel_data = intel_res.json()
        audit_trail = intel_data["issue_clusters"][0]["audit_trail"]
        assert len(audit_trail) >= 4
        decisions = [a["decision"] for a in audit_trail]
        assert "MARK_UNDER_INVESTIGATION" in decisions
        assert "REQUEST_MORE_EVIDENCE" in decisions
        assert "CONFIRM" in decisions
        assert "REJECT" in decisions

def test_citizen_signal_submission_workflow():
    """Verify citizen signal submission links scan_id and stays UNVERIFIED."""
    response = client.post(
        "/api/v1/reports",
        json={
            "product_name": "Premium Choco-Chip Biscuits",
            "gtin": "8901234567890",
            "issue_category": "Information Mismatch",
            "description": "The submitted product name does not appear to match the product shown in the package image.",
            "location_city": "Mumbai",
            "scan_id": "demo_scan_123"
        }
    )
    assert response.status_code == 200
    res = response.json()
    assert res["status"] == "UNVERIFIED"
    assert "report_id" in res
    assert "signal for officer review" in res["message"]
