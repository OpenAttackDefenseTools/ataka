FROM ubuntu:latest

RUN apt-get -y update

RUN apt-get install -y curl

WORKDIR /exploit

COPY . .

CMD [ "bash", "exploit.sh" ]
