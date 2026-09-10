import pytest
import numpy as np
from ai.quality import ImageQualityGate

def test_image_quality_acceptable():
    gate = ImageQualityGate()
    # Create synthetic sharp 500x500 RGB image with random noise
    img = np.random.randint(50, 200, (500, 500, 3), dtype=np.uint8)
    res = gate.assess_quality(img)
    assert res["resolution_ok"] is True
    assert res["status"] in ["ACCEPTABLE", "PARTIALLY_USABLE"]

def test_image_quality_low_resolution():
    gate = ImageQualityGate(min_width=400, min_height=400)
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    res = gate.assess_quality(img)
    assert res["status"] == "RETAKE_REQUIRED"
    assert res["resolution_ok"] is False
