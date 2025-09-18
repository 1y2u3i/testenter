# /********************************************************************************
# * Copyright (c) 2022 Contributors to the Eclipse Foundation
# *
# * See the NOTICE file(s) distributed with this work for additional
# * information regarding copyright ownership.
# *
# * This program and the accompanying materials are made available under the
# * terms of the Apache License 2.0 which is available at
# * http://www.apache.org/licenses/LICENSE-2.0
# *
# * SPDX-License-Identifier: Apache-2.0
# ********************************************************************************/

# Build stage
FROM --platform=$BUILDPLATFORM ubuntu:22.04 AS builder
ENV DEBIAN_FRONTEND="noninteractive"

RUN DEBIAN_FRONTEND=noninteractive apt-get update -y && \
    apt-get install -y git \
    cmake g++ build-essential g++-aarch64-linux-gnu \
    libjsoncpp-dev binutils-aarch64-linux-gnu jq python3 python3-pip 

RUN pip3 install conan==1.55.0

COPY . /src
WORKDIR /src

ARG TARGETPLATFORM
RUN echo "Building for ${TARGETPLATFORM}"

RUN if [ "$TARGETPLATFORM" = "linux/amd64" ]; then \
        ./build-release.sh amd64; \
    elif [ "$TARGETPLATFORM" = "linux/arm64" ]; then \
        ./build-release.sh aarch64; \
    else \
        echo "Unsupported platform: $TARGETPLATFORM"; exit 1; \
    fi
# Use final just for staticx to build based on target platform
FROM --platform=$TARGETPLATFORM ubuntu:22.04 AS final
ARG TARGETARCH
RUN DEBIAN_FRONTEND=noninteractive apt-get update -y && \
    apt-get install -y python3 python3-pip
# Remove this installation for Arm64 once staticx has a prebuilt wheel for Arm64
RUN /bin/bash -c 'set -ex && \
    ARCH=`uname -m` && \
    if [ "$ARCH" == "aarch64" ]; then \
    echo "ARM64" && \
    apt-get install -y gcc && \
    pip3 install --no-cache-dir scons; \
    fi'
    
RUN pip3 install --no-cache-dir patchelf==0.17.0.0
RUN pip3 install staticx

WORKDIR "/target/config"
WORKDIR "/target/bin"
COPY --from=builder /src/target/*/release/install/bin/someip_feeder/ /target/bin/someip_feeder
COPY --from=builder /src/target/*/release/install/bin/execute-apps-docker.sh /target/bin/execute-apps-docker.sh
COPY --from=builder /src/target/*/release/install/lib/* /lib/
COPY --from=builder /src/target/*/release/install/bin/config /target/config/


RUN staticx /target/bin/someip_feeder /target/bin/someip-exe

# use busybox in scratch image for runnign shell script and for debugging
FROM busybox:uclibc AS busybox
# Final scratch image for target
FROM scratch

COPY --from=final /target/bin/someip-exe /app/someip-exe
COPY --from=final /target/bin/execute-apps-docker.sh /app/execute-apps-docker.sh
COPY --from=builder /src/target/*/release/install/bin/config /config
COPY --from=builder /src/target/*/release/install/lib /lib
COPY --from=busybox /bin/busybox /bin/busybox
COPY --from=busybox /bin/sh /bin/sh
RUN /bin/busybox ln -s /bin/busybox /bin/ls
RUN /bin/busybox ln -s /bin/busybox /bin/cat
RUN /bin/busybox ln -s /bin/busybox /bin/tail
RUN /bin/busybox ln -s /bin/busybox /bin/sleep
RUN /bin/busybox ln -s /bin/busybox /bin/basename
WORKDIR /tmp
WORKDIR /lib
WORKDIR /app

ENV PATH="/target/bin/:$PATH"
ENV LD_LIBRARY_PATH="$LD_LIBRARY_PATH:/lib/"
ENTRYPOINT ["/bin/sh", "./execute-apps-docker.sh"]
