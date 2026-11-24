FROM debian:trixie-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates debian-archive-keyring debootstrap grub-common live-build \
        file mount python3 rsync sqv squashfs-tools xorriso xz-utils \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
