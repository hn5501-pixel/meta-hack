FROM python:3.11-slim

# HuggingFace Spaces requires port 7860
EXPOSE 7860

WORKDIR /app

# Install dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY main.py inference.py openenv.yaml ./
COPY server/ ./server/

# Non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:7860/health').raise_for_status()"

ENV PORT=7860
ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
