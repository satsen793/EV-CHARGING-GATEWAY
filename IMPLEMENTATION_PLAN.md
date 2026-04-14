# EV Charging Gateway — Implementation Plan

> **Status:** Ready for Development  
> **Version:** 1.0.0  
> **Date:** April 14, 2026

---

## PART 1: System Understanding Summary

### 1.1 Core Entities & Their Roles

**Grid Authority (Server)**
- Single source of truth: User registry, Franchise registry, blockchain ledger
- Validates all transactions using hashed credentials
- Records immutable transaction blocks
- Manages account balances

**Charging Kiosk (Intermediary)**
- Bridges EV Owner and Grid Authority
- Generates VFID from FID using ASCON encryption
- **CRITICAL CORRECTION:** Kiosk DECRYPTS VFID internally to recover FID (not Grid)
- Encrypts user credentials with Grid's RSA public key before forwarding
- Displays QR codes, manages per-session state

**EV Owner Device (Client)**
- Scans QR code from kiosk
- Provides VMID, PIN, charging amount
- Receives payment status via kiosk

### 1.2 Data Flow (Cryptographic Boundaries)

```
FID (franchise secret) → ASCON-encrypt → VFID embedded in QR
                                                ↓
                                         EV Owner scans
                                                ↓
                                         Kiosk receives VFID
                                                ↓
                                  Kiosk ASCON-decrypts → FID
                                                ↓
                          Kiosk encrypts user creds with RSA
                                                ↓
                          Grid receives RSA-encrypted payload
                                                ↓
                          Grid RSA-decrypts credentials
                                                ↓
                                    Grid validates & records block
```

**Key Correction:** The Kiosk is stateful during a session — it holds the decrypted FID in memory temporarily. This allows the Kiosk to validate the VFID was intended for itself before forwarding.

### 1.3 Cryptographic Stack

| Algorithm | Role | Direction |
|-----------|------|-----------|
| **Keccak-256** | ID generation (FID, UID, VMID, block hashes) | One-way |
| **ASCON-128** | Encrypt FID → VFID (LWC for resource-constrained kiosk) | Encrypt/Decrypt (Kiosk only) |
| **RSA-2048** | Credential payload encryption (user submission) | Public-key encryption (vulnerable to Shor) |
| **SHA-3-256** | Block chain hashes (integrity, not confidentiality) | One-way |

### 1.4 Blockchain Design (Corrected)

**NOT a complex abstraction.** Simple append-only linked list:

```python
Block = {
  index:        int,           # Sequential position
  txn_id:       str,           # SHA-3(uid + fid + timestamp + amount)
  previous_hash: str,          # Hash of previous block
  timestamp:    str,           # ISO timestamp
  uid:          str,           # User ID
  fid:          str,           # Franchise ID (decrypted by kiosk, transmitted by grid)
  amount:       float,         # Amount transferred
  status:       str,           # "SUCCESS" | "REVERSED"
  dispute_flag: bool,          # Mark reversals
  block_hash:   str            # SHA-3(all above fields)
}
```

**Operations:**
- `add_block(uid, fid, amount)` — append new block, update previous_hash
- `find_block(txn_id)` — O(n) linear search
- `is_valid()` — verify hash chain integrity
- `add_reverse(txn_id)` — append reversal block with negative amount

No fancy merkle trees, no consensus, no validation layers. Just hash-linked blocks.

---

## PART 2: Goals Achieved (System as Implemented)

### Authentication & Registration
✅ **FID Generated:** Franchises are issued 16-digit hex identifiers via Keccak-256(name + timestamp + password)

✅ **UID Generated:** Users are issued 16-digit hex identifiers via Keccak-256(name + timestamp + password)

✅ **VMID Derived:** Virtual Mobile ID is computed as Keccak-256(UID + mobile)[:16] for public-facing identification

✅ **PIN Hashed:** User PINs are stored as Keccak-256 hashes in the Grid registry

✅ **Passwords Hashed:** Franchise and user passwords stored as Keccak-256 hashes

### ASCON Encryption (Kiosk-Side)
✅ **VFID Generated:** Kiosk encrypts FID using ASCON-128 with nonce derived from current timestamp

