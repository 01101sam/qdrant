# Apple Silicon GPU benchmark

Machine: Apple M3 Max
Date: 2026-07-04 04:14

| size | dim | engine | precision | upload (s) | index build (s) | recall@10 | gpu used |
|---:|---:|---|---|---:|---:|---:|---|
| 100000 | 768 | cpu | f32 | 4.2 | 19.1 | 0.392 | False |
| 100000 | 768 | gpu-native | f32 | 4.1 | 7.1 | 0.367 | True |
| 100000 | 768 | gpu-native | f16 | 4.0 | 5.0 | 0.379 | True |
| 100000 | 768 | gpu-container | f32 | 6.1 | 7.0 | 0.376 | True |
| 100000 | 768 | gpu-container | f16 | 5.9 | 5.0 | 0.379 | True |
| 100000 | 1536 | cpu | f32 | 7.9 | 42.3 | 0.376 | False |
| 100000 | 1536 | gpu-native | f32 | 7.4 | 14.1 | 0.376 | True |
| 100000 | 1536 | gpu-native | f16 | 7.8 | 8.1 | 0.348 | True |
| 100000 | 1536 | gpu-container | f32 | 11.8 | 14.1 | 0.382 | True |
| 100000 | 1536 | gpu-container | f16 | 11.7 | 8.0 | 0.347 | True |
| 1000000 | 768 | cpu | f32 | 41.1 | 275.6 | 0.156 | False |
| 1000000 | 768 | gpu-native | f32 | 40.7 | 73.4 | 0.156 | True |
| 1000000 | 768 | gpu-native | f16 | 40.7 | 50.2 | 0.157 | True |
| 1000000 | 768 | gpu-container | f32 | 61.4 | 78.4 | 0.138 | True |
| 1000000 | 768 | gpu-container | f16 | 62.5 | 56.3 | 0.148 | True |
| 1000000 | 1536 | cpu | f32 | 77.0 | 545.5 | 0.149 | False |
| 1000000 | 1536 | gpu-native | f32 | 75.3 | 167.9 | 0.14 | True |
| 1000000 | 1536 | gpu-native | f16 | 75.4 | 86.5 | 0.137 | True |
| 1000000 | 1536 | gpu-container | f32 | 112.8 | 174.0 | 0.149 | True |
| 1000000 | 1536 | gpu-container | f16 | 124.7 | 99.5 | 0.149 | True |

Note: the synthetic dataset is uniform random, which is pathological for HNSW
(distance concentration) — recall values are only meaningful as a CPU vs GPU
comparison, not in absolute terms.

## Real-data comparison (mempalace, 384-dim, Cosine)

Vectors exported from a production collection (11,955 x 384). The amplified
set repeats them 10x with gaussian noise (sigma=1e-2) to preserve the
distribution at a measurable scale. Both engines ran the gpu-apple container
image (GPU on/off), m=16, ef_construct=100, single segment.

| engine | dataset | index build (s) | recall@10 |
|---|---|---:|---:|
| gpu | original 12K | 1.02 | 0.960 |
| cpu | original 12K | 0.51 | 0.997 |
| gpu | amplified 120K | 2.54 | 0.994 |
| cpu | amplified 120K | 5.59 | 0.997 |

Takeaways: below ~50K vectors the fixed GPU setup cost (shader compile,
upload) dominates and CPU wins; at 120K the GPU is 2.2x faster and the gap
widens with scale and dimension (see the synthetic matrix above). Recall on
real embeddings is 0.96+ for both engines — the low absolute recall in the
synthetic matrix is a property of uniform random data, not of the engines.
