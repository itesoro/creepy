docker build --tag creepy . && \
docker run -it \
    -p 8000:8000 \
    --mount type=bind,source=$(realpath ~/.ssh/authorized_keys),target=/root/.ssh/authorized_keys,readonly \
    --mount source=blobs,destination=/blobs \
    bash
    # creepy uvicorn creepy:app