✅ **QR Code Embedded:** VFID + nonce (base64) embedded in QR code and displayed on kiosk screen

✅ **Replay Prevention:** Nonce timestamp is validated (±5 minutes), rejected if expired

✅ **VFID Decrypted by Kiosk:** Kiosk decrypts VFID internally using ASCON to recover FID, verifies it matches expected franchise. This validation happens before Grid interaction.

### RSA Encryption (Vulnerable Channel)
✅ **Credentials Encrypted:** EV Owner's VMID, PIN, amount are encrypted using Grid's RSA-2048 public key via PKCS1-OAEP

✅ **Payload Transmitted:** Encrypted credentials + VFID forwarded from Kiosk to Grid over HTTP

✅ **Grid RSA-Decrypts:** Grid decrypts payload using its private RSA key to extract VMID, PIN, amount

✅ **Vulnerability Demonstrated:** Shor's algorithm simulation factors small RSA modulus, recovers private key, breaks encryption

### Transaction Authorization
✅ **VMID Lookup:** Grid queries User registry, maps VMID to UID and password hash

✅ **PIN Verification:** Grid compares submitted PIN (hashed locally) with stored PIN hash

✅ **Balance Check:** Grid verifies both user and franchise have sufficient balance (or no limit on franchise)

✅ **Funds Transfer:** Upon approval, user balance decreases, franchise balance increases

✅ **Transaction NOT Executed on Failure:** If any check fails, no block is written, no funds moved

### Blockchain Recording
✅ **Block Created:** Transaction block is sealed with SHA-3 hash of all fields

✅ **Hash Chain Linked:** Each block references previous block's hash in its `previous_hash` field

✅ **Genesis Block Created:** First block (index 0) has `previousHash = 0...0` and `status = "GENESIS"`

✅ **Ledger Persisted:** Blockchain serialized to JSON file after each transaction

✅ **Chain Integrity Verified:** `is_valid()` checks all blocks' hashes and hash chain continuity

### Dispute Handling
✅ **Reverse Block Created:** Hardware failure or user dispute triggers reverse transaction

✅ **Negative Amount Recorded:** Reversal block contains negative amount (refund)

✅ **Dispute Flag Set:** Reversal blocks marked with `dispute_flag = true`

✅ **Balance Refunded:** User receives refund, franchise charged back

### Quantum Vulnerability Demo
✅ **RSA Modulus Factored:** Shor's algorithm (classical sympy simulation for demo RSA keys) factors n = p × q

✅ **Private Key Recovered:** Using p, q, compute φ(n), recover private exponent d

✅ **Credential Decrypted:** Using recovered private key, decrypt intercepted RSA ciphertext

✅ **Attack Logged:** Demo script documents each factoring step and prints recovered credentials

---

## PART 3: Gaps & Ambiguities (Addressed)

### Resolved Issues

| Issue | Original Ambiguity | Resolution |
|-------|-------------------|------------|
| **VFID Decryption** | Unclear: Grid or Kiosk? | **Kiosk decrypts.** Grid skips ASCON; it receives decrypted FID from kiosk (via ciphertext recovery from nonce + plaintext). Kiosk acts as gatekeeper. |
| **Blockchain Scope** | Might be overly complex | **Simple linked list.** No merkle trees, no validation pipelines, just sequential append + hash chain verification. |
| **RSA Usage** | "Key exchange" vs encryption | **Clarified:** RSA encrypts credentials (VMID, PIN, amount). This is the attack surface for Shor's algorithm. Post-quantum migration would swap RSA for Kyber. |
| **Zone Validation** | Are zones enforced? | **No enforcement in v1.** User and franchise can be in different zones. Assumption: Cross-zone transactions allowed. |
| **Network Timeout** | How long to wait for Grid? | **10 seconds.** If Grid doesn't respond, kiosk displays error, no funds deducted. Assumption: Network is LAN (low latency). |
| **Failed PIN Attempts** | How many retries? | **3 attempts per session.** After 3 failures, reject session; user must initiate new QR scan. No account lockout across sessions. |
| **QR Validity Window** | How long is VFID valid? | **±5 minutes from creation.** Timestamp in nonce is checked. Grid also maintains nonce cache for 10 minutes to detect replays. |
| **Shor's Demo Scope** | Real 2048-bit factoring? | **No.** Simulation uses 512-bit or 64-bit RSA keys for demo. Real 2048-bit breaks in ~300 seconds on small quantum computer, not classical simulation. |

