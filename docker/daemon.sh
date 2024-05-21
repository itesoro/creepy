DOCKER_IMAGE=creepy
CREEPY_HOME=/home/creepy

gpu_available() {
    # Check if nvidia-smi command exists
    if command -v nvidia-smi >> /dev/null; then
        # Run nvidia-smi and capture the output
        output=$(nvidia-smi 2>&1)

        # Check if the specific error message is in the output
        if echo "$output" | grep -q "NVIDIA-SMI has failed because it couldn't communicate with the NVIDIA driver. Make sure that the latest NVIDIA driver is installed and running."; then
            return 1  # GPU is not available
        else
            return 0  # GPU is available
        fi
    else
        return 1  # GPU is not available
    fi
}

if gpu_available; then
    DOCKER_ARGS="--gpus all"
else
    DOCKER_ARGS=
fi

DOCKER_ARGS="$DOCKER_ARGS -e MKL_THREADING_LAYER=GNU"

try_bind () {
    local p=$(realpath $1)
    if [ -f "$p" ]; then
        DOCKER_ARGS="$DOCKER_ARGS --mount type=bind,source=$p,target=$2,readonly"
    fi
}

try_bind ~/.ssh/authorized_keys $CREEPY_HOME/.ssh/authorized_keys
try_bind ~/.ssh/id_rsa.pub $CREEPY_HOME/.ssh/id_rsa.pub

docker run -d \
    --restart always \
    -p ${1:-8000}:8000 \
    $DOCKER_ARGS \
    --mount source=blobs,destination=/blobs \
    $DOCKER_IMAGE
