FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc-riscv64-unknown-elf binutils-riscv64-unknown-elf verilator \
    g++ make python3 python3-pyelftools openjdk-21-jdk-headless \
    curl ca-certificates git autoconf flex bison help2man libfl-dev && rm -rf /var/lib/apt/lists/*
RUN curl -fsSL https://github.com/sbt/sbt/releases/download/v1.10.0/sbt-1.10.0.tgz \
    | tar -xz -C /opt && ln -s /opt/sbt/bin/sbt /usr/local/bin/sbt
RUN git clone --depth 1 --branch v5.040 https://github.com/verilator/verilator.git /opt/verilator-src \
    && cd /opt/verilator-src && autoconf && ./configure && make -j4 && make install
