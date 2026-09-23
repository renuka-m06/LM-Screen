"""
download_ocr_models.py
─────────────────────
Downloads EasyOCR model weight files (craft_mlt_25k.pth + english_g2.pth)
to ~/.EasyOCR/model/ WITHOUT initializing the PyTorch Reader.

Used during Docker image build to pre-cache model files so the container
does not need network access at runtime.

Memory profile:
  easyocr.Reader(['en'], ...) : ~505 MB  (NOT used here)
  This script             :  <50 MB  (stdlib only: urllib, zipfile)
"""
import os
import sys
import urllib.request
import zipfile
import tempfile

MODEL_DIR = os.path.join(os.path.expanduser("~"), ".EasyOCR", "model")

# EasyOCR 1.7.x model files for English-only pipeline:
#   craft_mlt_25k.pth  -- text detection (CRAFT), 79 MB
#   english_g2.pth     -- English recognition,    14 MB
# Source: easyocr/config.py in the installed package
MODELS = [
    {
        "filename": "craft_mlt_25k.pth",
        "zip_name": "craft_mlt_25k.zip",
        "url": "https://github.com/JaidedAI/EasyOCR/releases/download/pre-v1.1.6/craft_mlt_25k.zip",
        "size_mb": 79,
    },
    {
        "filename": "english_g2.pth",
        "zip_name": "english_g2.zip",
        "url": "https://github.com/JaidedAI/EasyOCR/releases/download/v1.3/english_g2.zip",
        "size_mb": 14,
    },
]


def download_model(model):
    target = os.path.join(MODEL_DIR, model["filename"])
    if os.path.exists(target):
        size_mb = os.path.getsize(target) / 1024 / 1024
        print("[OK] Already cached: %s (%.1f MB)" % (model["filename"], size_mb))
        return True

    print("[...] Downloading %s (~%d MB)..." % (model["filename"], model["size_mb"]))
    try:
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp_path = tmp.name

        urllib.request.urlretrieve(model["url"], tmp_path)

        with zipfile.ZipFile(tmp_path, "r") as z:
            names = z.namelist()
            print("    Zip contents: %s" % names)
            for name in names:
                if name.endswith(".pth"):
                    z.extract(name, MODEL_DIR)
                    # If zip puts it in a subdirectory, move it up
                    extracted = os.path.join(MODEL_DIR, name)
                    if extracted != target and os.path.exists(extracted):
                        os.rename(extracted, target)
                    break

        os.unlink(tmp_path)

        if os.path.exists(target):
            size_mb = os.path.getsize(target) / 1024 / 1024
            print("[OK] Downloaded: %s (%.1f MB)" % (model["filename"], size_mb))
            return True
        else:
            print("[ERR] Downloaded zip but .pth not found at: %s" % target)
            return False

    except Exception as e:
        print("[ERR] Failed to download %s: %s" % (model["filename"], e))
        return False


def main():
    os.makedirs(MODEL_DIR, exist_ok=True)
    print("[download_ocr_models] Target directory: %s" % MODEL_DIR)

    failed = []
    for model in MODELS:
        ok = download_model(model)
        if not ok:
            failed.append(model["filename"])

    if failed:
        print("\n[download_ocr_models] WARNING: Failed to download: %s" % failed)
        print("[download_ocr_models] EasyOCR will attempt download at runtime.")
        sys.exit(0)  # Non-fatal: runtime fallback exists (download_enabled=True)
    else:
        print("\n[download_ocr_models] All %d model files ready." % len(MODELS))
        sys.exit(0)


if __name__ == "__main__":
    main()
