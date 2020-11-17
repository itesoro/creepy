DOCKER_IMAGE=creepy

if which nvidia-smi >> /dev/null; then
    DOCKER_ARGS="--gpus all"
else
    DOCKER_ARGS=
fi

docker run -it \
    -p 8000:8000 \
    $DOCKER_ARGS \
    --mount type=bind,source=$(realpath ~/.ssh/authorized_keys),target=/root/.ssh/authorized_keys,readonly \
    --mount source=blobs,destination=/blobs \
    $DOCKER_IMAGE bash
