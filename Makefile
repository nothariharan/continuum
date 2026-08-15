.PHONY: hydradb-up hydradb-stop hydradb-health hydradb-smoke hydradb-reset test-hydradb dataset-info dataset-download dataset-sample dataset-inventory dataset-quality embedding-experiment claims-load claims-benchmark test-phase2b

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

embedding-experiment:
	python scripts/embedding_experiment.py
claims-load:
	python scripts/load_phase2b_claims.py --reset

claims-benchmark:
	python scripts/benchmark_phase2b.py

test-phase2b:
	python -m pytest tests/phase2b -m hydradb -q
hydradb-up:
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

