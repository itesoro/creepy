DOCKER_IMAGE=creepy

if which nvidia-smi >> /dev/null; then
    DOCKER_ARGS="--gpus all"
else
    DOCKER_ARGS=
fi

try_bind () {
    local p=$(realpath $1)
    if [ -f "$p" ]; then
        DOCKER_ARGS="$DOCKER_ARGS --mount type=bind,source=$p,target=$2,readonly"
    fi
}

try_bind ~/.ssh/authorized_keys /root/.ssh/authorized_keys
try_bind ~/.ssh/id_rsa.pub /root/.ssh/id_rsa.pub

docker run -it \
    -p 8000:8000 \
    $DOCKER_ARGS \
    --mount source=blobs,destination=/blobs \
    $DOCKER_IMAGE
