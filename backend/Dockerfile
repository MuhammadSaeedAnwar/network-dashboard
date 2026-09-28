# Backend: FastAPI app served by uvicorn.
FROM python:3.12-slim

# System dependencies for network diagnostics + nmap. tshark is optional
# and NOT installed by default (see ENABLE_PACKET_CAPTURE in .env.example) --
# add it here yourself if you want that optional feature, along with the
# container capabilities it needs (see README security section).
RUN apt-get update && apt-get install -y --no-install-recommends \
        iputils-ping \
        traceroute \
        nmap \
        curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 dashboard
WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
COPY tests ./tests

RUN pip install --no-cache-dir .
RUN pip install --no-cache-dir '.[dev]'

USER dashboard
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
