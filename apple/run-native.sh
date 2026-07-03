#!/usr/bin/env bash
# Run a GPU-enabled Qdrant binary natively on macOS (Apple Silicon).
#
# The binary is built with `cargo build --release --features gpu` and talks to
# the Apple GPU through the Vulkan loader + MoltenVK ICD (Vulkan -> Metal).
# Both come from Homebrew: `brew install vulkan-loader molten-vk`.
#
# Usage:
#   apple/run-native.sh [extra qdrant args...]
#
# Environment overrides:
#   QDRANT_BIN    path to the qdrant binary (default: target/release/qdrant)
#   QDRANT_CONFIG config file (default: config/config-apple.yaml)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BREW_PREFIX="$(brew --prefix 2>/dev/null || echo /opt/homebrew)"

QDRANT_BIN="${QDRANT_BIN:-$REPO_ROOT/target/release/qdrant}"
QDRANT_CONFIG="${QDRANT_CONFIG:-$REPO_ROOT/config/config-apple.yaml}"

if [[ ! -x "$QDRANT_BIN" ]]; then
    echo "qdrant binary not found at $QDRANT_BIN" >&2
    echo "Build it with: cargo build --release --features gpu" >&2
    exit 1
fi

MOLTENVK_ICD="$BREW_PREFIX/etc/vulkan/icd.d/MoltenVK_icd.json"
if [[ ! -f "$MOLTENVK_ICD" ]]; then
    echo "MoltenVK ICD not found at $MOLTENVK_ICD" >&2
    echo "Install it with: brew install molten-vk vulkan-loader" >&2
    exit 1
fi

# ash loads libvulkan.dylib at runtime; Homebrew's lib dir is not in the
# default dyld search path, and the loader needs the ICD manifest to find
# MoltenVK.
export DYLD_FALLBACK_LIBRARY_PATH="$BREW_PREFIX/lib${DYLD_FALLBACK_LIBRARY_PATH:+:$DYLD_FALLBACK_LIBRARY_PATH}"
export VK_ICD_FILENAMES="${VK_ICD_FILENAMES:-$MOLTENVK_ICD}"

exec "$QDRANT_BIN" --config-path "$QDRANT_CONFIG" "$@"
