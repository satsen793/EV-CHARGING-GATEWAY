# Secure Centralized EV Charging Payment Gateway
## Architecture & Developer Guide

> **Project:** BITSF463 — Secure Centralized EV Charging Payment Gateway using Post-Quantum and Lightweight Cryptography
> **Version:** 1.0.0
> **Audience:** Developers implementing the system from scratch

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Entity Definitions](#3-entity-definitions)
4. [Data Models](#4-data-models)
5. [Cryptographic Subsystems](#5-cryptographic-subsystems)
6. [Blockchain Subsystem](#6-blockchain-subsystem)
7. [Transaction Flow (End-to-End)](#7-transaction-flow-end-to-end)
8. [API / Communication Contracts](#8-api--communication-contracts)
9. [Module Breakdown](#9-module-breakdown)
10. [Edge Cases & Assumptions](#10-edge-cases--assumptions)
11. [Security Threat Model](#11-security-threat-model)
12. [Project Directory Structure](#12-project-directory-structure)
13. [Glossary](#13-glossary)

---

## 1. System Overview

The **Secure Centralized EV Charging Payment Gateway** simulates a complete digital transaction ecosystem for purchasing EV charging time. It demonstrates how three distinct security technologies — Lightweight Cryptography (LWC), classical cryptography (RSA), and Quantum Cryptography — interact and where classical approaches break down.

### Goals

- Simulate real-world EV charging station payment flows across three physical-device roles.
- Implement **ASCON** (LWC) to protect station identity data on resource-constrained kiosk hardware.
- Implement **RSA** for the initial credential key exchange, then use **Shor's Algorithm** to demonstrate its vulnerability.
- Record every verified transaction on a **centralized blockchain ledger** with SHA-3 hashed blocks.

### What This System Is NOT

- It is **not** a decentralized blockchain (no mining, no consensus between nodes).
- It is **not** a real payment processor — balances are simulated integers.
- It is **not** a production IoT system — LWC is simulated in software.

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SYSTEM TOPOLOGY                                   │
│                                                                             │
│   ┌──────────────────┐         ┌──────────────────────┐                    │
│   │   EV Owner       │         │   Charging Kiosk     │                    │
│   │   Device         │◄───────►│   (Intermediary)     │◄──────────────────►│
│   │  (User App)      │ Scan QR │                      │  Auth Request/     │
│   │                  │ Submit  │  - ASCON Encrypt FID │  Response          │
│   │  - VMID          │ Payment │  - Generate QR Code  │                    │
│   │  - PIN           │         │  - Relay Txns        │  ┌─────────────────┤
│   │  - Amount        │◄────────│  - Notify user       │  │  Grid Authority  │
│   └──────────────────┘ Status  └──────────────────────┘  │  Laptop          │
│                                          │  Unlock        │                  │
│                                          ▼                │  - Validate VMID │
│                                 ┌────────────────┐        │  - Validate PIN  │
│                                 │   Franchise    │        │  - Check Balance │
│                                 │   Hardware     │        │  - Record Block  │
│                                 │   (Cable Lock) │        │  - Transfer Funds│
│                                 └────────────────┘        └─────────────────┤
│                                                                    │         │
│                                                           ┌────────▼───────┐ │
│                                                           │  Blockchain    │ │
│                                                           │  Ledger        │ │
│                                                           │  (In-Memory /  │ │
│                                                           │   File)        │ │
│                                                           └────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Device-to-Role Mapping

| Physical Device | Logical Role | Primary Responsibilities |
|---|---|---|
| Student Laptop A | **Charging Kiosk** | ASCON encryption, QR generation, relay |
| Student Laptop B | **Grid Authority** | Validation, blockchain, fund transfer |
| Student Phone / Laptop C | **EV Owner Device** | VMID creation, QR scan, PIN submission |

Communication between devices is over a **local network (LAN/loopback)**. Use plain HTTP or WebSockets for the demo — TLS is not required but may be added.

---

## 3. Entity Definitions

### 3.1 Grid Authority

The single authoritative server in the system. Think of it as a bank + identity registry + ledger.

**State it owns:**
- Registry of all Energy Providers and their Zones
- Registry of all Franchises (`FID → FranchiseRecord`)
- Registry of all EV Owners (`UID → UserRecord`)
- Blockchain ledger

**Operations:**
- `registerFranchise(name, zone, password, initialBalance) → FID`
- `registerUser(name, zone, password, pin, mobile) → UID`
- `authorizeTransaction(encryptedPayload) → AuthResponse`
- `getBlock(txnId) → Block`
- `addReverseBlock(txnId, reason) → Block`

### 3.2 Franchise

A business entity. Registers once with the Grid and then operates a physical kiosk.

**State it owns:**
- Its own FID (kept private, never shared)
- Zone code
- Account balance (managed by Grid)

**Operations:**
- `enterFIDIntoKiosk(fid)` — triggers QR generation
- `receiveUnlockSignal()` — physically releases charging cable

### 3.3 EV Owner

A registered user who initiates charging sessions.

**State it owns:**
- UID
- Mobile number
- VMID (derived from UID + mobile)
- PIN

**Operations:**
- `scanQRCode() → encryptedVFID`
- `submitPayment(vmid, pin, amount, encryptedVFID) → sessionToken`

### 3.4 Charging Kiosk

The intermediary hardware device. It never stores the FID after generating the VFID. It is stateless between sessions.

**State it owns (per-session):**
- Current VFID (ephemeral, cleared after session)
- Session status

**Operations:**
- `loadFID(fid)` — called once by franchise owner
- `generateVFID(fid, timestamp) → vfid` — using ASCON
- `generateQRCode(vfid) → qrImage`
- `forwardAuthRequest(payload) → authResponse`
- `notifyUser(status)`
- `unlockFranchise(signal)`

---

## 4. Data Models

### 4.1 Energy Provider

```json
{
  "providerName": "Tata Power",
  "zones": [
    { "zoneCode": "TP-NORTH-01", "region": "North Delhi" },
    { "zoneCode": "TP-SOUTH-02", "region": "South Delhi" },
    { "zoneCode": "TP-WEST-03",  "region": "West Delhi" }
  ]
}
```

There are exactly **3 providers**, each with **3 zones**. Zone codes are globally unique strings.

### 4.2 Franchise Record

```json
{
  "fid":          "A3F2C1D4E5B60789",
  "name":         "SparkCharge Pvt Ltd",
  "zoneCode":     "TP-NORTH-01",
  "passwordHash": "<sha3-256 of password>",
  "balance":      5000.00,
  "createdAt":    "2025-04-11T10:00:00Z"
}
```

**FID Generation Algorithm:**

```
raw_input  = franchise_name + created_at_iso + password
keccak_256 = SHA3-Keccak256(raw_input)         // 32 bytes = 64 hex chars
fid        = keccak_256[0:16].upper()           // First 16 hex chars
```

> ⚠️ The Python `hashlib.sha3_256` is NOT the same as Keccak-256. Use the `pysha3` or `pycryptodome` library for true Keccak-256 (pre-NIST SHA-3). Confirm with your specification which variant is intended.

### 4.3 User Record

```json
{
  "uid":          "C9D8E7F6A5B41234",
  "name":         "Arjun Sharma",
  "mobile":       "9876543210",
  "zoneCode":     "TP-NORTH-01",
  "passwordHash": "<sha3-256 of password>",
  "pinHash":      "<sha3-256 of pin>",
  "balance":      2000.00,
  "createdAt":    "2025-04-11T10:05:00Z",
  "vmid":         "<derived — see below>"
}
```

**UID Generation:** Same algorithm as FID but using user's name, creation timestamp, and password.

**VMID Derivation:**

```
raw_input = uid + mobile_number
vmid      = Keccak256(raw_input)[0:16].upper()
```

The VMID is the primary identifier the user presents at a kiosk. It abstracts the UID so the user does not expose their UID in public.

### 4.4 Virtual Franchise ID (VFID)

The VFID is a dynamic, time-bound token derived from the FID. It is what gets embedded in the QR code.

```
vfid = ASCON_Encrypt(
    plaintext  = fid,
    key        = kiosk_session_key,    // 128-bit secret, pre-shared with Grid
    nonce      = timestamp_bytes       // 96-bit nonce derived from Unix timestamp
)
```

The Grid can recover FID by calling `ASCON_Decrypt(vfid, key, nonce)`. The nonce/timestamp is transmitted alongside the VFID so the Grid can reproduce it.

**VFID Validity Window:** ±5 minutes from creation timestamp. Reject replayed QR codes.

### 4.5 Transaction Block

```json
{
  "blockIndex":     42,
  "txnId":          "E3A2...F901",
  "previousHash":   "0000...0000",
  "timestamp":      "2025-04-11T10:15:00Z",
  "uid":            "C9D8E7F6A5B41234",
  "fid":            "A3F2C1D4E5B60789",
  "amount":         150.00,
  "status":         "SUCCESS",
  "disputeFlag":    false,
  "blockHash":      "<SHA3 of all above fields>"
}
```

**Transaction ID:**

```
txnId = SHA3-256(uid + fid + timestamp_iso + amount_string)
```

**Block Hash:**

```
blockHash = SHA3-256(blockIndex + txnId + previousHash + timestamp + uid + fid + amount + status + disputeFlag)
```

### 4.6 Auth Request Payload (Kiosk → Grid)

```json
{
  "encryptedCredentials": "<RSA-OAEP encrypted blob>",
  "vfid":                 "<ASCON ciphertext hex>",
  "vfidNonce":            "<nonce hex>",
  "vfidTimestamp":        "2025-04-11T10:14:55Z"
}
```

The `encryptedCredentials` blob, when decrypted by Grid's RSA private key, yields:

```json
{
  "vmid":   "...",
  "pin":    "...",
  "amount": 150.00
}
```

> This RSA encryption is the attack vector for Shor's Algorithm (see Section 5.3).

### 4.7 Auth Response (Grid → Kiosk)

```json
{
  "approved":   true,
  "txnId":      "E3A2...F901",
  "message":    "Transaction approved. Charging authorized.",
  "balance":    1850.00
}
```

---

## 5. Cryptographic Subsystems

### 5.1 SHA-3 / Keccak-256 — Identity Hashing

**Used for:** FID generation, UID generation, VMID derivation, block hashing, txnId.

```python
# Use pycryptodome: pip install pycryptodome
from Crypto.Hash import keccak

def keccak256(data: str) -> str:
    k = keccak.new(digest_bits=256)
    k.update(data.encode('utf-8'))
    return k.hexdigest()

def generate_fid(name: str, created_at: str, password: str) -> str:
    raw = name + created_at + password
    return keccak256(raw)[:16].upper()
```

### 5.2 ASCON — Lightweight Cryptography (LWC)

**Used for:** Encrypting FID → VFID on the Kiosk; embedding in QR code.

ASCON is an authenticated encryption algorithm (AEAD). It produces a ciphertext + authentication tag, so decryption also verifies integrity.

**Parameters:**
- Variant: `ASCON-128`
- Key length: 128 bits (16 bytes)
- Nonce length: 128 bits (16 bytes)
- Tag length: 128 bits (16 bytes)

```python
# pip install ascon
import ascon
import time, struct

KIOSK_ASCON_KEY = bytes.fromhex("00112233445566778899aabbccddeeff")  # Pre-shared 16-byte key

def generate_vfid(fid: str) -> tuple[bytes, bytes]:
    """Returns (ciphertext+tag, nonce)"""
    timestamp = int(time.time())
    nonce = struct.pack(">Q", timestamp).ljust(16, b'\x00')   # 16-byte nonce
    plaintext = fid.encode('ascii')                           # FID is 16 hex chars = 16 bytes
    associated_data = b"EV-KIOSK-V1"                         # Binding context
    ciphertext = ascon.encrypt(KIOSK_ASCON_KEY, nonce, associated_data, plaintext, variant="Ascon-128")
    return ciphertext, nonce

def decrypt_vfid(ciphertext: bytes, nonce: bytes) -> str:
    associated_data = b"EV-KIOSK-V1"
    plaintext = ascon.decrypt(KIOSK_ASCON_KEY, nonce, associated_data, ciphertext, variant="Ascon-128")
    return plaintext.decode('ascii')
```

**VFID Replay Prevention:**
```python
def is_vfid_fresh(nonce: bytes, tolerance_seconds: int = 300) -> bool:
    ts = struct.unpack(">Q", nonce[:8])[0]
    return abs(time.time() - ts) < tolerance_seconds
```

**QR Code Generation:**
```python
# pip install qrcode[pil]
import qrcode, json, base64

def generate_qr(ciphertext: bytes, nonce: bytes) -> Image:
    payload = json.dumps({
        "vfid": base64.b64encode(ciphertext).decode(),
        "nonce": base64.b64encode(nonce).decode()
    })
    return qrcode.make(payload)
```

### 5.3 RSA — Classical Key Exchange (Vulnerable)

**Used for:** Encrypting the EV Owner's credentials (VMID, PIN, amount) before transmission from Kiosk to Grid.

This is intentionally **insecure at the quantum level** — it is the attack surface for Shor's Algorithm.

```python
# pip install pycryptodome
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
import json

# Grid generates key pair once at startup
def generate_grid_keypair():
    key = RSA.generate(2048)
    return key.export_key(), key.publickey().export_key()

# Kiosk encrypts credentials using Grid's public key
def encrypt_credentials(public_key_pem: bytes, vmid: str, pin: str, amount: float) -> bytes:
    key = RSA.import_key(public_key_pem)
    cipher = PKCS1_OAEP.new(key)
    payload = json.dumps({"vmid": vmid, "pin": pin, "amount": amount}).encode()
    return cipher.encrypt(payload)

# Grid decrypts with private key
def decrypt_credentials(private_key_pem: bytes, ciphertext: bytes) -> dict:
    key = RSA.import_key(private_key_pem)
    cipher = PKCS1_OAEP.new(key)
    payload = cipher.decrypt(ciphertext)
    return json.loads(payload)
```

### 5.4 Shor's Algorithm Simulation — Quantum Attack

**Purpose:** Demonstrate that RSA-2048 is broken by a sufficiently large quantum computer. This is a **simulation** using classical computation on small key sizes.

**Approach:** Use `qiskit` or `sympy` to factor the RSA modulus `n = p * q`. On real quantum hardware with enough qubits, this breaks RSA. For demo, use a small RSA key (e.g., 32-bit or 64-bit `n`).

```python
# pip install qiskit qiskit-aer sympy
# NOTE: Use a tiny RSA key for demo — real 2048-bit factoring is not feasible classically

from sympy import factorint
from Crypto.PublicKey import RSA

def simulate_shors_attack_classical(n: int) -> tuple[int, int]:
    """
    Classical simulation of Shor's period-finding output.
    For demo: factor a small n to show the principle.
    """
    factors = factorint(n)
    primes = list(factors.keys())
    if len(primes) == 2:
        return primes[0], primes[1]
    raise ValueError("n is not a product of two primes")

def demo_quantum_vulnerability():
    # Generate a small (demo) RSA key
    small_key = RSA.generate(512)   # 512-bit — factorable in reasonable time for demo
    n = small_key.n
    print(f"[ATTACK] RSA modulus n = {n}")
    print(f"[ATTACK] Attempting to factor n using Shor's algorithm simulation...")
    p, q = simulate_shors_attack_classical(n)
    print(f"[ATTACK] Factored! p = {p}, q = {q}")
    print(f"[ATTACK] RSA private key is now recoverable. Classical crypto BROKEN.")
    return p, q
```

For a **Qiskit circuit-level** simulation of Shor's order-finding, refer to the [Qiskit Shor tutorial](https://qiskit.org/textbook/ch-algorithms/shor.html). Implement at minimum the period-finding circuit for small `n` (e.g., n=15 or n=21).

---

## 6. Blockchain Subsystem

### 6.1 Overview

The blockchain is a **centralized append-only linked list of blocks**, maintained solely by the Grid Authority. It is not distributed. Its purpose is immutability and auditability of transaction records.

### 6.2 Block Structure

```python
import hashlib, json
from dataclasses import dataclass, field
from datetime import datetime, timezone

@dataclass
class Block:
    index:          int
    txn_id:         str
    previous_hash:  str
    timestamp:      str
    uid:            str
    fid:            str
    amount:         float
    status:         str          # "SUCCESS" | "REVERSED"
    dispute_flag:   bool = False
    block_hash:     str = field(default="", init=False)

    def compute_hash(self) -> str:
        content = json.dumps({
            "index":         self.index,
            "txn_id":        self.txn_id,
            "previous_hash": self.previous_hash,
            "timestamp":     self.timestamp,
            "uid":           self.uid,
            "fid":           self.fid,
            "amount":        self.amount,
            "status":        self.status,
            "dispute_flag":  self.dispute_flag
        }, sort_keys=True)
        return hashlib.sha3_256(content.encode()).hexdigest()

    def seal(self):
        self.block_hash = self.compute_hash()
```

### 6.3 Blockchain Class

```python
class Blockchain:
    def __init__(self):
        self.chain: list[Block] = []
        self._add_genesis_block()

    def _add_genesis_block(self):
        genesis = Block(
            index=0, txn_id="GENESIS", previous_hash="0"*64,
            timestamp=datetime.now(timezone.utc).isoformat(),
            uid="SYSTEM", fid="SYSTEM", amount=0.0, status="GENESIS"
        )
        genesis.seal()
        self.chain.append(genesis)

    def add_transaction(self, uid, fid, amount, status="SUCCESS") -> Block:
        prev = self.chain[-1]
        timestamp = datetime.now(timezone.utc).isoformat()
        txn_id = hashlib.sha3_256(
            (uid + fid + timestamp + str(amount)).encode()
        ).hexdigest()
        block = Block(
            index=len(self.chain),
            txn_id=txn_id,
            previous_hash=prev.block_hash,
            timestamp=timestamp,
            uid=uid,
            fid=fid,
            amount=amount,
            status=status
        )
        block.seal()
        self.chain.append(block)
        return block

    def add_reverse_block(self, original_txn_id: str, reason: str) -> Block:
        original = self.find_block(original_txn_id)
        if not original:
            raise ValueError("Original transaction not found")
        reverse_block = self.add_transaction(
            uid=original.uid,
            fid=original.fid,
            amount=-original.amount,
            status="REVERSED"
        )
        reverse_block.dispute_flag = True
        reverse_block.seal()  # Re-seal after setting dispute_flag
        return reverse_block

    def is_valid(self) -> bool:
        for i in range(1, len(self.chain)):
            cur, prev = self.chain[i], self.chain[i-1]
            if cur.block_hash != cur.compute_hash():
                return False
            if cur.previous_hash != prev.block_hash:
                return False
        return True

    def find_block(self, txn_id: str) -> Block | None:
        return next((b for b in self.chain if b.txn_id == txn_id), None)
```

### 6.4 Persistence

Serialize the blockchain to a JSON file after every new block:

```python
import json

def save_chain(blockchain: Blockchain, path: str = "ledger.json"):
    with open(path, "w") as f:
        json.dump([vars(b) for b in blockchain.chain], f, indent=2)

def load_chain(path: str = "ledger.json") -> Blockchain:
    bc = Blockchain()
    bc.chain = []   # Clear genesis
    with open(path) as f:
        blocks_data = json.load(f)
    for bd in blocks_data:
        b = Block(**{k: v for k, v in bd.items() if k != "block_hash"})
        b.block_hash = bd["block_hash"]
        bc.chain.append(b)
    return bc
```

---

## 7. Transaction Flow (End-to-End)

### Phase 0: Registration (One-Time Setup)

```
Grid Admin                Grid Authority Server
    │                            │
    ├──── registerProvider() ────►│  Creates 3 providers × 3 zones each
    │                            │
    ├──── registerFranchise() ───►│  FID = Keccak256(name+time+pass)[:16]
    │◄─── FID returned ──────────┤
    │                            │
    ├──── registerUser() ────────►│  UID = Keccak256(name+time+pass)[:16]
    │                            │  VMID = Keccak256(UID+mobile)[:16]
    │◄─── UID + VMID returned ───┤
```

### Phase 1: Kiosk Activation (Franchise enters FID)

```
Franchise             Charging Kiosk
    │                       │
    ├── enter FID ──────────►│
    │                       │  timestamp = now()
    │                       │  nonce = pack(timestamp)
    │                       │  vfid = ASCON_Encrypt(FID, key, nonce)
    │                       │  qr_image = QRCode(vfid + nonce)
    │                       │  display qr_image on screen
    │◄── QR displayed ──────┤
```

### Phase 2: Payment Initiation (EV Owner scans QR)

```
EV Owner Device        Charging Kiosk          Grid Authority
    │                       │                        │
    ├── scan QR ────────────►│                        │
    │◄── vfid + nonce ───────┤                        │
    │                       │                        │
    │  user enters:          │                        │
    │  vmid, pin, amount     │                        │
    │                       │                        │
    │  creds = RSA_Encrypt(  │                        │
    │    {vmid,pin,amount},  │                        │
    │    grid_public_key     │                        │
    │  )                     │                        │
    │                       │                        │
    ├── POST /authorize ────►│                        │
    │   {creds, vfid, nonce} │                        │
    │                       │                        │
    │                       ├── POST /grid/authorize ►│
    │                       │   {creds, vfid, nonce}  │
```

### Phase 3: Grid Validation & Blockchain Record

```
                         Grid Authority
                              │
                              │  fid = ASCON_Decrypt(vfid, nonce)
                              │  if not is_vfid_fresh(nonce): REJECT
                              │
                              │  {vmid, pin, amount} = RSA_Decrypt(creds)
                              │
                              │  user = lookup_by_vmid(vmid)
                              │  if not user: REJECT "Unknown VMID"
                              │
                              │  if not verify_pin(user, pin): REJECT "Bad PIN"
                              │
                              │  if user.balance < amount: REJECT "Insufficient"
                              │
                              │  // All checks passed:
                              │  user.balance -= amount
                              │  franchise.balance += amount
                              │
                              │  block = blockchain.add_transaction(
                              │    uid=user.uid, fid=fid, amount=amount
                              │  )
                              │
                              │  return AuthResponse(approved=True, txnId=block.txn_id)
```

### Phase 4: Kiosk Receives Response

```
Kiosk              EV Owner Device          Franchise Hardware
  │                       │                        │
  │  if approved:          │                        │
  ├── notify ─────────────►│ "Charging Approved!"   │
  ├── unlock signal ───────┼────────────────────────►│ releases cable
  │                       │                        │
  │  if rejected:          │                        │
  ├── notify ─────────────►│ "Payment Failed: <msg>"│
  │                       │                        │
```

### Phase 5: Edge Case — Hardware Failure After Payment

```
                         Grid Authority
                              │
                              │  Receives: HardwareFailureReport(txnId)
                              │
                              │  block = blockchain.find_block(txnId)
                              │  assert block.status == "SUCCESS"
                              │
                              │  reverse = blockchain.add_reverse_block(
                              │    txnId, reason="Hardware failure"
                              │  )
                              │  reverse.dispute_flag = True
                              │
                              │  user.balance += block.amount  // Refund
                              │  franchise.balance -= block.amount
                              │
                              │  return RefundConfirmation(reverse.txn_id)
```

---

## 8. API / Communication Contracts

All communication is JSON over HTTP. Base URLs are configurable via environment variables.

### 8.1 Grid Authority Endpoints

#### `POST /api/register/franchise`
```json
// Request
{
  "name":           "SparkCharge Pvt Ltd",
  "zoneCode":       "TP-NORTH-01",
  "password":       "securepass123",
  "initialBalance": 5000.00
}

// Response 200
{
  "fid": "A3F2C1D4E5B60789",
  "message": "Franchise registered successfully"
}
```

#### `POST /api/register/user`
```json
// Request
{
  "name":     "Arjun Sharma",
  "mobile":   "9876543210",
  "zoneCode": "TP-NORTH-01",
  "password": "mypassword",
  "pin":      "4821",
  "initialBalance": 2000.00
}

// Response 200
{
  "uid":  "C9D8E7F6A5B41234",
  "vmid": "1A2B3C4D5E6F7890",
  "message": "User registered successfully"
}
```

#### `POST /api/authorize`
```json
// Request (from Kiosk)
{
  "encryptedCredentials": "<base64-encoded RSA ciphertext>",
  "vfid":                 "<base64-encoded ASCON ciphertext>",
  "vfidNonce":            "<base64-encoded nonce>",
  "vfidTimestamp":        "2025-04-11T10:14:55Z"
}

// Response 200 — Approved
{
  "approved":    true,
  "txnId":       "e3a2f1...c901",
  "message":     "Transaction approved.",
  "userBalance": 1850.00
}

// Response 200 — Rejected
{
  "approved": false,
  "message":  "Insufficient balance"
}
```

#### `POST /api/dispute`
```json
// Request (from Kiosk on hardware failure)
{
  "txnId":  "e3a2f1...c901",
  "reason": "Cable lock failed to release"
}

// Response 200
{
  "refunded":       true,
  "reverseTxnId":   "bb99aa...1234",
  "refundAmount":   150.00
}
```

#### `GET /api/ledger`
Returns the full blockchain as a JSON array of blocks. Used by Grid Admin console for audit.

#### `GET /api/ledger/verify`
```json
// Response
{
  "valid": true,
  "chainLength": 42
}
```

### 8.2 Kiosk Endpoints

#### `POST /kiosk/load-fid`
Called by Franchise owner via a local admin UI.
```json
{ "fid": "A3F2C1D4E5B60789" }
```

#### `GET /kiosk/qr`
Returns the current QR code image (PNG) for display.

#### `POST /kiosk/payment`
Called by EV Owner device after scanning QR.
```json
{
  "vmid":   "1A2B3C4D5E6F7890",
  "pin":    "4821",
  "amount": 150.00
}
```
The Kiosk fetches the current VFID from its own state, encrypts credentials with Grid's public key, and forwards to Grid.

---

## 9. Module Breakdown

```
project/
├── grid/                        # Grid Authority Server
│   ├── server.py                #   Flask/FastAPI app, route handlers
│   ├── registry.py              #   Provider, Franchise, User registrations
│   ├── auth.py                  #   Authorization logic
│   ├── crypto/
│   │   ├── hashing.py           #   Keccak-256, SHA-3 utilities
│   │   ├── rsa_handler.py       #   RSA key generation, decryption
│   │   └── ascon_handler.py     #   ASCON decrypt (for VFID)
│   ├── blockchain/
│   │   ├── block.py             #   Block dataclass
│   │   ├── chain.py             #   Blockchain class
│   │   └── persistence.py       #   save/load ledger.json
│   └── config.py                #   Port, key paths, etc.
│
├── kiosk/                       # Charging Kiosk Server
│   ├── server.py                #   Flask/FastAPI app
│   ├── qr_generator.py          #   QR code generation
│   ├── session.py               #   Per-session VFID state
│   ├── crypto/
│   │   ├── ascon_handler.py     #   ASCON encrypt (FID → VFID)
│   │   └── rsa_handler.py       #   RSA encrypt (credentials)
│   └── config.py                #   Grid URL, ASCON key, etc.
│
├── user/                        # EV Owner Device App
│   ├── app.py                   #   CLI or simple web UI
│   ├── qr_scanner.py            #   Decode QR from camera or file
│   └── api_client.py            #   POST to /kiosk/payment
│
├── quantum/                     # Shor's Algorithm Demo
│   ├── shors_simulation.py      #   Classical sympy factoring demo
│   ├── shors_qiskit.py          #   Qiskit circuit (optional, small n)
│   └── demo.py                  #   End-to-end attack demo script
│
├── tests/
│   ├── test_hashing.py
│   ├── test_ascon.py
│   ├── test_blockchain.py
│   ├── test_auth_flow.py
│   └── test_edge_cases.py
│
├── ledger.json                  # Blockchain persistence file
├── keys/
│   ├── grid_private.pem
│   └── grid_public.pem
├── requirements.txt
└── README.md
```

### Key Dependencies (`requirements.txt`)

```
flask>=3.0
requests>=2.31
pycryptodome>=3.20       # Keccak-256, RSA, AES
ascon>=1.0               # ASCON lightweight crypto
qrcode[pil]>=7.4         # QR code generation
Pillow>=10.0             # Image handling
sympy>=1.12              # Classical Shor simulation
qiskit>=1.0              # (Optional) Quantum circuit simulation
qiskit-aer>=0.13         # (Optional) Qiskit simulator backend
pytest>=8.0              # Testing
```

---

## 10. Edge Cases & Assumptions

The following edge cases must be handled. Document your assumptions in the README.

| Scenario | Handling |
|---|---|
| **Insufficient balance** | Grid returns `approved: false, message: "Insufficient balance"`. No block is written. No funds moved. |
| **Wrong PIN (≤3 attempts)** | Grid tracks failed attempts per UID per session. After 3 failures, lock the UID for 15 minutes (or until manual reset). |
| **VFID expired (>5 min old)** | Grid rejects with `"QR code expired. Please refresh the kiosk."` Kiosk regenerates VFID. |
| **VFID replay attack** | Grid maintains a set of recently used nonces. Reject any nonce seen in the past 10 minutes. |
| **Hardware failure post-payment** | Kiosk sends a `POST /api/dispute` with txnId. Grid creates reverse block, refunds user. |
| **Account closed mid-session** | If Grid cannot find the UID during auth, reject. No partial processing. |
| **Franchise balance check** | Assumption: Franchise balance represents receivables and has no upper limit. No check needed. |
| **Network timeout** | Kiosk waits 10 seconds. If no Grid response, show error: `"Server unreachable. Try again."` No funds deducted (no request was authorized). |
| **Double submission** | If a nonce is reused (same VFID submitted twice), reject as replay. |
| **Blockchain corruption** | `GET /api/ledger/verify` runs chain integrity check. If invalid, alert admin — do not add new blocks. |
| **Zone mismatch** | No cross-zone restrictions in v1. A user in zone TP-NORTH-01 can charge at a franchise in TP-SOUTH-02. |
| **Negative amount** | Reject at Kiosk before forwarding. Amount must be > 0. |

---

## 11. Security Threat Model

### Assets to Protect

| Asset | Where Stored | Protection Mechanism |
|---|---|---|
| FID | Franchise memory only | Never transmitted; only VFID (encrypted) sent |
| VFID | QR code (ephemeral) | ASCON encryption + time-bound nonce |
| UID | Grid registry | Hashed password; never sent over wire |
| VMID | User device + Grid | Derived identifier; doesn't expose UID |
| PIN | Grid registry (hashed) | Keccak-256 hash; transmitted via RSA (vulnerable to Shor) |
| Blockchain | Grid disk | SHA-3 hash chain; append-only; admin-only write access |

### Attack Surfaces

**1. QR Code Eavesdropping**
- Threat: Attacker photographs QR and uses it.
- Mitigation: VFID is ASCON-encrypted + nonce is time-bound (5 min window + replay cache).

**2. Network Interception (Kiosk → Grid)**
- Threat: Attacker sniffs credential payload.
- Mitigation: RSA-OAEP encryption. (Vulnerability: broken by Shor — see demo.)

**3. Shor's Algorithm Attack (Quantum)**
- Threat: A quantum computer factors RSA modulus and recovers private key.
- Demo: Use `quantum/demo.py` to show factoring on a small RSA key.
- Mitigation path (not implemented in v1): Replace RSA with a post-quantum KEM such as CRYSTALS-Kyber.

**4. Blockchain Tampering**
- Threat: Attacker modifies a historical block.
- Mitigation: SHA-3 hash chain — any modification invalidates all subsequent hashes. Detected by `verify()`.

**5. PIN Brute-Force**
- Threat: Attacker tries all 4-digit PINs (10,000 possibilities).
- Mitigation: Lockout after 3 failed attempts per session.

---

## 12. Project Directory Structure

```
BITSF463_Team_XX/
├── grid/
├── kiosk/
├── user/
├── quantum/
├── tests/
├── keys/
│   ├── grid_private.pem      # Generated at first run, never committed
│   └── grid_public.pem
├── ledger.json               # Auto-created; commit initial empty version
├── requirements.txt
└── README.md                 # Team members, setup steps, assumptions
```

### Startup Order

```bash
# 1. Generate RSA keys (run once)
python grid/crypto/rsa_handler.py --generate-keys

# 2. Start Grid Authority Server (Laptop B)
python grid/server.py --port 5000

# 3. Start Charging Kiosk Server (Laptop A)
GRID_URL=http://<laptop-b-ip>:5000 python kiosk/server.py --port 5001

# 4. Run Registration Script (one-time setup)
python grid/registry.py --seed-data

# 5. Run EV Owner App (Phone / Laptop C)
KIOSK_URL=http://<laptop-a-ip>:5001 python user/app.py

# 6. Run Quantum Attack Demo (standalone)
python quantum/demo.py
```

---

## 13. Glossary

| Term | Definition |
|---|---|
| **ASCON** | A family of lightweight authenticated encryption algorithms. Selected as the NIST standard for lightweight cryptography (2023). |
| **AEAD** | Authenticated Encryption with Associated Data. Provides both confidentiality and integrity. |
| **FID** | Franchise ID. A 16-digit hex identifier unique to each charging station, generated by the Grid. |
| **UID** | User ID. A 16-digit hex identifier unique to each EV Owner, generated by the Grid. |
| **VMID** | Vehicle Mobile ID. Derived from UID + mobile number. Used in place of UID at the kiosk to avoid exposing the UID. |
| **VFID** | Virtual Franchise ID. An ASCON-encrypted, time-bound version of the FID embedded in the QR code. |
| **Keccak-256** | The original SHA-3 hash function (pre-NIST standardization). Used for FID/UID/VMID/block hash generation. |
| **LWC** | Lightweight Cryptography. Cryptographic algorithms designed for constrained environments (low power, limited memory). |
| **Shor's Algorithm** | A quantum algorithm that can factor large integers in polynomial time, breaking RSA. |
| **RSA-OAEP** | RSA with Optimal Asymmetric Encryption Padding. Used for credential encryption (the vulnerable channel). |
| **Blockchain** | An append-only, hash-linked list of records. In this system, maintained centrally by the Grid. |
| **Genesis Block** | The first block in the chain, with `previousHash = "000...000"`. Contains no transaction data. |
| **Dispute Flag** | A boolean field on a block indicating it is a refund or reversal of a previous transaction. |
| **Replay Attack** | An attack where a previously valid message (e.g., a captured QR code payload) is reused to initiate a new session. |
| **Zone Code** | A unique string identifying a geographic zone under an energy provider (e.g., `TP-NORTH-01`). |

---

*This document is the authoritative architecture reference for the BITSF463 EV Charging Gateway project. All implementation decisions not covered here should be documented as assumptions in the team README.*
