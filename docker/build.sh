docker build \
    --build-arg CACHEBUST=$(date +%s) \
    --tag creepy .
