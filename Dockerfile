FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends software-properties-common git wget \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y --no-install-recommends python3.11 python3.11-venv python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN python3.11 -m venv /opt/venv

ENV PATH="/opt/venv/bin:${PATH}"
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src/ src/
COPY scripts/ scripts/
COPY configs/ configs/

RUN python -m pip install --upgrade pip setuptools wheel
RUN pip install torch==2.4.0 --index-url https://download.pytorch.org/whl/cu121
RUN pip install torch-geometric -f https://data.pyg.org/whl/torch-2.4.0+cu121.html
RUN pip install -e .

ENTRYPOINT ["python"]
CMD ["scripts/train.py", "--help"]
