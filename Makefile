.PHONY: hydradb-up hydradb-stop hydradb-health hydradb-smoke hydradb-reset test-hydradb
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

