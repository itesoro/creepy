docker kill $(docker ps -q)
cp ~/.ssh/authorized_keys authorized_keys && \
    (docker build --tag creepy . ; rm authorized_keys) \
    docker run -d -p 8000:8000 creepy bash
