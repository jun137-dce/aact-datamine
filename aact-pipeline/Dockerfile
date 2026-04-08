FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# install deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy ALL pipeline code
COPY . /app

# ensure output dir exists
RUN mkdir -p /app/output

CMD ["python", "run_aact_pipeline.py"]