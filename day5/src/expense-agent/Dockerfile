FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first (layer caching)
COPY pyproject.toml .
RUN uv sync --frozen --no-dev

# Copy application code
COPY app/ ./app/

ENV PORT=8080
EXPOSE 8080

CMD ["uv", "run", "uvicorn", "app.agent_runtime_app:fast_api_app", \
     "--host", "0.0.0.0", "--port", "8080"]