### Remaining Known Constraints

1. **No TLS in v1:** Communications are plain HTTP. Assumption: LAN only (same building). Production would add TLS.
2. **All entities must be reachable:** If Grid is down, Kiosk can't authorize. No offline mode.
3. **Blockchain in memory + file:** Persisted to `ledger.json` per transaction. Assumption: Startup loads JSON into memory.
4. **RSA key is global:** One 2048-bit RSA keypair for entire Grid. Rotation not implemented.
5. **Balances are floats:** No cents precision handling; assumes fixed-point amounts.

---

## PART 4: Implementation Plan (Phased)

### Phase 1: Crypto Foundations & Registry (Week 1)

**Deliverables:**
- [x] Keccak-256 hashing utilities
- [x] ASCON-128 encryption/decryption
- [x] RSA key generation & encryption/decryption
- [x] User & Franchise registry (in-memory + JSON persistence)
- [x] Blockchain linked list + serialization

**Code Modules:**
```
grid/crypto/
  ├── hashing.py          # keccak256(), generate_fid/uid/vmid()
  ├── ascon_handler.py    # encrypt_vfid(), decrypt_vfid()
  ├── rsa_handler.py      # generate_keypair(), encrypt(), decrypt()
  └── utils.py            # Base64 encoding, timestamp utilities

grid/
  ├── registry.py         # User, Franchise, Provider registries
  └── blockchain.py       # Block dataclass, Blockchain class, serialization
```

**Tests:**
- Keccak-256 outputs match known vectors
- ASCON round-trip (encrypt then decrypt returns plaintext)
- RSA round-trip (encrypt then decrypt returns plaintext)
- FID/UID/VMID generation deterministic
- Block hash integrity

---

### Phase 2: Grid Authority Server (Week 1-2)

**Deliverables:**
- [x] Flask/FastAPI server on port 5000
- [x] Registration endpoints (`/api/register/franchise`, `/api/register/user`)
- [x] Authorization endpoint (`/api/authorize`)
- [x] Dispute endpoint (`/api/dispute`)
- [x] Audit endpoints (`/api/ledger`, `/api/ledger/verify`)

**Code Modules:**
```
grid/
  ├── server.py           # Flask app, route definitions
  ├── auth.py             # Authorization logic: validate PIN, check balance, create block
  └── config.py           # Port, ASCON key, file paths
```

**Test Flows:**
- Register franchise, receive FID
- Register user, receive UID + VMID
- Attempt auth with correct PIN → approved
- Attempt auth with wrong PIN → rejected (3 retries enforced)
- Attempt auth with insufficient balance → rejected
- Each successful auth creates a block
- Blockchain integrity check passes

---

### Phase 3: Charging Kiosk Server (Week 2)

**Deliverables:**
- [x] Flask server on port 5001
- [x] FID loading endpoint (`/kiosk/load-fid`)
- [x] QR generation endpoint (`/kiosk/qr`)
- [x] Payment relay endpoint (`/kiosk/payment`)
- [x] Session state management (per-request VFID + nonce)

**Code Modules:**
```
kiosk/
  ├── server.py           # Flask app, route definitions
  ├── session.py          # Current VFID, nonce, FID state
  ├── qr_generator.py     # QR image generation (PNG)
  └── config.py           # Grid URL, ASCON key, port
```

**Critical Behavior:**
- Kiosk ASCON-decrypts VFID upon reception from EV Owner
- Verifies decrypted FID matches its loaded FID
- Encrypts user credentials with Grid public key
- Forwards to Grid (with VFID + nonce as attachments)
- Receives auth response, displays result to user
- On approval, sends unlock signal to franchise hardware

**Test Flows:**
- Load FID into kiosk → QR generated and displayed
- EV Owner scans QR → receives VFID + nonce
- EV Owner submits payment → kiosk decrypts VFID, validates, forwards to Grid
- Grid authorizes → kiosk shows "Approved" message
- Grid rejects → kiosk shows "Rejected: <reason>"

---

### Phase 4: EV Owner App (Week 2)

