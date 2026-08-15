.PHONY: hydradb-up hydradb-stop hydradb-health hydradb-smoke hydradb-reset test-hydradb dataset-info dataset-download dataset-sample dataset-inventory dataset-quality dataset-load-hydradb embedding-experiment extract-mentions extract-claims extract-dataset validate-extraction eval-extraction mention-inventory build-ground-truth test-phase2b test-phase2b-integration claims-load claims-benchmark checkpoint-claims real-claims-load real-claims-benchmark

dataset-info:
	python scripts/dataset_info.py

dataset-download:
	python scripts/dataset_download.py

dataset-sample:
	python scripts/dataset_sample.py

dataset-inventory:
	python scripts/dataset_inventory.py

dataset-quality:
	python scripts/dataset_quality.py

dataset-load-hydradb:
	python scripts/dataset_load_hydradb.py --reset

embedding-experiment:
	python scripts/embedding_experiment.py

extract-mentions:
	python scripts/extract_mentions.py

extract-claims:
	python scripts/extract_claims.py

extract-dataset:
	PYTHONUNBUFFERED=1 python scripts/extract_mentions.py --method hybrid
	PYTHONUNBUFFERED=1 python scripts/extract_claims.py --method hybrid --workers 5 --checkpoint data/extraction/claims.checkpoint.jsonl
	python scripts/slice_claims_checkpoint.py
	python scripts/validate_extraction.py

validate-extraction:
	python scripts/validate_extraction.py

eval-extraction:
	python scripts/validate_extraction.py
	python scripts/eval_extraction.py

mention-inventory:
	python scripts/mention_inventory.py

build-ground-truth:
	python scripts/build_ground_truth.py

test-phase2b:
	python -m pytest tests/phase2b/ -q

claims-load:
	python scripts/load_phase2b_claims.py --reset

claims-benchmark:
	python scripts/benchmark_phase2b.py

checkpoint-claims:
	python scripts/checkpoint_claims.py

real-claims-load:
	python scripts/load_phase2b_claims.py --reset --claims data/fixtures/phase2b_real_claims.jsonl --resolutions data/fixtures/phase2b/resolutions-real.json

real-claims-benchmark:
	python scripts/benchmark_phase2b.py --real

test-phase2b-integration:
	python -m pytest tests/phase2b -m hydradb -q


	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start_hydradb.ps1
hydradb-stop:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/stop_hydradb.ps1
hydradb-health:
	python -m continuum.hydradb.health
hydradb-smoke:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/smoke_test.ps1
hydradb-reset:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/reset_hydradb.ps1
test-hydradb:
	python -m pytest -m hydradb -q

