FROM owr-external-lab:local
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends qemu-system-x86 qemu-utils genisoimage && rm -rf /var/lib/apt/lists/*