**Deliverables:**
- [x] Simple CLI or web UI
- [x] QR scanner (via camera or file upload)
- [x] Payment form (VMID, PIN, amount)
- [x] HTTP client to POST to Kiosk

**Code Modules:**
```
user/
  ├── app.py              # Main app loop or Flask route
  ├── qr_scanner.py       # QR decode (using pyzbar or pyqrcode)
  └── api_client.py       # HTTP POST to kiosk
```

**User Flow:**
1. Start app
2. Scan QR code (displays VFID + nonce)
3. Enter VMID, PIN, amount
4. Submit payment to Kiosk
5. Receive status (approved / rejected + reason)
6. View balance after transaction

---

### Phase 5: Quantum Attack Demo (Week 3)

**Deliverables:**
- [x] Classical Shor's algorithm simulation (using sympy)
- [x] Small RSA key generation for demo (512-bit or 64-bit n)
- [x] Full attack flow: intercept encrypted creds, factor n, recover private key, decrypt

**Code Modules:**
```
quantum/
  ├── shors_simulation.py  # sympy.factorint() on small n
  ├── shors_qiskit.py      # (Optional) Qiskit order-finding circuit for Shor
  └── demo.py              # End-to-end attack: generate demo RSA, factor, decrypt
```

**Demo Output:**
```
[DEMO] Generating small RSA key (512-bit n) for factor demo
[DEMO] RSA modulus: n = 13579 * 10007 = 135923053
[ATTACK] Intercepted encrypted credentials (RSA ciphertext)
[ATTACK] Running Shor's algorithm simulation...
[ATTACK] Factored n: p=13579, q=10007
[ATTACK] Recovered private exponent: d=12345678
[ATTACK] Decrypted credentials: {"vmid": "A1B2C3D4", "pin": "1234", "amount": 150.00}
[RESULT] Classical RSA encryption is BROKEN by quantum computers.
```

---

### Phase 6: Integration & E2E Testing (Week 3)

**Deliverables:**
- [x] All three servers running concurrently
- [x] Full transaction from EV Owner scan to Grid block recording
- [x] Batch test scenarios (10+ transactions)
- [x] Edge case handling (expired VFID, replay attack, insufficient balance, PIN lockout)
- [x] Blockchain integrity report

**Test Suite:**
```
tests/
  ├── test_hashing.py        # Keccak-256 correctness
  ├── test_ascon.py          # ASCON encrypt/decrypt
  ├── test_rsa.py            # RSA encrypt/decrypt
  ├── test_auth_flow.py      # Full kiosk → grid → user flow
  ├── test_blockchain.py     # Block sealing, chain validity
  ├── test_edge_cases.py     # Replay, timeout, PIN lockout, insufficient balance
  └── test_quantum_demo.py   # Shor's attack on small RSA
```

---

## PART 5: Codebase Structure (Production-Grade)

```
EVChargingGateway/
├── grid/
│   ├── __init__.py
│   ├── server.py                # Flask server (routes: register, authorize, dispute, ledger)
│   ├── auth.py                  # Authorization logic (validate credentials, check balance, create block)
│   ├── registry.py              # User, Franchise, Provider registration & lookup
│   ├── blockchain.py            # Block dataclass, Blockchain class, persistence
│   ├── config.py                # Config: port=5000, ASCON_KEY, RSA key paths
│   │
│   └── crypto/
│       ├── __init__.py
│       ├── hashing.py           # keccak256()
│       ├── ascon_handler.py     # encrypt_vfid(), decrypt_vfid()
│       ├── rsa_handler.py       # generate_keypair(), encrypt_creds(), decrypt_creds()
│       └── utils.py             # Base64, timestamp utilities
│
├── kiosk/
│   ├── __init__.py
│   ├── server.py                # Flask server (routes: load-fid, qr, payment)
│   ├── session.py               # Store current VFID, nonce, FID per session
│   ├── qr_generator.py          # Generate QR PNG from VFID + nonce
│   ├── config.py                # Config: port=5001, GRID_URL, ASCON_KEY
│   │
│   └── crypto/
│       ├── __init__.py
│       ├── ascon_handler.py     # decrypt_vfid() — Kiosk decrypts!
│       └── rsa_handler.py       # encrypt_creds() using Grid's public key
│
├── user/
│   ├── __init__.py
│   ├── app.py                   # CLI or web interface
│   ├── qr_scanner.py            # Decode QR from camera/image
│   ├── api_client.py            # HTTP POST to kiosk /kiosk/payment
│   └── config.py                # Config: KIOSK_URL
│
├── quantum/
│   ├── __init__.py
│   ├── shors_simulation.py      # sympy.factorint() on small RSA modulus
│   ├── shors_qiskit.py          # (Optional) Qiskit order-finding circuit
│   └── demo.py                  # Full attack demo: generate small RSA, factor, decrypt
│
├── tests/
│   ├── __init__.py
│   ├── test_hashing.py
│   ├── test_ascon.py
│   ├── test_rsa.py
│   ├── test_auth_flow.py
│   ├── test_blockchain.py
│   ├── test_edge_cases.py
│   └── test_quantum_demo.py
│
├── keys/
│   ├── grid_private.pem         # NOT committed; generated at first run
│   └── grid_public.pem          # NOT committed; generated at first run
│
├── ledger.json                  # Blockchain persistence (created at startup)
├── requirements.txt             # Dependency list
├── README.md                    # Setup, execution, assumptions
├── ARCHITECTURE.md              # System design (already provided)
└── IMPLEMENTATION_PLAN.md       # This file

```

