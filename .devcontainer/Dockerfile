FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

# Install basic dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set up workspace
WORKDIR /workspace

# The features in devcontainer.json will install:
# - Python 3.14
# - Node.js 22
# - Bun
# - uv
# - GitHub CLI
# - Azure CLI
