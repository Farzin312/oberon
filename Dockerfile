# Oberon CPU runtime — lightweight, no torch.
# Built with uv for reproducible dependency resolution.
FROM python:3.12-slim AS builder

# Install uv (pinned for reproducibility).
COPY --from=ghcr.io/astral-sh/uv:0.6.6 /uv /usr/local/bin/uv

WORKDIR /app

# Copy lock + manifest first for layer caching.
COPY pyproject.toml uv.lock ./

# Install production deps only (no dev, no ai extras).
RUN uv sync --frozen --no-dev --no-install-project

# Copy source, readme, and install project so console script is available.
COPY src/ src/
COPY README.md ./
RUN uv sync --frozen --no-dev --no-editable

# ---- Runtime stage ----
FROM python:3.12-slim AS runtime

# Install system libraries needed by rasterio/GDAL.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libexpat1 libgdal36 libgeos-c1t64 libspatialindex-c8 libpq5 && \
    rm -rf /var/lib/apt/lists/*

# Copy the virtualenv from builder.
COPY --from=builder /app/.venv /app/.venv

WORKDIR /app

# Put venv on PATH.
ENV PATH="/app/.venv/bin:$PATH"
ENV OBERON_CACHE_DIR=/root/.cache/oberon

# Entry point.
ENTRYPOINT ["oberon"]
CMD ["--help"]
