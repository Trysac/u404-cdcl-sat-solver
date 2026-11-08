# Project record

## Objective

Pure-Python CDCL SAT solver with two-watched-literals, 1-UIP learning, DRAT proofs, and assumptions.

## Scope

- In scope: the public API documented in [README.md](../README.md), typed and tested.
- Out of scope: anything that needs runtime dependencies or I/O without an accepted ADR.

## Timeline

| Date | Event |
|---|---|
| 2026 | Repository created from the factory utility template. |

## Effort metrics

Measured values only; a value that has not been measured stays "pending measurement".

| Metric | Value |
|---|---|
| Tokens (input / output) | 1248701 / 9601 |
| Hours (human) | pending measurement |
| Cost (USD) | 0.2645 |

## Factory run cdcl-sat-solver-dimacs (measured from API usage)

| Phase | Model | Batch | Input | Output | Cache write | Cache read | Cost (USD) |
|---|---|---|---|---|---|---|---|
| generation | gemini-3.8-flash | yes | 8312 | 5019 | 0 | 0 | 0.0125 |
| fix-1 | gemini-3.8-flash | no | 34384 | 425 | 0 | 117460 | 0.0362 |
| fix-2 | gemini-3.8-flash | no | 10098 | 135 | 0 | 5876 | 0.0085 |
| fix-3 | gemini-3.8-flash | no | 4076 | 130 | 0 | 11899 | 0.0044 |
| fix-4 | gemini-3.8-flash | no | 13672 | 193 | 0 | 19167 | 0.0124 |
| fix-5 | gemini-3.8-flash | no | 24426 | 203 | 0 | 8635 | 0.0197 |
| fix-6 | gemini-3.8-flash | no | 16870 | 170 | 0 | 7741 | 0.0139 |
| fix-1 | gemini-3.8-flash | no | 61368 | 2423 | 0 | 350626 | 0.0814 |
| audit | gemini-3.1-flash-lite | no | 61534 | 451 | 0 | 215699 | 0.0215 |
| fix-2 | gemini-3.8-flash | no | 46656 | 452 | 0 | 230202 | 0.0540 |

Total: $0.2645. Prices: Anthropic list prices.

## Factory run cdcl-sat-solver-proof (measured from API usage)

| Phase | Model | Batch | Input | Output | Cache write | Cache read | Cost (USD) |
|---|---|---|---|---|---|---|---|
| generation | gemini-3.8-flash | yes | 8241 | 8359 | 0 | 0 | 0.0188 |
| fix-1 | gemini-3.8-flash | no | 22007 | 882 | 0 | 42117 | 0.0230 |
| fix-2 | gemini-3.8-flash | no | 23494 | 466 | 0 | 42994 | 0.0226 |
| fix-3 | gemini-3.8-flash | no | 13466 | 131 | 0 | 9244 | 0.0113 |
| audit | gemini-3.1-flash-lite | no | 53438 | 1182 | 0 | 132124 | 0.0184 |
| fix-4 | gemini-3.8-flash | no | 50764 | 1271 | 0 | 235588 | 0.0605 |

Total: $0.1546. Prices: Anthropic list prices.

## Factory run cdcl-sat-solver-engine (measured from API usage)

| Phase | Model | Batch | Input | Output | Cache write | Cache read | Cost (USD) |
|---|---|---|---|---|---|---|---|
| generation | gemini-3.8-flash | yes | 8905 | 46473 | 0 | 0 | 0.0905 |
| fix-1 | gemini-3.8-flash | no | 44345 | 664 | 0 | 206363 | 0.0512 |
| fix-2 | gemini-3.8-flash | no | 33075 | 240 | 0 | 36859 | 0.0285 |
| fix-3 | gemini-3.8-flash | no | 72547 | 1209 | 0 | 451540 | 0.0928 |
| audit | gemini-3.1-flash-lite | no | 96878 | 743 | 0 | 662594 | 0.0419 |
| fix-4 | gemini-3.8-flash | no | 102785 | 1247 | 0 | 1127581 | 0.1663 |
| fix-5 | gemini-3.8-flash | no | 29244 | 771 | 0 | 72085 | 0.0302 |

Total: $0.5014. Prices: Anthropic list prices.

## Factory run cdcl-sat-solver-facade (measured from API usage)

| Phase | Model | Batch | Input | Output | Cache write | Cache read | Cost (USD) |
|---|---|---|---|---|---|---|---|
| generation | gemini-3.8-flash | yes | 8887 | 58559 | 0 | 0 | 0.1131 |
| fix-1 | gemini-3.8-flash | no | 76928 | 1993 | 0 | 618803 | 0.1116 |
| fix-2 | gemini-3.8-flash | no | 130981 | 834 | 0 | 1648008 | 0.2250 |
| fix-3 | gemini-3.8-flash | no | 54244 | 193 | 0 | 200513 | 0.0564 |
| fix-1 | gemini-3.8-flash | no | 131590 | 926 | 0 | 1662361 | 0.2268 |
| fix-2 | gemini-3.8-flash | no | 106403 | 745 | 0 | 1047671 | 0.1612 |
| fix-3 | gemini-3.8-flash | no | 121904 | 2928 | 0 | 1540174 | 0.2179 |
| fix-4 | gemini-3.8-flash | no | 67896 | 492 | 0 | 506707 | 0.0908 |
| audit | gemini-3.1-flash-lite | no | 0 | 0 | 0 | 0 | 0.0000 |

Total: $1.2028. Prices: Anthropic list prices.