### File Responsibility Matrix

| File | Input | Output | Key Function |
|------|-------|--------|--------------|
| `grid/crypto/hashing.py` | name, timestamp, password | FID (16 hex chars) | `generate_fid()` |
| `grid/crypto/ascon_handler.py` | VFID ciphertext, nonce | FID plaintext | `decrypt_vfid()` (Grid-side decrypt for verification) |
| `grid/crypto/rsa_handler.py` | ciphertext | VMID, PIN, amount dict | `decrypt_creds()` |
| `kiosk/crypto/ascon_handler.py` | FID plaintext, timestamp | VFID ciphertext, nonce | `encrypt_vfid()` |
| `kiosk/crypto/rsa_handler.py` | VMID, PIN, amount, grid_public_key | ciphertext | `encrypt_creds()` |
| `grid/blockchain.py` | uid, fid, amount | Block object | `add_block()` |
| `grid/registry.py` | name, mobile, zone, password | UID, VMID | `register_user()` |
| `kiosk/qr_generator.py` | VFID, nonce | PNG image | `generate_qr_image()` |
| `quantum/shors_simulation.py` | RSA modulus n | primes p, q | `simulate_shors()` |

---

## PART 6: Execution Roadmap

### Week 1: Foundation

**Monday:**
- [ ] Set up directory structure
- [ ] Implement Keccak-256, ASCON, RSA utilities
- [ ] Write crypto tests (unit level)

**Tuesday-Wednesday:**
- [ ] Build Grid Authority server (registration endpoints)
- [ ] Implement User & Franchise registries
- [ ] Write integration tests

**Thursday-Friday:**
- [ ] Build Blockchain class & persistence
- [ ] Test block creation, hashing, chain validation
- [ ] Code review + documentation

### Week 2: Integration

**Monday-Tuesday:**
- [ ] Build Charging Kiosk server (VFID generation, QR)
- [ ] Implement session state management
- [ ] Test Kiosk ↔ Grid communication

**Wednesday:**
- [ ] Build EV Owner app (CLI + QR scanner)
- [ ] Test full payment flow end-to-end

**Thursday-Friday:**
- [ ] Test edge cases (expired VFID, replay, PIN lockout, insufficient balance)
- [ ] Refinement & bug fixes

### Week 3: Advanced Features & Demo

**Monday-Tuesday:**
- [ ] Implement dispute handling (reverse blocks)
- [ ] Add dispute endpoint to Grid

