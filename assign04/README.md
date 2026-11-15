# Assignment 4: A UTXO Ledger and Transaction Validator (`utxo`)

**Course**: Practical Blockchain Engineering (Dr. Mayank Agarwal, IIT Patna)  
**Student Roll**: `2301AI14`  
**Package**: `utxo`  

---

## 1. Overview & Purpose

The Unspent Transaction Output (UTXO) model forms the foundational state-transition engine of Bitcoin and related distributed ledgers. Rather than maintaining account balances (like a banking ledger), ownership is tracked as a discrete set of unspent graphical outputs. Each transaction consumes existing UTXOs in their entirety as inputs and creates new UTXOs as outputs.

This assignment implements an in-memory UTXO ledger engine, P2PKH validator, and wallet transaction builder (`utxo`).

---

## 2. Core Data Models

1. **`OutPoint`**:
   - `tx_id`: 64 hexadecimal characters (double-SHA256 of canonical transaction).
   - `output_index`: Zero-indexed integer identifying the specific output within `tx_id`.
   - String serialization: `"<tx_id>:<output_index>"`.
2. **`TxOutput`**:
   - `value`: Strictly positive integer amount ($\text{value} > 0$).
   - `pubkey_hash`: 20-byte hexadecimal string ($40 \text{ characters} = \text{RIPEMD-160}(\text{SHA-256}(K_{\text{pub}}))$).
3. **`TxInput`**:
   - `prev_tx_id`: 64-character hex ID of the transaction containing the output being consumed.
   - `prev_out_index`: Index of the output in the previous transaction.
   - `signature_hex`: 128-character hex Ed25519 signature over the sighash.
   - `pubkey_hex`: 64-character hex public key of the spender.
4. **`Transaction`**:
   - `inputs`: Ordered list of `TxInput` elements.
   - `outputs`: Ordered list of `TxOutput` elements.
   - `locktime`: Transaction locktime sequence (default `0`).
   - `tx_id`: Deterministic double-SHA256 digest of canonical serialized transaction bytes.

---

## 3. P2PKH Locking Condition & Sighash Specification

Each input must satisfy the Pay-to-Public-Key-Hash (P2PKH) authorization rule:
1. **Hash Lock**:
   $$\text{RIPEMD160}(\text{SHA256}(\text{input.pubkey})) \stackrel{?}{=} \text{referenced\_utxo.pubkey\_hash}$$
2. **Signature Verification**:
   The spender must sign a deterministic commitment to the entire unsigned transaction skeleton bound to the specific input index:
   $$\text{sighash} = \text{SHA256}\Big(\text{CanonicalJSON}\big(\{\text{inputs}, \text{outputs}, \text{locktime}, \text{signed\_input\_index}: i\}\big)\Big)$$
   $$\text{Verify}(\text{input.pubkey}, \text{input.signature}, \text{sighash}) \stackrel{?}{=} \text{True}$$

---

## 4. Deterministic Coin Selection: Largest-First Strategy

When building a transaction, the wallet builder collects UTXOs matching the sender's `pubkey_hash` and executes the **Largest-First** algorithm:
1. Filter confirmed ledger UTXOs where $\text{output.pubkey\_hash} == \text{sender.pubkey\_hash}$.
2. Sort candidate outputs in **descending order of value**.
3. **Deterministic Tie-Breaking**: If two UTXOs have identical values, sort lexicographically by `(outpoint.tx_id ASC, outpoint.output_index ASC)`.
4. Greedily accumulate UTXOs until:
   $$\sum \text{selected\_values} \ge \text{target\_amount} + \text{fee}$$
5. If $\sum \text{selected\_values} > \text{target\_amount} + \text{fee}$, automatically construct a change output:
   $$\text{change} = \sum \text{selected\_values} - (\text{target\_amount} + \text{fee})$$
   locked to the sender's own `pubkey_hash`.

---

## 5. Atomicity & Validation Rejection Trace

State mutation occurs **strictly after all validations succeed**. If any check fails, the ledger state remains 100% unaltered.

### Alice-Pays-Bob Canonical Scenario
- Initial State: Alice holds two UTXOs:
  - `1111...:0` with value **40**
  - `2222...:1` with value **70**
