#!/usr/bin/env bash
# One-time setup of a GPU-capable podman machine (libkrun/krunkit) on macOS.
#
# Requires: brew install podman && brew tap slp/krun && brew install krunkit
#
# Usage:
#   apple/setup-podman-machine.sh [--cpus N] [--memory MB] [--disk-size GB]
#
# After this script completes, docker CLI / docker compose can talk to podman:
#   export DOCKER_HOST=$(podman machine inspect --format 'unix://{{.ConnectionInfo.PodmanSocket.Path}}')

set -euo pipefail

# Note: running qdrant needs ~8-12GB; building the image inside the VM with
# the release profile (fat LTO, codegen-units=1) needs 24GB+ or the linker
# gets OOM-killed.
CPUS=8
MEMORY=16384
DISK=60

while [[ $# -gt 0 ]]; do
    case "$1" in
        --cpus) CPUS="$2"; shift 2 ;;
        --memory) MEMORY="$2"; shift 2 ;;
        --disk-size) DISK="$2"; shift 2 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

# libkrun is the only provider that forwards the Apple GPU (virtio-gpu Venus).
export CONTAINERS_MACHINE_PROVIDER=libkrun

if ! command -v krunkit >/dev/null; then
    echo "krunkit not found. Install it with: brew tap slp/krun && brew install krunkit" >&2
    exit 1
fi

if podman machine inspect >/dev/null 2>&1; then
    echo "podman machine already exists (provider: libkrun assumed); starting it."
else
    podman machine init --cpus "$CPUS" --memory "$MEMORY" --disk-size "$DISK"
fi

podman machine start 2>/dev/null || echo "machine already running"

echo
echo "Verifying GPU forwarding inside the VM..."
podman machine ssh "ls /dev/dri/renderD128 >/dev/null && echo 'OK: /dev/dri/renderD128 present (virtio-gpu active)'"

echo
echo "To use docker CLI / docker compose against this machine:"
echo "  export CONTAINERS_MACHINE_PROVIDER=libkrun"
echo "  export DOCKER_HOST=\"unix://\$(podman machine inspect --format '{{.ConnectionInfo.PodmanSocket.Path}}')\""
