FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY lumina_orderbook_mcp ./lumina_orderbook_mcp

RUN pip install --no-cache-dir .

ENTRYPOINT ["lumina-orderbook-mcp"]
