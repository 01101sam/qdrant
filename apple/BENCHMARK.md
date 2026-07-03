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
