# 容器路径的 GPU 访问采用 Podman + krunkit（Venus），放弃 Docker Desktop 与 apple/container

在 macOS 上所有容器都运行于 Linux 虚拟机内，Apple 的 Hypervisor/Virtualization 框架不向 guest 暴露 GPU，因此 Docker Desktop 与 apple/container 均无法让容器使用 Apple GPU（后者的 `--gpu` PR #1314 只是 MLX 推理 RPC 代理，对需要容器内真实 Vulkan 设备的 Qdrant 无效，且已被官方拒收）。唯一可行路径是 Podman machine + krunkit（libkrun provider）：容器内使用 Mesa Venus Vulkan 驱动，经 virtio-gpu 将 Vulkan 调用转发至宿主 MoltenVK/Metal，性能约为原生的 75-80%。通过 podman 的 docker 兼容 socket 保留 docker CLI / docker compose 工作流。

## Considered Options

- Docker Desktop：无 GPU 透传，排除。
- apple/container：同样受 Virtualization.framework 限制，官方明确无 GPU 方案，排除。
- Podman + krunkit + Venus：唯一可行，采用。代价：容器侧目前需要 patched Mesa（Fedora 42 + copr `slp/mesa-libkrun-vulkan`，实测 25.2.3-101 可用；Fedora 44 的 stock Mesa 26.1.3 存在 venus 回归，vkCreateInstance 直接失败）。

## Consequences

- 镜像必须是 linux/arm64 且内置 Venus 能力的 Mesa Vulkan 驱动（基于 Fedora + copr），与上游 nvidia/amd GPU 镜像结构不同。
- 用户必须以 `CONTAINERS_MACHINE_PROVIDER=libkrun` 初始化 podman machine，容器运行需带 `--device /dev/dri`。
- jemalloc 需按 16K 页（`JEMALLOC_SYS_WITH_LG_PAGE=14`）编译以兼容 libkrun guest 内核。
