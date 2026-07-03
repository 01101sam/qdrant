# Qdrant on Apple Silicon GPU

本 fork 的目标：让 Qdrant 在 Apple Silicon（M3 Max）上用上 GPU 加速，自用为主、专为 Apple GPU 优化，不追随上游官方路线。

## Language

**GPU 索引加速（GPU Indexing）**:
Qdrant 中 GPU 的唯一用途——加速 HNSW 索引构建阶段（最高 ~10x）；搜索/查询始终由 CPU 执行。
_Avoid_: GPU 推理、GPU 查询加速、GPU 搜索

**原生路径（Native Path）**:
直接运行在 macOS 上的 Qdrant 二进制，通过 MoltenVK 把 Vulkan 转译为 Metal 使用 Apple GPU，性能 100%。

**容器路径（Container Path）**:
运行在 Linux 容器（linux/arm64 镜像）内的 Qdrant，容器内是 Mesa Venus Vulkan 驱动，经 virtio-gpu 把 Vulkan 调用转发到宿主 Apple GPU，性能约为原生的 75-80%。
_Avoid_: "Docker Desktop GPU"、"apple/container GPU"（两者均无此能力，已验证排除）

**容器底座（Container Runtime）**:
Podman machine + krunkit（libkrun provider），是容器路径的唯一运行时；通过 podman 的 docker 兼容 socket 保留 docker CLI / docker compose 用法。
_Avoid_: Docker Desktop、apple/container、colima（未验证）
