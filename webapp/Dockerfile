# Code and Test Crew - Web Application Dockerfile
# Build from project root: docker build -f webapp/Dockerfile -t code-crew-webapp .

FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install ALL requirements (web includes langchain-ollama)
COPY requirements.txt .
COPY webapp/requirements-web.txt .
RUN pip install --no-cache-dir -r requirements.txt -r requirements-web.txt

# Copy application code
COPY agents/ ./agents/
COPY utils/ ./utils/
COPY webapp/ ./webapp/

# Create outputs directory
RUN mkdir -p /app/outputs

WORKDIR /app/webapp

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 5001

ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV OLLAMA_URL=http://ollama:11434

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5001/ || exit 1

CMD ["python", "app.py", "--port", "5001"]
