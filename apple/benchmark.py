#!/usr/bin/env python3
"""HNSW index-build benchmark: CPU vs Apple GPU (native) vs Apple GPU (container).

Matrix (default): sizes {100K, 1M} x dims {768, 1536} x engines
{cpu, gpu-native, gpu-container} x precision {f32, f16 (GPU only)}.

For every run the same seeded dataset is uploaded with indexing deferred,
then indexing is enabled and the time until the collection turns green is
measured. Index quality is checked as recall@10 of HNSW search against exact
search on 100 held-out queries.

Usage:
  python3 apple/benchmark.py --quick                 # 10K x 768, all engines
  python3 apple/benchmark.py                         # full matrix
  python3 apple/benchmark.py --engines cpu,gpu-native --sizes 100000 --dims 768

Requires: pip install -r apple/requirements.txt (qdrant-client, numpy),
a binary built via apple/build-native.sh, and for gpu-container the image
built from apple/Dockerfile.gpu-apple on a libkrun podman machine.
"""

import argparse
import itertools
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
from qdrant_client import QdrantClient, models

REPO_ROOT = Path(__file__).resolve().parent.parent
COLLECTION = "bench"
BATCH = 1024
QUERIES = 100
TOP_K = 10
DEFER_INDEXING_KB = 10**9  # effectively "never index"


def log(msg: str) -> None:
    print(f"[bench] {msg}", flush=True)


class Server:
    """Starts/stops a qdrant server (native process or podman container)."""

    def __init__(self, engine: str, half_precision: bool, container_image: str):
        self.engine = engine
        self.half = half_precision
        self.image = container_image
        self.proc = None
        self.container_id = None
        self.tmpdir = None

    def start(self) -> None:
        if self.engine == "gpu-container":
            self._start_container()
        else:
            self._start_native()
        self._wait_ready()

    def _gpu_env(self) -> dict:
        return {
            "QDRANT__GPU__INDEXING": "true" if self.engine.startswith("gpu") else "false",
            "QDRANT__GPU__FORCE_HALF_PRECISION": "true" if self.half else "false",
            "QDRANT__LOG_LEVEL": "INFO",
        }

    def _start_native(self) -> None:
        self.tmpdir = tempfile.mkdtemp(prefix=f"qdrant-bench-{self.engine}-")
        env = os.environ.copy()
        env.update(self._gpu_env())
        logfile = open(Path(self.tmpdir) / "qdrant.log", "w")
        self.proc = subprocess.Popen(
            [str(REPO_ROOT / "apple" / "run-native.sh")],
            cwd=self.tmpdir,
            env=env,
            stdout=logfile,
            stderr=subprocess.STDOUT,
        )

    def _start_container(self) -> None:
        env_flags = []
        for key, value in self._gpu_env().items():
            env_flags += ["-e", f"{key}={value}"]
        result = subprocess.run(
            ["podman", "run", "-d", "--rm", "--device", "/dev/dri",
             "-p", "6333:6333", "-p", "6334:6334", *env_flags, self.image],
            check=True, capture_output=True, text=True,
        )
        self.container_id = result.stdout.strip()

    def _wait_ready(self, timeout: float = 120.0) -> None:
        import urllib.request
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                with urllib.request.urlopen("http://localhost:6333/readyz", timeout=2) as r:
                    if r.status == 200:
                        return
            except Exception:
                time.sleep(0.5)
        raise RuntimeError(f"server ({self.engine}) did not become ready")

    def gpu_device_initialized(self) -> bool:
        if self.engine == "gpu-container":
            out = subprocess.run(["podman", "logs", self.container_id],
                                 capture_output=True, text=True).stdout
        else:
            out = (Path(self.tmpdir) / "qdrant.log").read_text()
        return "Initialized GPU device" in out

    def stop(self) -> None:
        if self.container_id:
            subprocess.run(["podman", "rm", "-f", self.container_id],
                           capture_output=True, check=False)
            self.container_id = None
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            self.proc = None
        if self.tmpdir:
            shutil.rmtree(self.tmpdir, ignore_errors=True)
            self.tmpdir = None


def dataset_batches(size: int, dim: int):
    """Deterministic dataset, generated in batches to bound memory."""
    rng = np.random.default_rng(42)
    for start in range(0, size, BATCH):
        n = min(BATCH, size - start)
        yield start, rng.random((n, dim), dtype=np.float32)


def query_vectors(dim: int) -> np.ndarray:
    return np.random.default_rng(7).random((QUERIES, dim), dtype=np.float32)


