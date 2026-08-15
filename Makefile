.PHONY: hydradb-up hydradb-stop hydradb-health hydradb-smoke hydradb-reset test-hydradb dataset-info dataset-download dataset-sample dataset-inventory dataset-quality embedding-experiment extract-mentions extract-claims eval-extraction mention-inventory build-ground-truth test-phase2b

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

extract-mentions:
	python scripts/extract_mentions.py

extract-claims:
	python scripts/extract_claims.py

eval-extraction:
	python scripts/eval_extraction.py

mention-inventory:
	python scripts/mention_inventory.py

build-ground-truth:
	python scripts/build_ground_truth.py

test-phase2b:
	python -m pytest tests/phase2b/ -q

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

