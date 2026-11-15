# Assignment 3: Keys, Addresses, and Signed Transactions (`wallet`)

**Course**: Practical Blockchain Engineering (Dr. Mayank Agarwal, IIT Patna)  
**Student Name**: Navaneeth Nalla  
**Student Roll**: `2301AI14`  
**Webmail**: `navaneeth_2301ai14@iitp.ac.in`  
**Package**: `wallet`  

---

## 1. Overview & Purpose

A cryptographic wallet is not a container of coins; it is a key management and digital signing agent. It generates asymmetric keypairs from secure entropy, derives public identifiers (addresses) via one-way cryptographic hash functions, canonicalizes transaction payloads into deterministic byte streams, signs them, and permits trustless independent verification.

This assignment implements an educational wallet library and CLI (`wallet`) based on Ed25519 (RFC 8032) using Python's standard `cryptography` library.

---

## 2. Byte-Level Transaction Format Specification

Every transaction is committed as a canonical, deterministic JSON object transformed into UTF-8 bytes:

```json
{
  "version": 1,
  "network_id": "course-testnet",
  "sender": "mvN2x4rP7Y2XvK4jLzJ3aM5sN1b8...",
  "recipient": "mzQ1a5b8c9d0e1f2g3h4i5j6k7...",
  "amount_units": 1250000,
  "nonce": 7,
  "memo_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
}
```

### Field Definitions & Byte Constraints:
1. `version` (`uint32`): Protocol version (integer, must be positive).
2. `network_id` (`string`): Network domain separator (e.g., `"course-testnet"`), preventing cross-chain replay.
3. `sender` (`string`): 25-byte Base58Check-encoded address (`0x6f` prefix + 20-byte RIPEMD-160 + 4-byte checksum).
4. `recipient` (`string`): 25-byte Base58Check-encoded destination address.
5. `amount_units` (`uint64`): Atomic integer units (positive, overflow protected).
6. `nonce` (`uint64`): Strictly monotonic transaction sequence number per sender.
7. `memo_hash` (`hex string`): 64 hexadecimal characters representing a 32-byte payload digest (e.g. hash of payment details or smart contract data).

### Deterministic Serialization Rules:
- Keys are sorted lexicographically (`amount_units`, `memo_hash`, `network_id`, `nonce`, `recipient`, `sender`, `version`).
- Compact separators: `separators=(',', ':')` with zero whitespace around punctuation.
- Unicode normalization: All strings recursively normalized to NFC (`unicodedata.normalize('NFC', s)`).
- Two representations differing only in key ordering or whitespace serialize to the exact same bytes!

---

## 3. Cryptographic Derivations

### A. Address Derivation:
$$\text{SHA256}(\text{pubkey}) \to \text{RIPEMD160} \to \text{PubkeyHash (20 bytes)}$$
$$\text{Data} = 0\text{x}6f \parallel \text{PubkeyHash} \quad (21 \text{ bytes})$$
$$\text{Checksum} = \text{SHA256}(\text{SHA256}(\text{Data}))[0:4] \quad (4 \text{ bytes})$$
$$\text{Address} = \text{Base58}(\text{Data} \parallel \text{Checksum}) \quad (\sim 34 \text{ characters})$$

### B. Ed25519 Signing:
Ed25519 (RFC 8032) produces a deterministic 64-byte signature:
$$\sigma = \text{Ed25519\_Sign}(K_{\text{priv}}, \text{CanonicalBytes})$$
Signatures are non-malleable, completely deterministic, and eliminate ECDSA low-S malleability and PRNG reuse hazards.

---

## 4. Threat Model & Security Analysis

| Threat Category | Attack Vector | Mitigation in Wallet |
|---|---|---|
| **Key Theft** | Malware reading plain-text keys from disk or process memory. | Sensitive files written with restrictive permissions (`0600` / owner-only read-write). Prominent `WARNING: TEST ONLY - DO NOT USE ON MAINNET` header prevents accidental production usage. In production, keys must reside in hardware enclaves (HSM/Ledger/TPM). |
| **Weak Randomness** | Compromised PRNG (e.g. Debian OpenSSL 2008 bug) producing predictable keys. | System uses `os.urandom` / `secrets` backed by kernel cryptographically secure CSPRNG (`/dev/urandom` / Windows `BCryptGenRandom`). Ed25519 signature generation is deterministic (RFC 8032) and does not rely on per-signature random nonces. |
| **Replay Attacks** | Mallory intercepts Alice's signed tx and re-submits it on mainnet or multiple times on testnet. | **Network ID separation** ensures testnet signatures fail on mainnet. **Monotonic Nonce tracking** ensures any transaction with $\text{nonce} \le \text{last\_nonce}$ is permanently rejected. |
| **Clipboard Replacement** | Trojan monitors clipboard and swaps copied recipient address with Mallory's address. | Address format includes 4-byte double-SHA256 checksum (Base58Check). Typo or invalid character is instantly detected. Wallets must display full visual verification and address book confirmation. |
| **Phishing / Lookalike** | Attacker generates addresses matching first/last 4 characters of victim's address (vanity mining). | Verification functions check the cryptographic derivation from the signed public key. Users are prompted to verify the middle and checksum characters of the address. |
| **Accidental Mainnet Use** | Developer accidentally sends real assets to testnet address or exposes dev keys. | Version byte prefix `0x6f` generates testnet addresses (starting with `'m'` or `'n'`) distinct from Bitcoin mainnet `0x00` (`'1'`). Files include bold warnings. |

---

## 5. CLI Usage Examples

### 1. Key Generation
```bash
wallet keygen --out alice.key --pub-out alice_pub.json
```
**Output:**
```json
{
  "address": "mrT9C9kU3Z2eHk5L...",
  "public_key_hex": "4a5b6c...",
  "network_id": "course-testnet"
}
```

### 2. Derive Address from Public Key
```bash
wallet address --pubkey 4a5b6c...
```

### 3. Sign Transaction
```bash
wallet sign --key alice.key --tx tx.json --out signed_tx.json
```

### 4. Verify Signed Transaction
```bash
wallet verify --signed-tx signed_tx.json --state-db nonces.json
```
**Output:**
```
TRANSACTION VERIFIED: Signature, address derivation, nonce, and contents are authentic.
```

---

## 6. Running Tests

```bash
pytest -v
```
All 14 tests pass with 100% compliance across Base58Check validation, deterministic serialization invariance, replay attack prevention, and tamper detection.

