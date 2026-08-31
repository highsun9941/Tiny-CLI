FROM python:3.12-slim

WORKDIR /workspace

RUN useradd --create-home --uid 10001 tiny
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

COPY tiny_cli.py /usr/local/bin/tiny-cli
RUN chmod +x /usr/local/bin/tiny-cli

USER tiny
ENTRYPOINT ["tiny-cli"]
