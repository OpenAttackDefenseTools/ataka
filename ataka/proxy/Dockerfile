FROM ubuntu:latest

RUN apt-get update && apt-get install -y \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# This should be the same UID and GID that owns the capot-env outside of the container
ARG UID=1000
ARG GID=1000

RUN apt-get update && apt-get install -y proxychains4
RUN apt-get update && apt-get install -y iproute2 ncat curl

RUN sed -i "s/^socks4\(.*\)9050/socks5\11080/g" /etc/proxychains4.conf

RUN mkdir -p /home/ubuntu/ssh-sockets/ \
 && chown -R ubuntu:ubuntu /home/ubuntu/ssh-sockets/

USER ubuntu:ubuntu

EXPOSE 1080/TCP

WORKDIR /home/ubuntu

#CMD ["sleep", "3000" ]
#CMD ["ssh", "server", "echo", "Connected", "&&", "sleep", "3"]
CMD ["ssh", "-N", "server"]
