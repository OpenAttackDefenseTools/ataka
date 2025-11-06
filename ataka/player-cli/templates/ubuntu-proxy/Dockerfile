FROM ubuntu:latest

RUN apt-get -y update

RUN apt-get install -y curl ncat
RUN apt-get install -y proxychains4
RUN sed -i "s/socks4.*9050/socks5 172.22.1.2 1080/g" /etc/proxychains4.conf

WORKDIR /exploit

COPY . .

CMD [ "bash", "exploit.sh" ]
