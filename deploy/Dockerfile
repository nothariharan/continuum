# Continuum backend runtime — Query API (FastAPI/uvicorn) over HydraDB.
# Build context is the repo root:  docker build -f deploy/Dockerfile -t continuum-api .
FROM python:3.12-slim

WORKDIR /app

# Install the package + delivery deps (fastapi, uvicorn, slack-bolt, pydantic, mcp, neo4j).
COPY pyproject.toml ./
COPY continuum ./continuum
RUN pip install --no-cache-dir ".[delivery]"

# Runtime bits used by the server entrypoints.
COPY scripts ./scripts

ENV PYTHONPATH=/app \
    HYDRADB_HOST=hydradb \
    PORT=8080

EXPOSE 8080

# Bind to 0.0.0.0 so the container is reachable.
CMD ["python", "scripts/run_query_api.py", "--host", "0.0.0.0", "--port", "8080"]
