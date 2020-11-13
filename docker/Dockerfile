FROM nvidia/cuda:10.1-cudnn7-devel-ubuntu18.04
ARG PYTHON_VERSION=3.8

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && \
    rm -rf /var/lib/apt/lists/*

ENV PATH=/opt/conda/bin:$PATH

RUN curl -o ~/miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh && \
    apt-get remove -y curl && \
    chmod +x ~/miniconda.sh && \
    ~/miniconda.sh -b -p /opt/conda && \
    rm ~/miniconda.sh && \
    conda install -y python=$PYTHON_VERSION pytorch torchvision cudatoolkit=10.2 -c pytorch && \
    conda clean -ya && \
    pip install uvicorn

RUN mkdir ~/.ssh && \
    touch ~/.ssh/authorized_keys && \
    chmod 700 ~/.ssh && \
    chmod 600 ~/.ssh/authorized_keys

EXPOSE 8000

RUN echo "uvicorn creepy:app --host 0.0.0.0 --log-level=warning" >> /root/start.sh && \
    chmod +x /root/start.sh

ARG CACHEBUST="Build with option --build-arg CACHEBUST=$(date +%s) to prevent caching the lines below."

ARG CREEPY_BRANCH=master

WORKDIR /root

RUN git clone --depth 1 -b $CREEPY_BRANCH https://github.com/itesoro/creepy.git && \
    pip install -e ./creepy
