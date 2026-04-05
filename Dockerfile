FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04

ARG PYTHON_VERSION=3.11
ARG TGNN_EXTRAS=gui,dev
ARG INSTALL_BASELINES=0

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PATH="/opt/venv/bin:${PATH}"

SHELL ["/bin/bash", "-lc"]

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        software-properties-common \
        git \
        wget \
        curl \
        ca-certificates \
        build-essential \
        bash \
        libglib2.0-0 \
        libxext6 \
        libsm6 \
        libxrender1 \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        python${PYTHON_VERSION} \
        python${PYTHON_VERSION}-venv \
        python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN python${PYTHON_VERSION} -m venv /opt/venv

WORKDIR /app
COPY . /app

RUN python -m pip install --upgrade pip setuptools wheel
RUN pip install torch==2.4.0 --index-url https://download.pytorch.org/whl/cu121
RUN pip install torch-geometric -f https://data.pyg.org/whl/torch-2.4.0+cu121.html
RUN if [[ -n "${TGNN_EXTRAS}" ]]; then \
        pip install -e ".[${TGNN_EXTRAS}]"; \
    else \
        pip install -e .; \
    fi
RUN if [[ "${INSTALL_BASELINES}" == "1" ]]; then \
        pip install -e ".[baselines]"; \
    fi
RUN pip install mkdocs mkdocs-material pymdown-extensions

EXPOSE 8501 8000

ENTRYPOINT ["python"]
CMD ["scripts/training/train.py", "--help"]
