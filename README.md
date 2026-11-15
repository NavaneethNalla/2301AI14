# IIT Patna CSE — Practical Blockchain Engineering Coursework

**Instructor**: Dr. Mayank Agarwal  
**Student Roll**: `2301AI14`  
**Webmail**: `navaneeth_2301ai14@iitp.ac.in`  
**Reference Structure**: Aligned with [mayank265/9901CS06](https://github.com/mayank265/9901CS06)

---

## 1. Repository Overview

This repository contains the complete, production-grade implementations for all 7 Blockchain assignments. Each assignment is structured modularly with its own `src/`, `tests/`, configuration manifest (`pyproject.toml` / `package.json`), and comprehensive `README.md` containing formal specifications, threat models, architectural diagrams, benchmark data, and execution receipts.

| Folder | Package / System | Topic | Tech Stack | Tests | Status |
|---|---|---|---|---|---|
| [`assign01/`](./assign01/) | `hashlab` | Bytes, Hashes & Reproducible Data | Python 3.11+, `hashlib` | 19 Unit Tests | **PASS (100%)** |
| [`assign02/`](./assign02/) | `merkle` | Merkle Trees & Proofs of Inclusion | Python 3.11+, `pytest` | 25 Unit Tests | **PASS (100%)** |
| [`assign03/`](./assign03/) | `wallet` | Keys, Addresses & Signed Transactions | Python 3.11+, `cryptography` (Ed25519) | 14 Unit Tests | **PASS (100%)** |
| [`assign04/`](./assign04/) | `utxo` | In-Memory UTXO Ledger & Validator | Python 3.11+, `pytest` | 22 Unit Tests | **PASS (100%)** |
| [`assign05/`](./assign05/) | `chain` | PoW Blockchain, Forks & Reorganisation | Python 3.11+, `pytest` | 11 Unit Tests | **PASS (100%)** |
| [`assign06/`](./assign06/) | `p2p` | P2P Mempool & Block Relay Network | Python 3.11+, `asyncio` | 10 Unit Tests | **PASS (100%)** |
| [`assign07/`](./assign07/) | `Escrow` | Solidity Escrow Contract & Deployment | Solidity 0.8.20, Hardhat 2 | 23 Unit & Fuzz Tests | **PASS (100%)** |

---

## 2. Directory Layout

```
2301AI14/
├── .gitignore                    # Global git ignore (caches, node_modules, .venv)
├── roll.md                       # Official student roll & webmail identifier
├── README.md                     # Root index and quickstart guide
├── Blockchain_Assignments.pdf    # Course assignment specifications
├── assign01/                     # Assignment 1: hashlab
│   ├── README.md
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── src/hashlab/
│   └── tests/
├── assign02/                     # Assignment 2: merkle
│   ├── README.md
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── src/merkle/
│   └── tests/
├── assign03/                     # Assignment 3: wallet
│   ├── README.md
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── src/wallet/
│   └── tests/
├── assign04/                     # Assignment 4: utxo
│   ├── README.md
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── src/utxo/
│   └── tests/
├── assign05/                     # Assignment 5: chain
│   ├── README.md
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── src/chain/
│   └── tests/
├── assign06/                     # Assignment 6: p2p
│   ├── README.md
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── src/p2p/
│   └── tests/
└── assign07/                     # Assignment 7: Solidity Escrow
    ├── README.md
    ├── package.json
    ├── hardhat.config.js
    ├── src/Escrow.sol
    ├── tests/Escrow.test.js
    └── scripts/deploy_and_interact.js
```

---

## 3. Quickstart: Running Tests & Demos

### Global Test Runner
To execute the automated verification test suites across all 7 assignments:

```bash
# Python Assignments (1 through 6)
cd assign01 && pytest -v && cd ..
cd assign02 && pytest -v && cd ..
cd assign03 && pytest -v && cd ..
cd assign04 && pytest -v && cd ..
cd assign05 && pytest -v && cd ..
cd assign06 && pytest -v && cd ..

# Solidity Assignment 7
cd assign07 && npm test && cd ..
```

---

### Detailed Assignment Overviews

#### Assignment 1: `assign01` (`hashlab`)
- **Key Features**: Diagnostic CLI for text, hex, and file streaming; avalanche effect analysis; deterministic canonical JSON serialization; visual differences demonstration.
- **Commands**:
  ```bash
  cd assign01
  pip install -e .
  hashlab text "Alice pays Bob 10"
  hashlab avalanche --text "Alice pays Bob 10" --bit 7
  hashlab demo-differences
  pytest -v
  ```

#### Assignment 2: `assign02` (`merkle`)
- **Key Features**: Domain-separated SHA-256 leaf (`0x00`) and node (`0x01`) hashing; unambiguous odd-leaf node promotion; inclusion proof generation in JSON; independent verification; high-performance scaling (100,000 leaves in 0.12s).
- **Commands**:
  ```bash
  cd assign02
  pip install -e .
  merkle root "tx1" "tx2" "tx3" "tx4" "tx5"
  merkle prove --index 2 "tx1" "tx2" "tx3" "tx4" "tx5" --out proof.json
  merkle benchmark
  pytest -v
  ```

#### Assignment 3: `assign03` (`wallet`)
- **Key Features**: Ed25519 asymmetric cryptography; Base58Check address derivation (`0x6f` testnet prefix + 4-byte double-SHA256 checksum); deterministic canonical JSON transaction format; signing and independent verification; nonce replay tracking.
- **Commands**:
  ```bash
  cd assign03
  pip install -e .
  wallet keygen --out dev.key --pub-out pub.json
  wallet sign --key dev.key --tx sample_tx.json --out signed_tx.json
  wallet verify --signed-tx signed_tx.json
  pytest -v
  ```

#### Assignment 4: `assign04` (`utxo`)
- **Key Features**: Discrete UTXO accounting with P2PKH script verification; deterministic `tx_id` computation; Largest-First coin selection with tie-breaking by `(tx_id, output_index)`; atomic state updates; double-spend prevention; snapshot serialization.
- **Commands**:
  ```bash
  cd assign04
  pip install -e .
  utxo demo-alice-bob
  pytest -v
  ```

#### Assignment 5: `assign05` (`chain`)
- **Key Features**: Canonical 116-byte binary block headers; Proof-of-Work CPU miner; Merkle root commitments over block transaction sets; Cumulative work chain selection (shorter high-work branches strictly dominate longer low-work branches); atomic chain reorganisations.
- **Commands**:
  ```bash
  cd assign05
  pip install -e .
  chain hex-dump
  chain benchmark
  chain simulate-fork
  pytest -v
  ```

#### Assignment 6: `assign06` (`p2p`)
- **Key Features**: Asyncio TCP localhost networking; 4-byte length-prefixed framing with 1 MB cap; inventory-first gossip relay (`inv` $\to$ `getdata` $\to$ `tx` / `block`); mempool with fee-rate prioritization and conflict rejection; token-bucket rate limiter; 5-node partition and healing convergence experiment.
- **Commands**:
  ```bash
  cd assign06
  pip install -e .
  p2p simulate-partition
  pytest -v
  ```

#### Assignment 7: `assign07` (`Escrow.sol`)
- **Key Features**: Production-grade Solidity 0.8.20 escrow contract; 7-state finite state machine (`Created`, `Funded`, `Released`, `Disputed`, `ResolvedToBuyer`, `ResolvedToSeller`, `Cancelled`); custom errors; events; checks-effects-interactions; pull-over-push payments (`withdraw()`); solvency invariant `balance == totalLiabilities`; unit and fuzz tests; automated local deployment script.
- **Commands**:
  ```bash
  cd assign07
  npm test
  npm run deploy
  ```
