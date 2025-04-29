FROM nvidia/cuda:12.2.0-devel-ubuntu20.04
ARG PYTHON_VERSION=3.12.9

ENV PATH=/opt/conda/bin:$PATH

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git && \
    rm -rf /var/lib/apt/lists/* && \
    curl -o ~/miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh && \
    apt-get remove -y curl && \
    chmod +x ~/miniconda.sh && \
    ~/miniconda.sh -b -p /opt/conda && \
    rm ~/miniconda.sh && \
    conda install -y python=$PYTHON_VERSION && \
    conda clean -ya && \
    pip install --quiet uvicorn && \
    mkdir /workspace

WORKDIR /workspace

COPY . creepy

RUN pip install --quiet -e ./creepy && \
    useradd -m creepy && \
    chown creepy . && \
    chmod 755 .

USER creepy

RUN mkdir ~/.ssh && \
    touch ~/.ssh/authorized_keys && \
    chmod 700 ~/.ssh && \
    chmod 600 ~/.ssh/authorized_keys

EXPOSE 8000

CMD ["creepy", "run", "--host", "0.0.0.0", "--log-level=info"]
