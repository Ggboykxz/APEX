# ============================================
# APEX v1.2.0 — Multi-stage Docker Image
# Universal AI coding agent. Every model. One terminal.
# ============================================

# ---- Stage 1: Python backend ----
FROM python:3.13-slim AS python-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md MANIFEST.in ./
COPY apex/ apex/

RUN pip install --no-cache-dir .

# ---- Stage 2: Bun + TUI frontend ----
FROM oven/bun:1 AS tui-builder

WORKDIR /app/tui-frontend

COPY tui-frontend/package.json tui-frontend/bun.lock ./
RUN bun install

COPY tui-frontend/ ./

# ---- Stage 3: Final image ----
FROM python:3.13-slim AS final

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl git ca-certificates unzip && \
    rm -rf /var/lib/apt/lists/*

# Install Bun for TUI
RUN curl -fsSL https://bun.sh/install | bash && \
    ln -s /root/.bun/bin/bun /usr/local/bin/bun

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy Python package from builder
COPY --from=python-base /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=python-base /usr/local/bin/apex /usr/local/bin/apex

# Copy APEX source (needed for runtime imports)
COPY apex/ apex/
COPY pyproject.toml README.md ./

# Copy TUI frontend
COPY --from=tui-builder /app/tui-frontend /app/tui-frontend

# Create workspace directory
RUN mkdir -p /workspace
WORKDIR /workspace

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD apex --version > /dev/null 2>&1 || exit 1

# Default: run APEX CLI
ENTRYPOINT ["apex"]
CMD ["--help"]
