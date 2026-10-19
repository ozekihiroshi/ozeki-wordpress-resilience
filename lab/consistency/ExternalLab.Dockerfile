ARG BASE_IMAGE
FROM ${BASE_IMAGE}
RUN apt-get update && apt-get install -y --no-install-recommends openssh-server openssh-client python3 \
    && rm -rf /var/lib/apt/lists/* /etc/ssh/ssh_host_* \
    && useradd -u 1000 -m -s /bin/sh owr-operator \
    && usermod -p '*' owr-operator \
    && usermod -a -G owr-operator www-data \
    && mkdir -p /run/sshd /run/owr-dispatch /queue \
    && chown www-data:owr-operator /run/owr-dispatch \
    && chmod 2750 /run/owr-dispatch \
    && chown owr-operator:owr-operator /queue