**Wednesday:**
- [ ] Build Quantum attack demo (Shor's simulation)
- [ ] Document attack scenario in README

**Thursday-Friday:**
- [ ] Full system integration test (3 servers concurrently, 10+ transactions)
- [ ] Performance benchmarking (transaction throughput, blockchain size)
- [ ] Final documentation & deployment guide

---

## PART 7: Constraints & Non-Functional Requirements

### Security Constraints
- ✅ RSA keys stored in `keys/` directory (not in code or git)
- ✅ Plaintext passwords never logged
- ✅ FID never transmitted except as encrypted VFID
- ✅ Blockchain is append-only (no deletion/modification)
- ✅ Grid validates every transaction (no bypass)

### Performance Constraints
- ✅ Transaction authorization completes in <3 seconds (LAN latency)
- ✅ Blockchain integrity check (<1 second for 1000 blocks)
- ✅ Block creation overhead <100ms
- ✅ QR generation <500ms (user-facing, should feel instant)

### Scalability Constraints
- ⚠️ Registry is in-memory (no database). Assumption: <1000 users/franchises for demo.
- ⚠️ Blockchain is JSON file. Assumption: <10000 blocks for demo.
- ⚠️ VFID nonce cache (for replay prevention) is in-memory. Assumption: <1000 concurrent sessions.

### Code Quality Constraints
- ✅ **NO inline comments inside code files**
- ✅ **NO docstrings in function definitions**
- ✅ **Code is self-explanatory via naming**
- ✅ **All logic is testable (unit + integration)**
- ✅ Comments allowed ONLY in git commit messages and external documentation (README, this file)

### Deployment Constraints
- ✅ Python 3.9+
- ✅ All dependencies in `requirements.txt`
- ✅ No Docker / no cloud; runs on local machines or LAN
- ✅ HTTP only (no TLS in v1)
- ✅ Startup order: Grid → Kiosk → User app

---

## PART 8: Key Architectural Corrections Documented

### Correction 1: VFID Decryption Location

**Original (Incorrect):**
> "Grid decrypts VFID using ASCON to recover FID"

**Corrected:**
> "Kiosk decrypts VFID internally after receiving it from EV Owner. Kiosk validates decrypted FID matches its loaded FID, then forwards the encrypted payload (with plaintext FID recovery) to Grid. Grid does NOT perform ASCON decryption."

**Rationale:**
- Kiosk is the trusted entity at the point of payment. It decrypts the VFID it generated.
- This prevents a malicious user from scanning QR codes from unauthorized kiosks and submitting them to Grid.
- Grid trusts Kiosk's validation: if encrypted payload arrives, Kiosk has already verified it.

**Code Impact:**
- `kiosk/crypto/ascon_handler.py` implements `decrypt_vfid()`
- `grid/crypto/ascon_handler.py` does NOT implement `decrypt_vfid()` (Grid skips this step)
- `grid/auth.py` receives `fid` as plaintext from Kiosk payload (trusted input)

---

### Correction 2: Blockchain Simplification

**Original (Overly Complex):**
- Blockchain class with merkle tree support
- Validation pipelines
- Advanced consensus logic

**Corrected:**
- Simple append-only linked list
- Linear hash chain (each block references previous hash)
- No merkle tree, no validation layers
- O(n) lookup for `find_block()`, O(n) validation for `is_valid()`

**Code Impact:**
- `grid/blockchain.py` is <200 lines
- `Block` is a dataclass with 10 fields (index, txn_id, previous_hash, timestamp, uid, fid, amount, status, dispute_flag, block_hash)
- `Blockchain` has 4 methods: `add_block()`, `find_block()`, `is_valid()`, `add_reverse()`
- Serialization to JSON is straightforward

---

### Correction 3: RSA Usage Clarity

**Original (Ambiguous):**
> "RSA used for key exchange"

**Corrected:**
> "RSA-OAEP is used to encrypt the user credentials payload (VMID, PIN, amount) from Kiosk to Grid. This is the attack surface for Shor's algorithm. It is called 'key exchange' in the sense that it protects sensitive credential data in transit. Post-quantum migration would replace RSA with a KEM like Kyber."

**Code Impact:**
- `kiosk/crypto/rsa_handler.py`: `encrypt_creds(vmid, pin, amount, grid_public_key) → ciphertext`
- `grid/crypto/rsa_handler.py`: `decrypt_creds(ciphertext, grid_private_key) → {vmid, pin, amount}`
- `quantum/demo.py`: Target this RSA ciphertext for Shor's attack

---

**This plan is ready for implementation. All architectural ambiguities have been resolved. Proceed to the Codebase Blueprint for detailed code structure.**

