FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/jupyter && \
    chown -R 1000:1000 /home/jupyter

# GPU PyTorch — swap index URL for CPU-only:
# CPU: https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir \
    torch==2.6.0+cu124 \
    --index-url https://download.pytorch.org/whl/cu124

RUN pip install --no-cache-dir \
    transformers \
	safetensors \
    accelerate \
    pandas \
    numpy \
    scikit-learn \
    pyarrow \
    requests \
    sqlalchemy \
    psycopg2-binary \
    real_ladybug \
	jupyterlab \
	networkx \
	matplotlib \
	umap-learn \
	python-igraph \
	leidenalg

RUN pip install --no-cache-dir \
    pyg_lib \
    torch_scatter \
    torch_sparse \
    torch_cluster \
    torch_spline_conv \
    -f https://data.pyg.org/whl/torch-2.6.0+cu124.html

RUN pip install --no-cache-dir torch-geometric==2.6.1
RUN python -m ipykernel install --user
    
WORKDIR /app
