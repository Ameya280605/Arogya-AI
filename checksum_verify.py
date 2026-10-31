import hashlib
import json
from pathlib import Path

artifacts = Path("ml/tabular/artifacts")
joblib_path = artifacts / "tabular_baseline.joblib"
meta_path = artifacts / "model_metadata.json"

# Compute actual SHA-256 of the artifact
sha256 = hashlib.sha256()
with open(joblib_path, "rb") as f:
    while chunk := f.read(65536):
        sha256.update(chunk)
actual_hash = sha256.hexdigest()

# Read expected hash from metadata
with open(meta_path, "r", encoding="utf-8") as f:
    meta = json.load(f)
expected_hash = meta.get("sha256_checksum", "")

print(f"Artifact: {joblib_path}")
print(f"Size: {joblib_path.stat().st_size} bytes")
print(f"Actual SHA-256:   {actual_hash}")
print(f"Expected SHA-256: {expected_hash}")
print(f"Checksum match: {actual_hash.lower() == expected_hash.lower()}")

# Verify key metadata fields
print("\n--- Metadata Validation ---")
required_keys = ["model_name", "model_version", "model_family", "features", "classes",
                 "disclaimer", "sha256_checksum", "evaluation_metrics"]
for key in required_keys:
    present = key in meta
    print(f"  {key}: {'OK' if present else 'MISSING'}")

# Verify disclaimer
disc = meta.get("disclaimer", "")
print(f"\nDisclaimer contains 'RESEARCH PROTOTYPE ONLY': {'RESEARCH PROTOTYPE ONLY' in disc}")
print(f"\nmodel_name: {meta.get('model_name')}")
print(f"model_version: {meta.get('model_version')}")
print(f"features: {meta.get('features')}")
print(f"classes: {meta.get('classes')}")
print(f"cv_macro_f1_mean: {meta.get('evaluation_metrics', {}).get('cv_macro_f1_mean')}")

