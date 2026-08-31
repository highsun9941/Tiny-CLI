FROM python:3.12-slim

WORKDIR /workspace

RUN useradd --create-home --uid 10001 tiny
COPY pyproject.toml README.md /tmp/
COPY tiny_cli /tmp/tiny_cli
RUN pip install --no-cache-dir /tmp && rm -rf /tmp/pyproject.toml /tmp/README.md /tmp/tiny_cli

USER tiny
ENTRYPOINT ["tiny"]