- Action 1: Alice pays Bob **85 units with fee 2**.
  - Coins selected: 70 + 40 = 110.
  - Outputs created: 85 to Bob, 23 change to Alice.
  - Fee collected: $110 - (85 + 23) = 2$.
  - Status: **`ACCEPTED`**.
- Action 2: Re-submitting the exact same transaction (Double Spend Attack).
  - Status: **`REJECTED`** with `REJECT_MISSING_UTXO`.

### Summary of Rejection Codes Tested:

| Rejection Code | Trigger Condition |
|---|---|
| `REJECT_MISSING_UTXO` | Input references an OutPoint already spent or never created (double spend). |
| `REJECT_DUPLICATE_INPUT` | Same transaction contains two inputs referencing the exact same OutPoint. |
| `REJECT_VALUE_CREATION` | Total output values exceed total input values ($\sum \text{in} < \sum \text{out}$). |
| `REJECT_INVALID_OUTPUT_VALUE` | Output value $\le 0$ (negative or zero value outputs). |
| `REJECT_INTEGER_OVERFLOW` | Output value or cumulative sums exceed $2^{63} - 1$. |
| `REJECT_LOCK_MISMATCH` | Provided public key hash does not match UTXO's recorded `pubkey_hash`. |
| `REJECT_BAD_SIGNATURE` | Cryptographic signature fails verification against sighash. |
| `REJECT_MALFORMED_PUBKEY` | Public key length $\ne 32$ bytes (64 hex characters). |
| `REJECT_MALFORMED_SIG` | Signature length $\ne 64$ bytes (128 hex characters). |
| `REJECT_EMPTY_INPUTS` | Transaction contains 0 inputs. |
| `REJECT_EMPTY_OUTPUTS` | Transaction contains 0 outputs. |

---

## 6. CLI Usage & Demo

Run the end-to-end Alice-pays-Bob scenario:
```bash
utxo demo-alice-bob
```
**Output:**
```
===========================================================================
UTXO LEDGER EXECUTION DEMO: ALICE PAYS BOB SCENARIO
===========================================================================
Alice PubKeyHash: d5491f2f58dd8cda4d0fe79d46e03448684dc44e
Bob   PubKeyHash: ea41b748d09c65921661aeec50f4e5ace4692259

--- INITIAL UTXO LEDGER STATE ---
  1111111111111111111111111111111111111111111111111111111111111111:0 => value:  40, owner: d5491f2f58dd8cda4d0fe79d46e03448684dc44e
  2222222222222222222222222222222222222222222222222222222222222222:1 => value:  70, owner: d5491f2f58dd8cda4d0fe79d46e03448684dc44e

[ACTION 1] Alice builds and signs transaction paying 85 to Bob with fee 2...
Transaction ID: 83190563122a0c5e99d3d2bf7811d572988eb124c1db18f994d5f3985e6639bf
Inputs consumed: ['2222222222222222222222222222222222222222222222222222222222222222:1', '1111111111111111111111111111111111111111111111111111111111111111:0']
Outputs created: [(85, 'ea41b748d09c65921661aeec50f4e5ace4692259'), (23, 'd5491f2f58dd8cda4d0fe79d46e03448684dc44e')]
Submission 1 Result: ACCEPTED (Fee collected: 2)

--- UTXO LEDGER STATE AFTER TRANSACTION 1 ---
  83190563122a0c5e99d3d2bf7811d572988eb124c1db18f994d5f3985e6639bf:0 => value:  85, owner: Bob (ea41b748d09c65921661aeec50f4e5ace4692259)
  83190563122a0c5e99d3d2bf7811d572988eb124c1db18f994d5f3985e6639bf:1 => value:  23, owner: Alice (change) (d5491f2f58dd8cda4d0fe79d46e03448684dc44e)

[ACTION 2] Mallory re-submits the exact same transaction (Double Spend Attack)...
Submission 2 Result: REJECT_MISSING_UTXO: Referenced OutPoint 2222222222222222222222222222222222222222222222222222222222222222:1 does not exist in ledger.
===========================================================================
```

---

## 7. Running Tests

```bash
pytest -v
```
All **22 comprehensive unit tests** pass with 100% coverage across double-spends, coin selection, atomicity rollback, P2PKH locks, zero-fees, and snapshot persistence.

