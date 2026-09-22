FROM python@sha256:2f17fc044b579bab302c2e8054d3a686e2cb9a83de48e70534b94cd8ebbe06a9
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates xz-utils procps && rm -rf /var/lib/apt/lists/*
COPY node-v22.23.2-linux-arm64.tar.xz /tmp/node.tar.xz
RUN tar -xJf /tmp/node.tar.xz --strip-components=1 -C /usr/local && rm /tmp/node.tar.xz
COPY codex/package/vendor/aarch64-unknown-linux-musl /opt/codex
COPY claude/package/claude /usr/local/bin/claude
ENV PATH="/opt/codex/bin:/opt/codex/codex-path:${PATH}" PYTHONDONTWRITEBYTECODE=1
RUN python -m pip install --no-cache-dir pytest==9.0.3 && codex --version && claude --version && node --version
RUN useradd --uid 501 --create-home participant
USER 501:501
WORKDIR /work
