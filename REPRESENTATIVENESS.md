# Representativeness of the 100-item sample

Population represented: **corpus chunks with >= 50 tokens** (274,236 of 296,381 chunks = 92.5% of the corpus).

Selected from the **268** clean pool items (283 uncontested, minus those under the floor).

Matched marginals below. Language is **not** a stratum: the corpus is 100% Russian.

**Source (database)**

| stratum | corpus % | sample n | sample % | diff |
|---|---:|---:|---:|---:|
| telegram_official | 89.23 | 88 | 88.00 | -1.23 |
| kremlin | 4.42 | 5 | 5.00 | +0.58 |
| state_duma | 3.84 | 4 | 4.00 | +0.16 |
| federation_council | 2.51 | 3 | 3.00 | +0.49 |

**Chunk length (corpus token quartiles)**

| stratum | corpus % | sample n | sample % | diff |
|---|---:|---:|---:|---:|
| Q1 | 25.00 | 25 | 25.00 | +0.00 |
| Q2 | 25.00 | 25 | 25.00 | +0.00 |
| Q3 | 25.00 | 25 | 25.00 | +0.00 |
| Q4 | 25.00 | 25 | 25.00 | +0.00 |

**Year era**

| stratum | corpus % | sample n | sample % | diff |
|---|---:|---:|---:|---:|
| 2014-2019 | 6.24 | 6 | 6.00 | -0.24 |
| 2020-2021 | 9.35 | 8 | 8.00 | -1.35 |
| 2022 | 15.03 | 16 | 16.00 | +0.97 |
| 2023 | 18.08 | 19 | 19.00 | +0.92 |
| 2024 | 20.74 | 21 | 21.00 | +0.26 |
| 2025 | 19.52 | 19 | 19.00 | -0.52 |
| 2026 | 9.21 | 9 | 9.00 | -0.21 |
| <2014 | 1.84 | 2 | 2.00 | +0.16 |

**Source identity (channel)**

| stratum | corpus % | sample n | sample % | diff |
|---|---:|---:|---:|---:|
| Минобороны России | 12.60 | 13 | 13.00 | +0.40 |
| МИД России 🇷🇺 | 10.92 | 11 | 11.00 | +0.08 |
| МВД МЕДИА | 10.34 | 7 | 7.00 | -3.34 |
| МЧС России | 6.39 | 5 | 5.00 | -1.39 |
| Правительство России | 6.14 | 6 | 6.00 | -0.14 |
| kremlin.ru | 4.42 | 5 | 5.00 | +0.58 |
| Минстрой России | 4.08 | 2 | 2.00 | -2.08 |
| duma.gov.ru | 3.84 | 4 | 4.00 | +0.16 |
| Русский дом | 3.81 | 3 | 3.00 | -0.81 |
| Marina Akhmedova | 3.07 | 3 | 3.00 | -0.07 |
| Настоящий Гладков | 3.01 | 3 | 3.00 | -0.01 |
| Росгвардия | 2.99 | 3 | 3.00 | +0.01 |
| council.gov.ru | 2.51 | 3 | 3.00 | +0.49 |
| Мэр Москвы Сергей Собянин | 2.06 | 2 | 2.00 | -0.06 |
| Юнармия | 2.01 | 2 | 2.00 | -0.01 |
| Минфин России | 1.93 | 2 | 2.00 | +0.07 |
| Kadyrov_95 | 1.93 | 2 | 2.00 | +0.07 |
| Мария Захарова | 1.81 | 4 | 4.00 | +2.19 |
| Минэкономразвития России | 1.81 | 1 | 1.00 | -0.81 |
| Кремль. Новости | 1.68 | 2 | 2.00 | +0.32 |

## Labels are deliberately over-sampled

Corpus NTS prevalence is **2.563%**. This sample carries **18 NTS-positive of 100** = 18.0%, an enrichment of **7.0x**. A prevalence-faithful sample of 100 would contain about 3 nuclear items and could not measure a miss rate. Report metrics twice: conditional on this challenge set, and reweighted to corpus prevalence using inverse-probability weights (NTS-positive weight = 0.1424).

Deterministic: seed 20260901, sorted inputs. sha256 `1314c6cb2798c6d31134631ff71bf1a8`.