FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# GPU PyTorch — swap index URL for CPU-only:
# CPU: https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir \
    torch \
    --index-url https://download.pytorch.org/whl/cu121

RUN pip install --no-cache-dir \
    transformers \
    pandas \
    numpy \
    scikit-learn \
    pyarrow \
    requests \
    sqlalchemy \
    psycopg2-binary \
    real_ladybug \
	kuzu

WORKDIR /app
