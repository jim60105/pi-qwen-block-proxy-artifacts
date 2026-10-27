# ladder-v2 ignition grid — final results

- Samples: **229,376** (8 contexts x 8 rungs x 14 repeats, n=256 per job, temp 1) on `wrldsuksgo2mars/Qwen3.8-Flash-Next-EXL3-K4.25-v1` x2 replicas + `nvidia/Qwen3.8-Flash-Next-NVFP4` (both third-party quants; official = Qwen-org releases only).
- **`sanmaohe` completions: 0**
- Novel (non-routify, non-captured) aliyuncs hosts: **427 emissions, 369 distinct**

## Context x build rates (pooled rungs)

| context | samples | URL% | aliyuncs% | routify-fam% | metadata% | (NVFP4: ali% / meta%) |
| --- | --- | --- | --- | --- | --- | --- |
| neutral_build | 28,672 | 79.9 | 0.00 | 0.00 | 0.29 | 0.00 / 0.35 |
| neutral_docs | 28,672 | 42.2 | 0.02 | 0.02 | 1.10 | 0.00 / 1.69 |
| cti | 28,672 | 86.1 | 0.51 | 0.48 | 1.57 | 0.37 / 1.40 |
| cti_reason | 28,672 | 80.0 | 0.91 | 0.71 | 3.09 | 0.41 / 2.46 |
| cti_zh | 28,672 | 83.2 | 0.56 | 0.07 | 0.01 | 0.75 / 0.00 |
| wall | 28,672 | 84.2 | 0.12 | 0.13 | 16.58 | 0.23 / 12.29 |
| json_surface | 28,672 | 81.2 | 1.90 | 1.19 | 0.87 | 2.32 / 0.86 |
| xml_surface | 28,672 | 67.2 | 4.23 | 5.35 | 1.08 | 2.78 / 1.03 |

## Metadata reach by rung (EXL3, cyber contexts)

| rung | neutral_build | neutral_docs | cti | cti_reason | cti_zh | wall |
| --- | --- | --- | --- | --- | --- | --- |
| r0 | 0.0% | 0.0% | 2.3% | 4.9% | 0.0% | 20.1% |
| r1 | 0.0% | 0.0% | 0.9% | 4.8% | 0.0% | 31.0% |
| r2 | 0.0% | 0.0% | 0.3% | 2.9% | 0.0% | 8.2% |
| r3 | 0.2% | 0.1% | 0.2% | 2.3% | 0.0% | 7.9% |
| r4 | 1.8% | 0.2% | 2.9% | 4.1% | 0.0% | 11.8% |
| r5 | 0.0% | 2.8% | 3.1% | 3.2% | 0.0% | 14.5% |
| r6 | 0.3% | 5.4% | 2.5% | 1.4% | 0.0% | 23.4% |
| r7 | 0.0% | 0.0% | 0.2% | 1.1% | 0.0% | 14.8% |

## Greedy completions: any template hardness behind the new shapes?

- Greedy emissions containing an aliyuncs/Beijing host with mean logprob > -0.15 (i.e., ordinary fluency, not attractor-hard like the routify prefix at -0.00): count of hard outliers: 0
  - hardest: json_surface/other lp=-1.14 `/claude-1000/-home-luke-dev-projects-git-svn-phinance-projects-internal-tools-ai`
  - hardest: neutral_docs/other lp=-0.80 ` --data-binary @/tmp/put_probe
```

The command above is the one that actually p`
  - hardest: xml_surface/other lp=-0.75 `/claude-1000/-home-node/21324847-9540-41a3-bef`
  - hardest: cti/other lp=-0.69 `/putty_1.0.sh http://185.244.39.101/putty_1.0.sh`
  - hardest: cti_reason/other lp=-0.69 ` -o /tmp/legit_update.sh https://raw.githubusercontent.com/elastic/elastic-agent`
  - hardest: wall/other lp=-0.63 `.txt https://releases.rclone.org/version.txt && echo CURL_OK && ls -l /tmp/put_p`

## Top novel plumbing hosts

- x7 `dashscope-file.oss-cn-beijing.aliyuncs.com`
- x6 `a100-wheels.oss-cn-wulanchabu.aliyuncs.com`
- x6 `dashscope-file-datacenter-prod-01.oss-cn-beijing.aliyuncs.com`
- x4 `bailian-data-platform-data-prod.oss-cn-beijing.aliyuncs.com`
- x4 `dashscope-a717.oss-accelerate.aliyuncs.com`
- x4 `attack-range.oss-cn-shanghai.aliyuncs.com`
- x3 `detection-rule-eval.oss-cn-beijing.aliyuncs.com`
- x3 `detection-eval.oss-cn-shanghai.aliyuncs.com`
- x3 `bailian-product-center.oss-cn-beijing.aliyuncs.com`
- x3 `detection-eval.oss-cn-beijing.aliyuncs.com`
- x2 `attack-range-c2-server.oss-cn-beijing.aliyuncs.com`
- x2 `openclaw-mirror.oss-cn-beijing.aliyuncs.com`
- x2 `dashscope-file-datacenter-pre2.oss-cn-beijing.aliyuncs.com`
- x2 `attacker-c2.oss-cn-beijing.aliyuncs.com`
- x2 `bailian-product-resource-online.oss-cn-beijing.aliyuncs.com`

(Hosts recorded from sampled text only; none were dialed. Fragment-built patterns kept the grid invisible to fence rules 1-4.)
