docker kill $(docker ps -q)
cp ~/.ssh/authorized_keys authorized_keys

docker build --tag creepy . && docker run -it -p 8000:8000 creepy bash

rm authorized_keys