#!/usr/bin/env bash
# Build a GPU-enabled Qdrant binary optimized for the local Apple Silicon CPU.
#
# Usage:
#   apple/build-native.sh [--profile release|perf] [extra cargo args...]
#
# Requires: brew install cmake protobuf ninja (shaderc is built from source),
# and Xcode command line tools.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILE=release

if [[ "${1:-}" == "--profile" ]]; then
    PROFILE="$2"
    shift 2
fi

cd "$REPO_ROOT"

# target-cpu=native tunes codegen for this exact M-series core.
export RUSTFLAGS="-C target-cpu=native ${RUSTFLAGS:-}"

exec cargo build --profile "$PROFILE" --features gpu "$@"
