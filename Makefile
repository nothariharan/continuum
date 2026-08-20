.PHONY: hydradb-up hydradb-stop hydradb-health hydradb-smoke hydradb-reset test-hydradb dataset-info dataset-download dataset-sample dataset-inventory dataset-quality dataset-load-hydradb embedding-experiment extract-mentions extract-claims extract-dataset validate-extraction eval-extraction mention-inventory build-ground-truth test-phase2b test-phase2b-integration claims-load claims-benchmark checkpoint-claims real-claims-e2e eval-real-claims eval-synthetic-claims identity-pairs identity-pairs-v1 test-identity-data query-shapes real-claims-load real-claims-benchmark gold-v1 enrich-gold-claims eval-run test-eval eval-entity-resolution calibrate-entity-resolution entity-integration benchmark-e2e build-benchmark-v1 benchmark-foundation benchmark-foundation-official benchmark-foundation-live benchmark-trace test-benchmark
.PHONY: hydradb-up hydradb-stop hydradb-health hydradb-smoke hydradb-reset test-hydradb dataset-info dataset-download dataset-sample dataset-inventory dataset-quality dataset-load-hydradb embedding-experiment extract-mentions extract-claims extract-dataset validate-extraction eval-extraction mention-inventory build-ground-truth test-phase2b test-phase2b-integration claims-load claims-benchmark checkpoint-claims real-claims-e2e eval-real-claims eval-synthetic-claims identity-pairs identity-pairs-v1 test-identity-data query-shapes real-claims-load real-claims-benchmark gold-v1 enrich-gold-claims eval-run test-eval eval-entity-resolution benchmark-e2e
.PHONY: hydradb-up hydradb-stop hydradb-health hydradb-smoke hydradb-reset test-hydradb dataset-info dataset-download dataset-sample dataset-inventory dataset-quality dataset-load-hydradb embedding-experiment extract-mentions extract-claims extract-dataset validate-extraction eval-extraction mention-inventory build-ground-truth test-phase2b test-phase2b-integration claims-load claims-benchmark checkpoint-claims real-claims-e2e eval-real-claims eval-synthetic-claims identity-pairs query-shapes real-claims-load real-claims-benchmark gold-v1 enrich-gold-claims eval-run test-eval eval-entity-resolution calibrate-entity-resolution entity-integration benchmark-e2e benchmark-continuum-sample benchmark-trace

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

real-claims-e2e:
	python scripts/real_claims_e2e.py

eval-real-claims:
	python scripts/eval_real_claims.py --fixture real

eval-synthetic-claims:
	python scripts/eval_real_claims.py --fixture synthetic

identity-pairs:
	python scripts/build_identity_pairs.py

identity-pairs-v1:
	python scripts/build_identity_pairs_v1.py
	python scripts/generate_identity_features.py
	python scripts/eval_identity_pairs.py

test-identity-data:
	python -m pytest tests/eval/test_identity_pairs_v1.py -q

query-shapes:
	python scripts/measure_query_shapes.py

real-claims-load:
	python scripts/load_phase2b_claims.py --reset --claims data/fixtures/phase2b_real_claims.jsonl --resolutions data/fixtures/phase2b/resolutions-real.json

real-claims-benchmark:
	python scripts/benchmark_phase2b.py --real

test-phase2b-integration:
	python -m pytest tests/phase2b -m hydradb -q

gold-v1:
	python scripts/build_gold_benchmark_v1.py

enrich-gold-claims:
	python scripts/enrich_gold_claims_v1.py

RUN ?= 001
STRATEGY ?= deterministic

eval-run:
	python scripts/run_extraction_eval.py --run $(RUN) --strategy $(STRATEGY)

test-eval:
	python -m pytest tests/eval -q

DATA ?= data/fixtures/phase3/identity-pairs-tiny.jsonl

eval-entity-resolution:
	python scripts/eval_entity_resolution.py --pairs $(DATA)

calibrate-entity-resolution:
	python scripts/calibrate_entity_resolution.py --pairs $(DATA)

entity-integration:
	python scripts/entity_resolution_integration.py --reset

benchmark-e2e:
	python scripts/benchmark_e2e_questions.py

build-benchmark-v1:
	PYTHONPATH=. python scripts/build_benchmark_v1.py --mode all
benchmark-continuum-sample:
	python scripts/benchmark_continuum_sample.py

benchmark-trace:
	PYTHONPATH=. python scripts/benchmark_trace.py $(QUESTION)

benchmark-full-v1-verify:
	PYTHONPATH=. python scripts/verify_benchmark_corpus.py

benchmark-full-v1-smoke:
	PYTHONPATH=. python scripts/build_benchmark_v1.py --mode full-v1
	PYTHONPATH=. python scripts/run_full_v1_baseline.py --run-id full-v1-smoke-001 --regression --answer-model real --with-graph --fail-on-fallback

