FROM pytorch/pytorch:2.1.0-cuda11.8-cudnn8-runtime
WORKDIR /workspace/agent1_v2

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install --no-cache-dir \
    torch_geometric==2.5.0
RUN pip install --no-cache-dir \
    pyg_lib torch_scatter torch_sparse torch_cluster torch_spline_conv \
    -f https://data.pyg.org/whl/torch-2.1.0+cu118.html

COPY src/ ./src/

CMD ["/bin/bash"]
