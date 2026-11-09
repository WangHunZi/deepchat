ARG BASE_IMAGE
FROM ${BASE_IMAGE}

ARG RECIPE
LABEL org.opencontainers.image.source="https://github.com/WangHunZi/deepchat" \
      org.opencontainers.image.title="DeepChat development toolchain" \
      org.opencontainers.image.licenses="MIT" \
      io.deepchat.recipe="${RECIPE}"

WORKDIR /opt/deepchat
COPY tools/native.py tools/sdk-lock.json tools/requirements-host.txt tools/requirements-idf.txt tools/idf-constraints.txt ./tools/
# A session CA is mounted only while downloading; it must not remain in image layers.
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then \
        export SSL_CERT_FILE=/run/secrets/proxy_ca \
            REQUESTS_CA_BUNDLE=/run/secrets/proxy_ca \
            PIP_CERT=/run/secrets/proxy_ca \
            GIT_SSL_CAINFO=/run/secrets/proxy_ca; \
    fi; \
    python3 tools/native.py --jobs 4 setup && \
    rm -rf /root/.cache /opt/deepchat/.sdk/tools/dist && \
    git config --system --add safe.directory /opt/deepchat/.sdk/esp-idf

ENV DC_TOOL_ROOT=/opt/deepchat \
    DC_BUILD_ROOT=/workspace/build/container \
    PATH=/opt/deepchat/.venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    HOME=/tmp
WORKDIR /workspace
