# Core Runtime Capability Matrix

| Skill | Executor | Independent | Pipeline fallback | Real data | Contract safe |
|---|---:|---:|---:|---:|---:|
| industrial-analysis | 是 | 是 | 否 | 是 | 是 |
| standardization | 是 | 是 | 核心路径否 | 是 | 是 |
| cleaning | 是 | 是 | 核心路径否 | 是 | 是 |
| segmentation | 是 | 是 | 核心路径否 | 是 | 是 |
| modeling | 是 | 是 | 核心路径否 | 是 | 是 |
| optimization | 是 | 是 | 核心路径否 | 是 | 是 |
| review | 是 | 是 | 否 | 是 | 是 |
| report | 是 | 是 | 否 | 是 | 是 |
| simulation | 是 | 是 | 否 | 不适用（显式仿真） | 是 |
| visualization | 是 | 是 | 否 | 是 | 是 |
| experiment | 是 | 是 | 否 | 是 | 是 |
| supervision | 是 | 是 | 否 | 是 | 是 |

本轮要求的八个核心执行 Skill 中已无 reader-only。合并最新远程基线后，Registry 还包含四个已注册的独立 Executor。未注册的 Catalog 能力通过 `executor_status()` 返回 unavailable；治理和文档节点继续按 planner/read 活动计数，不计入 executed。
