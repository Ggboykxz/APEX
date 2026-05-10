# ============================================
# APEX - Multi-stage Docker Image
# Universal AI coding agent. Every model. One terminal.
# ============================================

# ---- Stage 1: Python backend ----
FROM python:3.12-slim AS python-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY apex/ apex/

RUN pip install --no-cache-dir .

# ---- Stage 2: Bun + TUI frontend ----
FROM oven/bun:1 AS tui-builder

WORKDIR /app/tui-frontend

COPY tui-frontend/package.json tui-frontend/bun.lock ./
RUN bun install --frozen-lockfile

COPY tui-frontend/ ./

# ---- Stage 3: Final image ----
FROM python:3.12-slim AS final

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl git && \
    curl -fsSL https://bun.sh/install | bash && \
    rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.bun/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy Python package
COPY --from=python-base /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=python-base /usr/local/bin/apex /usr/local/bin/apex

# Copy APEX source
COPY apex/ apex/
COPY pyproject.toml README.md ./

# Copy TUI frontend
COPY --from=tui-builder /app/tui-frontend /app/tui-frontend

# Copy website
COPY src/ src/
COPY public/ public/
COPY package.json bun.lock next.config.ts tailwind.config.ts postcss.config.mjs tsconfig.json ./
COPY prisma/ prisma/

RUN bun install --frozen-lockfile

EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:3000 || exit 1

# Default: run APEX CLI
ENTRYPOINT ["apex"]
CMD ["--help"]
