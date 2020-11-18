BRANCH_NAME=$(git rev-parse --abbrev-ref HEAD)

docker build \
    --build-arg CREEPY_BRANCH=$BRANCH_NAME \
    --build-arg CACHEBUST=$(date +%s) \
    --tag creepy .
