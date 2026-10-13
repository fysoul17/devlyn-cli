FROM python@sha256:2f17fc044b579bab302c2e8054d3a686e2cb9a83de48e70534b94cd8ebbe06a9
# The registered image .Id is the frozen input; apt and pip resolve once here, as in 0232.
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates xz-utils procps less \
 && rm -rf /var/lib/apt/lists/*
COPY node.tar.xz claude.tgz codex.tgz gh.tgz artifacts.sha256 /tmp/artifacts/
RUN cd /tmp/artifacts && sha256sum -c artifacts.sha256 \
 && tar -xJf node.tar.xz --strip-components=1 -C /usr/local \
 && mkdir claude codex gh \
 && tar -xzf claude.tgz -C claude && tar -xzf codex.tgz -C codex && tar -xzf gh.tgz -C gh \
 && cp claude/package/claude /usr/local/bin/claude \
 && mv codex/package/vendor/aarch64-unknown-linux-musl /opt/codex \
 && ln -s /opt/codex/bin/* /opt/codex/codex-path/rg /usr/local/bin/ \
 && cp gh/gh_2.83.2_linux_arm64/bin/gh /usr/local/bin/gh \
 && rm -rf /tmp/artifacts \
 && python -m pip install --no-cache-dir pytest==9.0.3 \
 && test "$(node --version)" = 'v22.23.2' \
 && claude --version | grep -Eq '^2\.1\.296([[:space:]]|$)' \
 && codex --version | grep -Eq '^codex-cli 0\.162\.1$' \
 && gh --version | grep -Eq '^gh version 2\.83\.2([[:space:]]|$)' \
 && test "$(python -m pytest --version)" = 'pytest 9.0.3'
ENV PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS="-p no:cacheprovider"
RUN useradd --uid 501 --create-home participant
USER 501:501
WORKDIR /work
