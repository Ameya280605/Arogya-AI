"""Structural analysis of all Module 9 Phase 5 implementation files."""
import ast
import os
from pathlib import Path

ROOT = Path(".")

files_to_inspect = [
    "backend/app/api/analysis.py",
    "backend/app/services/tabular_ml.py",
    "backend/app/schemas/analysis.py",
    "backend/app/api/__init__.py",
    "backend/app/main.py",
    "backend/tests/test_tabular_api.py",
    "tests/unit/test_tabular_dataset.py",
    "tests/unit/test_tabular_artifacts.py",
    "tests/unit/test_tabular_predictor.py",
    "tests/unit/test_tabular_training.py",
    "ml/tabular/src/__init__.py",
    "ml/tabular/src/dataset.py",
    "ml/tabular/src/predictor.py",
    "ml/tabular/src/train.py",
    "ml/tabular/src/evaluate.py",
    "ml/model_cards/tabular_exasens_baseline.md",
    "ml/tabular/artifacts/model_metadata.json",
    "ml/tabular/artifacts/experiment_summary.md",
]

print("=== Module 9 File Existence Check ===\n")
all_exist = True
for rel_path in files_to_inspect:
    p = ROOT / rel_path
    exists = p.exists()
    size = p.stat().st_size if exists else 0
    print(f"  {'OK  ' if exists else 'MISS'} {rel_path} ({size} bytes)" if exists else f"  MISS {rel_path}")
    if not exists:
        all_exist = False

artifact_path = ROOT / "ml/tabular/artifacts/tabular_baseline.joblib"
print(f"\n  {'OK  ' if artifact_path.exists() else 'MISS'} ml/tabular/artifacts/tabular_baseline.joblib ({artifact_path.stat().st_size if artifact_path.exists() else 0} bytes)")

print(f"\nAll files present: {all_exist and artifact_path.exists()}")

# Inspect analysis.py for endpoint registration
print("\n=== API Endpoint Analysis ===")
with open("backend/app/api/analysis.py", "r") as f:
    content = f.read()
    
endpoints = [line.strip() for line in content.split('\n') if '@router.' in line]
for ep in endpoints:
    print(f"  {ep}")

# Check that analysis router is registered in main.py
with open("backend/app/main.py", "r") as f:
    main_content = f.read()

print("\n=== Router Registration in main.py ===")
if "analysis_router" in main_content:
    print("  OK: analysis_router included in main.py")
else:
    print("  MISS: analysis_router NOT found in main.py")

# Inspect services __init__
with open("backend/app/services/__init__.py", "r") as f:
    svc_init = f.read()
print("\n=== services/__init__.py ===")
print(svc_init[:500])

# Inspect schemas/__init__.py
with open("backend/app/schemas/__init__.py", "r") as f:
    sch_init = f.read()
print("\n=== schemas/__init__.py snippet ===")
if "TabularInferenceRequest" in sch_init:
    print("  OK: TabularInferenceRequest exported in schemas/__init__.py")
else:
    print("  WARN: TabularInferenceRequest not found in schemas/__init__.py")

