FROM python@sha256:2f17fc044b579bab302c2e8054d3a686e2cb9a83de48e70534b94cd8ebbe06a9
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates xz-utils procps less && rm -rf /var/lib/apt/lists/*
COPY node-v22.23.2-linux-arm64.tar.xz /tmp/node.tar.xz
RUN tar -xJf /tmp/node.tar.xz --strip-components=1 -C /usr/local && rm /tmp/node.tar.xz
COPY codex/package/vendor/aarch64-unknown-linux-musl /opt/codex
COPY claude/package/claude /usr/local/bin/claude
# Login shells reset PATH (/etc/profile), so the CLIs live on the default PATH.
RUN ln -s /opt/codex/bin/* /opt/codex/codex-path/rg /usr/local/bin/ \
 && python -m pip install --no-cache-dir pytest==9.0.3 && codex --version && claude --version && node --version
# Read-only evaluator mounts and owner scope both need pytest to write no cache.
ENV PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS="-p no:cacheprovider"
RUN useradd --uid 501 --create-home participant
USER 501:501
WORKDIR /work