def run_one(engine: str, size: int, dim: int, half: bool, image: str) -> dict:
    label = f"{engine}/{'f16' if half else 'f32'} size={size} dim={dim}"
    log(f"=== {label} ===")
    server = Server(engine, half, image)
    server.start()
    client = QdrantClient(host="localhost", port=6333, grpc_port=6334,
                          prefer_grpc=True, timeout=600)
    try:
        client.delete_collection(COLLECTION)
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE),
            hnsw_config=models.HnswConfigDiff(m=16, ef_construct=128),
            optimizers_config=models.OptimizersConfigDiff(
                default_segment_number=1,
                max_segment_size=32_000_000,  # KB; keep everything in one segment
                indexing_threshold=DEFER_INDEXING_KB,
            ),
        )

        t0 = time.time()
        for start, batch in dataset_batches(size, dim):
            client.upsert(
                COLLECTION,
                points=models.Batch(ids=list(range(start, start + len(batch))),
                                    vectors=batch.tolist()),
                wait=False,
            )
        # flush: wait until all points are visible
        while client.count(COLLECTION, exact=True).count < size:
            time.sleep(0.5)
        upload_s = time.time() - t0
        log(f"upload done in {upload_s:.1f}s")

        # enable indexing and measure build time
        t0 = time.time()
        client.update_collection(
            COLLECTION,
            optimizers_config=models.OptimizersConfigDiff(indexing_threshold=10),
        )
        last_report = 0.0
        while True:
            info = client.get_collection(COLLECTION)
            if (info.status == models.CollectionStatus.GREEN
                    and (info.indexed_vectors_count or 0) >= size * 0.95):
                break
            if time.time() - last_report > 15:
                log(f"  indexing... status={info.status} "
                    f"indexed={info.indexed_vectors_count}/{size}")
                last_report = time.time()
            time.sleep(1)
        index_s = time.time() - t0
        log(f"index build took {index_s:.1f}s")

        # recall@10 against exact search
        queries = query_vectors(dim)
        hits = 0
        for q in queries:
            exact = client.query_points(
                COLLECTION, query=q.tolist(), limit=TOP_K,
                search_params=models.SearchParams(exact=True),
            ).points
            approx = client.query_points(
                COLLECTION, query=q.tolist(), limit=TOP_K,
                search_params=models.SearchParams(hnsw_ef=128),
            ).points
            exact_ids = {p.id for p in exact}
            hits += sum(1 for p in approx if p.id in exact_ids)
        recall = hits / (QUERIES * TOP_K)
        log(f"recall@{TOP_K} = {recall:.4f}")

        gpu_used = server.gpu_device_initialized() if engine.startswith("gpu") else False
        if engine.startswith("gpu") and not gpu_used:
            log("WARNING: GPU engine requested but no GPU device was initialized!")

        return {"engine": engine, "precision": "f16" if half else "f32",
                "size": size, "dim": dim, "upload_s": round(upload_s, 1),
                "index_s": round(index_s, 1), "recall": round(recall, 4),
                "gpu_used": gpu_used}
    finally:
        server.stop()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", default="100000,1000000")
    parser.add_argument("--dims", default="768,1536")
    parser.add_argument("--engines", default="cpu,gpu-native,gpu-container")
    parser.add_argument("--container-image", default="qdrant-gpu-apple")
    parser.add_argument("--quick", action="store_true",
                        help="single 10K x 768 run per engine")
    parser.add_argument("--output", default=str(REPO_ROOT / "apple" / "BENCHMARK.md"))
    args = parser.parse_args()

    sizes = [10_000] if args.quick else [int(s) for s in args.sizes.split(",")]
    dims = [768] if args.quick else [int(d) for d in args.dims.split(",")]
    engines = args.engines.split(",")

    results = []
    for size, dim, engine in itertools.product(sizes, dims, engines):
        precisions = [False] if engine == "cpu" else [False, True]
        if args.quick:
            precisions = [False]
        for half in precisions:
            try:
                results.append(run_one(engine, size, dim, half, args.container_image))
            except Exception as exc:
                log(f"FAILED {engine} size={size} dim={dim} half={half}: {exc}")
                results.append({"engine": engine, "precision": "f16" if half else "f32",
                                "size": size, "dim": dim, "upload_s": None,
                                "index_s": None, "recall": None, "gpu_used": None,
                                "error": str(exc)[:120]})

    lines = [
        "# Apple Silicon GPU benchmark",
        "",
        f"Machine: {subprocess.run(['sysctl', '-n', 'machdep.cpu.brand_string'], capture_output=True, text=True).stdout.strip()}",
        f"Date: {time.strftime('%Y-%m-%d %H:%M')}",
        "",
        "| size | dim | engine | precision | upload (s) | index build (s) | recall@10 | gpu used |",
        "|---:|---:|---|---|---:|---:|---:|---|",
    ]
    for r in results:
        lines.append(
            f"| {r['size']} | {r['dim']} | {r['engine']} | {r['precision']} "
            f"| {r['upload_s']} | {r['index_s']} | {r['recall']} | {r.get('gpu_used')} |")
    report = "\n".join(lines) + "\n"
    Path(args.output).write_text(report)
    print("\n" + report)
    log(f"report written to {args.output}")


if __name__ == "__main__":
    main()