benchmark-full-v1-baseline:
	PYTHONPATH=. python scripts/run_full_v1_baseline.py --run-id full-v1-baseline-001 --system bm25 --answer-model real --with-graph --fail-on-fallback
	PYTHONPATH=. python scripts/run_full_v1_baseline.py --run-id full-v1-baseline-001 --system dense --answer-model real --with-graph --fail-on-fallback
	PYTHONPATH=. python scripts/run_full_v1_baseline.py --run-id full-v1-baseline-001 --system hybrid --answer-model real --with-graph --fail-on-fallback
	PYTHONPATH=. python scripts/run_full_v1_baseline.py --run-id full-v1-baseline-001 --system continuum --answer-model real --with-graph --fail-on-fallback

analyze-full-v1-baseline:
	PYTHONPATH=. python scripts/analyze_full_v1_baseline.py --run-id full-v1-baseline-001

benchmark-full-v1-resume-bm25:
	PYTHONPATH=. python scripts/run_full_v1_baseline.py --run-id full-v1-baseline-001 --system bm25 --answer-model real --no-graph --fail-on-fallback

benchmark-foundation:
	PYTHONPATH=. python scripts/build_benchmark_v1.py --mode sample-v1
	PYTHONPATH=. python scripts/run_benchmark_foundation.py --mode sample-v1 --answer-model mock

benchmark-foundation-official:
	PYTHONPATH=. python scripts/build_benchmark_v1.py --mode full-v1
	PYTHONPATH=. python scripts/run_benchmark_foundation.py --mode full-v1 --answer-model real

benchmark-foundation-live:
	PYTHONPATH=. python scripts/run_benchmark_foundation.py --mode sample-v1 --answer-model real --with-graph

QUESTION ?= qst_0001
benchmark-trace:
	PYTHONPATH=. python scripts/run_benchmark_foundation.py --mode sample-v1 --trace $(QUESTION) --answer-model mock

test-benchmark:
	PYTHONPATH=. python -m pytest tests/eval/test_benchmark_*.py -q

ifeq ($(OS),Windows_NT)
  HYDRADB_START = powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start_hydradb.ps1
  HYDRADB_STOP = powershell -NoProfile -ExecutionPolicy Bypass -File scripts/stop_hydradb.ps1
  HYDRADB_RESET = powershell -NoProfile -ExecutionPolicy Bypass -File scripts/reset_hydradb.ps1
  HYDRADB_SMOKE = powershell -NoProfile -ExecutionPolicy Bypass -File scripts/smoke_test.ps1
else
  HYDRADB_START = bash scripts/start_hydradb.sh
  HYDRADB_STOP = bash scripts/stop_hydradb.sh
  HYDRADB_RESET = bash scripts/reset_hydradb.sh
  HYDRADB_SMOKE = bash scripts/smoke_test.sh
endif

hydradb-up:
	$(HYDRADB_START)
hydradb-stop:
	$(HYDRADB_STOP)
hydradb-health:
	python -m continuum.hydradb.health
hydradb-smoke:
	$(HYDRADB_SMOKE)
hydradb-reset:
	$(HYDRADB_RESET)
test-hydradb:
	python -m pytest -m hydradb -q

ingest-slack-fixtures:
	python3 scripts/ingest_slack.py --mode fixtures

ingest-gmail-fixtures:
	python3 scripts/ingest_gmail.py --mode fixtures

build-source-e2e-gold:
	PYTHONPATH=. python3 scripts/build_source_e2e_gold.py

source-e2e:
	PYTHONPATH=. python3 scripts/source_to_answer_e2e.py --refinement mock

source-e2e-fireworks-smoke:
	PYTHONPATH=. python3 scripts/source_to_answer_e2e.py --refinement fireworks --fireworks-answer --fireworks-budget 20

test-sources:
	python3 -m pytest tests/sources/ -q

expand-identity-gold:
	python3 scripts/expand_identity_pairs_gold.py

test-delivery:
	python3 -m pytest tests/delivery/ -q

PYTHON ?= $(shell test -x .venv312/bin/python && echo .venv312/bin/python || echo python3)

install-delivery:
	uv pip install --python $(PYTHON) -e ".[delivery]"

run-query-api:
	PYTHONPATH=. $(PYTHON) scripts/run_query_api.py

run-slack-bot:
	PYTHONPATH=. python3 scripts/run_slack_bot.py

run-slack-events:
	PYTHONPATH=. python3 scripts/run_slack_events_gateway.py

run-memory-worker:
	PYTHONPATH=. python3 scripts/run_memory_worker.py --mode fixtures

slack-demo-sync:
	PYTHONPATH=. python3 scripts/slack_demo_initial_sync.py --mode fixtures

ingest-source:
	python3 scripts/ingest_source.py --source $(SOURCE) --mode $(MODE)

post-stabilization-health:
	PYTHONPATH=. python3 scripts/post_stabilization_health_check.py

web-clean:
	rm -rf web/.next

web-dev:
	cd web && npm run dev

web-build:
	cd web && npm run build

web-install:
	cd web && npm install
