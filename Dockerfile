FROM python:3.12-slim

WORKDIR /workspace

RUN useradd --create-home --uid 10001 tiny
RUN apt-get update && apt-get install -y --no-install-recommends git ripgrep \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /tmp/
COPY tiny_cli /tmp/tiny_cli
RUN pip install --no-cache-dir /tmp

USER tiny
ENTRYPOINT ["tiny"]
