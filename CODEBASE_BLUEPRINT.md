# Codebase Blueprint — Detailed Design

> Data flows, interfaces, state machines, and implementation notes for each module.

---

## Module 1: Crypto Utilities (`grid/crypto/hashing.py`)

### Purpose
Implement Keccak-256 hashing for ID generation (FID, UID, VMID) and block hashing.

### API

```python
def keccak256(data: str) -> str
    Input:  data (string)
    Output: 64-character hex digest
    Logic:  Use pycryptodome's keccak.new(digest_bits=256)

def generate_fid(name: str, created_at: str, password: str) -> str
    Input:  franchise_name, ISO_timestamp, password
    Output: 16-char uppercase FID (first 16 hex chars of Keccak-256)
    Logic:  keccak256(name + created_at + password)[:16].upper()

def generate_uid(name: str, created_at: str, password: str) -> str
    Input:  user_name, ISO_timestamp, password
    Output: 16-char uppercase UID
    Logic:  Same as FID

def generate_vmid(uid: str, mobile: str) -> str
    Input:  uid, mobile_number (10 digits)
    Output: 16-char uppercase VMID
    Logic:  keccak256(uid + mobile)[:16].upper()

def generate_txn_id(uid: str, fid: str, timestamp: str, amount: str) -> str
    Input:  uid, fid, ISO_timestamp, amount_as_string
    Output: 64-char hex transaction ID
    Logic:  keccak256(uid + fid + timestamp + amount)

def hash_block(index: int, txn_id: str, prev_hash: str, timestamp: str, 
               uid: str, fid: str, amount: float, status: str, dispute: bool) -> str
    Input:  All block fields
    Output: 64-char block hash
    Logic:  JSON-encode all fields, compute Keccak-256
```

### Dependencies
- `pycryptodome>=3.20` (keccak)
- `json` (for block encoding)

### Notes
- All outputs are deterministic (same input = same output)
- Uppercase hex is enforced for consistency
- No error handling needed (inputs assumed valid)

---

## Module 2: ASCON Encryption (`kiosk/crypto/ascon_handler.py`)

### Purpose
Kiosk-side ASCON-128 encryption of FID to VFID. Also provide decryption for standalone testing.

### API

```python
def encrypt_vfid(fid: str, encryption_key: bytes, timestamp: int) -> tuple[bytes, bytes]
    Input:  fid (16-char hex), key (16 bytes), Unix timestamp
    Output: (ciphertext_bytes, nonce_bytes)
    Logic:
      - nonce = struct.pack(">Q", timestamp).ljust(16, b'\x00')
      - plaintext = fid.encode('ascii')
      - associated_data = b"EV-KIOSK-V1"
      - ciphertext = ascon.encrypt(key, nonce, associated_data, plaintext)
      - return (ciphertext, nonce)

def decrypt_vfid(ciphertext: bytes, nonce: bytes, encryption_key: bytes) -> str
    Input:  ciphertext, nonce, key
    Output: fid (plaintext, 16-char hex)
    Raises: ascon.DecryptionError if authentication fails
    Logic:
      - associated_data = b"EV-KIOSK-V1"
      - plaintext = ascon.decrypt(key, nonce, associated_data, ciphertext)
      - return plaintext.decode('ascii')

def is_vfid_fresh(nonce: bytes, tolerance_seconds: int = 300) -> bool
    Input:  nonce, tolerance_seconds (default 300)
    Output: True if timestamp in nonce is within tolerance
    Logic:
      - ts = struct.unpack(">Q", nonce[:8])[0]
      - return abs(current_time() - ts) < tolerance_seconds
```

### Dependencies
- `ascon>=1.0` (ASCON-128)
- `struct` (pack/unpack timestamps)
- `time` (current Unix timestamp)

### Notes
- ASCON is AEAD (authenticated encryption); provides confidentiality + integrity
- Nonce is 16 bytes; first 8 bytes encode timestamp, remaining 8 bytes are padding
- Replay prevention: if nonce is outside tolerance window, reject at Grid
- No key rotation in v1 (single global ASCON key per site)

---

## Module 3: RSA Encryption/Decryption

### `kiosk/crypto/rsa_handler.py`

```python
def encrypt_creds(vmid: str, pin: str, amount: float, grid_public_key_pem: bytes) -> bytes
    Input:  vmid, pin, amount, Grid's public key (PEM format)
    Output: ciphertext (RSA-OAEP encrypted)
    Logic:
      - Load public key from PEM
      - Create payload = {"vmid": vmid, "pin": pin, "amount": amount}
      - JSON-encode payload
      - cipher = PKCS1_OAEP.new(public_key)
      - return cipher.encrypt(payload_json)
```

### `grid/crypto/rsa_handler.py`

```python
def generate_keypair() -> tuple[bytes, bytes]
    Input:  None
    Output: (private_key_pem, public_key_pem)
    Logic:
      - key = RSA.generate(2048)
      - private_pem = key.export_key()
      - public_pem = key.publickey().export_key()
      - return (private_pem, public_pem)

def decrypt_creds(ciphertext: bytes, grid_private_key_pem: bytes) -> dict
    Input:  ciphertext, Grid's private key (PEM format)
    Output: {"vmid": str, "pin": str, "amount": float}
    Raises: ValueError if decryption fails or JSON is invalid
    Logic:
      - Load private key from PEM
      - cipher = PKCS1_OAEP.new(private_key)
      - payload_json = cipher.decrypt(ciphertext)
      - return json.loads(payload_json)
```

### Dependencies
- `pycryptodome>=3.20` (RSA, PKCS1_OAEP)
- `json` (payload serialization)

### Notes
- RSA-2048 is intentionally vulnerable for Shor's demo
- PKCS1_OAEP provides semantic security (deterministic encryption would be broken)
- Private key NEVER goes into code; loaded from `keys/grid_private.pem` at runtime

---

## Module 4: Blockchain (`grid/blockchain.py`)

### Data Model

```python
@dataclass
class Block:
    index:          int       # Position in chain
    txn_id:         str       # Transaction ID (64-char hex)
    previous_hash:  str       # Previous block's hash (64-char hex)
    timestamp:      str       # ISO 8601 timestamp
    uid:            str       # User ID (16-char hex)
    fid:            str       # Franchise ID (16-char hex) — now plaintext from Kiosk
    amount:         float     # Amount transferred
    status:         str       # "SUCCESS" | "GENESIS" | "REVERSED" | "FAILED"
    dispute_flag:   bool      # True if this is a reversal block
    block_hash:     str       # SHA3-256 of all above fields

    def compute_hash(self) -> str
        Input:  self (all fields)
        Output: 64-char hex hash
        Logic:
          - Create dict of all fields except block_hash
          - JSON-encode (sorted keys)
          - SHA3-256 hash
          - Return hex

    def seal(self)
        Input:  self
        Output: None (modifies self.block_hash)
        Logic:  self.block_hash = self.compute_hash()
```

### Blockchain Class

```python
class Blockchain:
    def __init__(self)
        Initializes empty chain + creates genesis block

    def add_block(uid: str, fid: str, amount: float) -> Block
        Input:  uid, fid, amount
        Output: Created and sealed Block
        Logic:
          - prev = self.chain[-1]
          - Create new Block(index=len(chain), txn_id=generate_txn_id(...), 
            previous_hash=prev.block_hash, ...)
          - Seal block (compute hash)
          - Append to chain
          - Return block

    def find_block(txn_id: str) -> Block | None
        Input:  txn_id (64-char hex)
        Output: Block if found, None otherwise
        Logic:  Linear search

    def add_reverse(original_txn_id: str) -> Block
        Input:  original_txn_id
        Output: Reversal block
        Logic:
          - Find original block
          - Create new block with negative amount, dispute_flag=True
          - Append to chain
          - Return reversal block

    def is_valid() -> bool
        Input:  None
        Output: True if chain is valid
        Logic:
          - For each block i from 1 to len(chain):
            - Verify block_hash == block.compute_hash()
            - Verify block.previous_hash == chain[i-1].block_hash
          - Return True if all checks pass
```

### Persistence

```python
def save_blockchain(blockchain: Blockchain, path: str = "ledger.json")
    Input:  Blockchain object, file path
    Output: None (writes to file)
    Logic:  Convert each block to dict, JSON-serialize, write

def load_blockchain(path: str = "ledger.json") -> Blockchain
    Input:  File path
    Output: Blockchain object
    Logic:  Read JSON, reconstruct Block objects, rebuild chain
```

### Notes
- Genesis block: index=0, txn_id="GENESIS", previous_hash="0"*64, status="GENESIS"
- Block hash is computed over deterministic JSON representation (stable field ordering)
- No consensus; no validation network — simple append-only log
- Integrity check is O(n) but fast enough for demo (<1000 blocks)

---

## Module 5: Registry (`grid/registry.py`)

### Data Models

```python
@dataclass
class Provider:
    name: str                # "Tata Power", "NTPC", etc.
    zones: list[str]        # ["TP-NORTH-01", "TP-SOUTH-02", "TP-WEST-03"]

@dataclass
class FranchiseRecord:
    fid: str                 # Generated ID (16-char hex)
    name: str
    zone_code: str
    password_hash: str       # Keccak-256 hash
    balance: float
    created_at: str          # ISO timestamp

@dataclass
class UserRecord:
    uid: str                 # Generated ID (16-char hex)
    vmid: str                # Derived from uid + mobile
    name: str
    mobile: str              # 10 digits
    zone_code: str
    password_hash: str       # Keccak-256 hash
    pin_hash: str            # Keccak-256 hash of PIN
    balance: float
    created_at: str          # ISO timestamp
```

### Registry Class

```python
class Registry:
    def __init__(self)
        Initialize empty registries (in-memory dicts)

    def register_franchise(name: str, zone_code: str, password: str, 
                          initial_balance: float) -> str
        Input:  franchise details
        Output: fid (16-char hex)
        Logic:
          - timestamp = now_iso()
          - password_hash = keccak256(password)
          - fid = generate_fid(name, timestamp, password)
          - Store FranchiseRecord(fid, name, zone_code, password_hash, balance, timestamp)
          - Return fid

    def register_user(name: str, mobile: str, zone_code: str, password: str, 
                      pin: str, initial_balance: float) -> tuple[str, str]
        Input:  user details
        Output: (uid, vmid)
        Logic:
          - timestamp = now_iso()
          - password_hash = keccak256(password)
          - pin_hash = keccak256(pin)
          - uid = generate_uid(name, timestamp, password)
          - vmid = generate_vmid(uid, mobile)
          - Store UserRecord(uid, vmid, name, mobile, zone_code, password_hash, pin_hash, balance, timestamp)
          - Return (uid, vmid)

    def lookup_franchise(fid: str) -> FranchiseRecord | None
        Input:  fid
        Output: FranchiseRecord or None

    def lookup_user_by_vmid(vmid: str) -> UserRecord | None
        Input:  vmid
        Output: UserRecord or None

    def lookup_user_by_uid(uid: str) -> UserRecord | None
        Input:  uid
        Output: UserRecord or None

    def verify_pin(vmid: str, pin: str) -> bool
        Input:  vmid, pin plaintext
        Output: True if pin matches

    def deduct_balance(vmid: str, amount: float) -> bool
        Input:  vmid, amount
        Output: True if successful, False if insufficient balance
        Logic:
          - If user.balance >= amount:
            - user.balance -= amount
            - return True
          - Else: return False

    def credit_balance(fid: str, amount: float) -> bool
        Input:  fid, amount
        Output: True if successful
        Logic:
          - franchise.balance += amount
          - return True
```

### Notes
- All registries are in-memory (no database)
- VMIDs are computed from UID + mobile (deterministic, repeatable)
- Passwords and PINs stored as hashes (Keccak-256)
- Balance deduction is atomic (either succeeds or fails, no partial updates)
- No authentication by Grid for registration (v1 assumes admin-only access)

---

## Module 6: Grid Authorization (`grid/auth.py`)

### Authorization Flow

```python
def authorize_transaction(encrypted_creds: bytes, vfid_ciphertext: bytes, 
                          vfid_nonce: bytes, vfid_timestamp: str,
                          registry: Registry, blockchain: Blockchain,
                          grid_private_key_pem: bytes) -> dict
    
    Input:
      - encrypted_creds: RSA-OAEP encrypted (VMID, PIN, amount)
      - vfid_ciphertext: ASCON-encrypted FID
      - vfid_nonce: 16-byte nonce
      - vfid_timestamp: ISO timestamp from Kiosk
      - registry: User/Franchise registries
      - blockchain: Blockchain instance
      - grid_private_key: Grid's RSA private key (PEM)
    
    Output:
      - {"approved": True, "txnId": "...", "message": "...", "userBalance": ...}
      OR
      - {"approved": False, "message": "...", "reason": "..."}
    
    Logic:
      1. Check VFID freshness: if (now - vfid_timestamp) > 300 seconds, reject
      2. Check VFID replay: if nonce in nonce_cache, reject (then add to cache)
      3. Decrypt credentials using grid_private_key
      4. Extract vmid, pin, amount
      5. Lookup user by vmid
      6. If user not found, reject
      7. Verify PIN: if pin_hash != keccak256(pin), increment fail counter
      8. If fail counter >= 3, reject with "PIN locked"
      9. Check user balance: if balance < amount, reject
      10. Check franchise (extracted from VFID) balance: if franchise.balance < 0 (assuming no limit, skip)
      11. Deduct from user, credit to franchise
      12. Create block: blockchain.add_block(uid, fid, amount)
      13. Persist blockchain to ledger.json
      14. Return approved response with new user balance
```

### Notes
- Replay protection: maintain set of (nonce, timestamp) seen in past 10 minutes
- PIN lockout: track failed attempts per VMID per session (not persistent across sessions in v1)
- VFID timestamp is transmitted separately; if > 5 minutes old, reject
- Atomic: if any check fails, NO BLOCK IS WRITTEN

---

## Module 7: Grid Server (`grid/server.py`)

### Routes

```python
POST /api/register/franchise
    Body: {"name": str, "zoneCode": str, "password": str, "initialBalance": float}
    Response 200: {"fid": str, "message": str}

POST /api/register/user
    Body: {"name": str, "mobile": str, "zoneCode": str, "password": str, "pin": str, "initialBalance": float}
    Response 200: {"uid": str, "vmid": str, "message": str}

POST /api/authorize
    Body: {"encryptedCredentials": str (base64), "vfid": str (base64), 
           "vfidNonce": str (base64), "vfidTimestamp": str (ISO)}
    Response 200: {"approved": bool, "txnId": str, "message": str, ...}

POST /api/dispute
    Body: {"txnId": str, "reason": str}
    Response 200: {"refunded": bool, "reverseTxnId": str, "refundAmount": float}

GET /api/ledger
    Response 200: [Block, Block, ...]

GET /api/ledger/verify
    Response 200: {"valid": bool, "chainLength": int}
```

### Server Initialization

```python
class GridServer:
    def __init__(self, port: int = 5000):
        self.port = port
        self.registry = Registry()
        self.blockchain = Blockchain()
        self.grid_private_key = load_or_generate_rsa_private_key()
        self.grid_public_key = extract_public_key(self.grid_private_key)
        self.app = Flask(__name__)
        self.nonce_cache = set()  # For replay prevention
        self.pin_fail_counter = {}  # {vmid: fail_count}
```

### Notes
- All endpoints return JSON
- Requests use base64 encoding for binary data (ciphertext, nonce)
- Public key is served at `GET /api/grid/public-key` for kiosk to fetch
- Error responses include descriptive messages (do not leak internal details)

---

## Module 8: Kiosk Server (`kiosk/server.py`)

### Routes

```python
POST /kiosk/load-fid
    Body: {"fid": str}
    Response 200: {"message": "FID loaded", "qrReady": True}
    Side effect: Store FID in session state, generate VFID + QR

GET /kiosk/qr
    Response 200 (image/png): PNG bytes of current QR code
    If no QR ready, return error

POST /kiosk/payment
    Body: {"vmid": str, "pin": str, "amount": float}
    Logic:
      1. Retrieve current VFID + nonce from session
      2. If VFID is stale (>5 min), regenerate
      3. Decrypt VFID locally to verify FID matches loaded FID
      4. Encrypt (vmid, pin, amount) using Grid's public key
      5. POST to Grid /api/authorize with encrypted payload
      6. Receive response
      7. Return response to EV Owner
      8. If approved, send unlock signal to franchise hardware (mock)
    Response 200: {"approved": bool, "message": str, ...}
```

### Session State

```python
class KioskSession:
    def __init__(self):
        self.fid = None              # Current FID (loaded by franchise owner)
        self.vfid_ciphertext = None  # ASCON ciphertext
        self.vfid_nonce = None       # 16-byte nonce
        self.vfid_timestamp = None   # ISO timestamp
        self.qr_image = None         # PNG bytes

    def load_fid(fid: str):
        self.fid = fid
        self.regenerate_vfid()

    def regenerate_vfid(self):
        timestamp = time.time()
        self.vfid_ciphertext, self.vfid_nonce = encrypt_vfid(self.fid, ASCON_KEY, int(timestamp))
        self.vfid_timestamp = datetime.fromtimestamp(timestamp).isoformat()
        self.qr_image = generate_qr(self.vfid_ciphertext, self.vfid_nonce)
```

### Notes
- Kiosk decrypts VFID internally to validate it before forwarding to Grid
- VFID regeneration happens every 5 minutes (or on demand)
- Franchise hardware (cable lock) is mocked; no real hardware control
- Session is per-kiosk instance (no concurrent sessions in v1)

---

## Module 9: EV Owner App (`user/app.py`)

### User Flow

```python
def main_cli():
    1. Display menu: "1. Register, 2. Scan QR & Pay, 3. View Balance, 0. Exit"
    2. If Register:
       - Input: name, mobile, password, pin
       - POST /grid/register/user
       - Display: uid, vmid
    3. If Scan & Pay:
       - Input: path to QR image (or camera)
       - Decode QR: extract VFID + nonce
       - Input: vmid, pin, charging amount
       - POST /kiosk/payment {vmid, pin, amount}
       - Display response: approved or rejected
    4. If View Balance:
       - GET /grid/ledger (search for user's transactions)
       - Display: cumulative balance change
```

### QR Scanner

```python
def scan_qr_from_file(image_path: str) -> dict
    Input:  path to image file (PNG, JPG, etc.)
    Output: {"vfid": str (base64), "nonce": str (base64)}
    Logic:
      - Use pyzbar or OpenCV to detect QR code
      - Decode JSON payload
      - Return parsed dict

def scan_qr_from_camera() -> dict
    Input:  None
    Output: {"vfid": str, "nonce": str}
    Logic:  (Optional in v1; use pyzbar + camera)
```

### Notes
- Simple CLI for v1 (no web UI in first iteration)
- QR payload is JSON with base64-encoded fields
- User must known VMID (provided during registration or stored locally)

---

## Module 10: Quantum Attack Demo (`quantum/demo.py`)

### Demo Flow

```python
def demo_shors_attack():
    1. Generate small RSA key (512-bit or 64-bit for demo)
       n = p * q (where p, q are two primes)
    2. Simulate user payment:
       - vmid = "A1B2C3D4E5F67890"
       - pin = "1234"
       - amount = 150.00
       - Encrypt with 512-bit RSA public key
    3. Run Shor's algorithm simulation:
       - use sympy.factorint(n) to factor n
       - extract p, q
    4. Recover private key:
       - Compute φ(n) = (p-1) * (q-1)
       - Find d such that e*d ≡ 1 (mod φ(n))
    5. Decrypt intercepted payload
       - Show recovered credentials
    6. Print report:
       - Original encrypted blob
       - Factored primes
       - Recovered private key
       - Decrypted plaintext
```

### Shor's Simulation

```python
def simulate_shors_algorithm(n: int) -> tuple[int, int]
    Input:  RSA modulus n
    Output: (p, q) such that p * q = n
    Logic:  Use sympy.factorint(n)
    
    NOTE: This is classical factoring simulation, not a true quantum Shor circuit.
    For a real quantum circuit demonstration, implement a Qiskit version.
```

### Notes
- Demo RSA is 512-bit or smaller (factorable in <1 second classically)
- Production RSA-2048 cannot be factored classically
- Output should be dramatic and educational (print each step)
- Include timing: "Factoring n took X seconds"

---

## Module 11: Testing Strategy

### Unit Tests (`tests/test_*.py`)

**test_hashing.py:**
- Keccak-256 produces correct hex output
- FID/UID/VMID generation is deterministic
- Hash vectors match known test cases

**test_ascon.py:**
- Encrypt then decrypt returns plaintext
- Decryption fails with wrong key
- Nonce freshness check works

**test_rsa.py:**
- Encrypt then decrypt returns plaintext
- Decryption fails with wrong key
- Payload JSON is correctly serialized/deserialized

**test_blockchain.py:**
- Blocks seal correctly (hash computed)
- Chain linkage verified
- add_block appends to chain
- find_block returns correct block
- add_reverse creates negative block
- is_valid detects tampering

**test_edge_cases.py:**
- Expired VFID rejected
- Replay attack detected (same nonce twice)
- PIN lockout after 3 failures
- Insufficient balance rejected
- Double-spend prevented (balance goes negative temporarily, then rolled back on failure)

**test_quantum_demo.py:**
- Demo RSA key factors correctly
- Private key recovery works
- Decryption of intercepted creds succeeds

### Integration Tests (`test_auth_flow.py`)

- Grid + Kiosk + User app running concurrently
- User registration → FID registration → QR generation → payment submission → block recorded
- Full transaction lifecycle
- Blockchain integrity maintained
- Batch: 10 concurrent transactions

---

## API Contract Summary

### Grid Authority APIs

| Endpoint | Method | Request | Response | Error |
|----------|--------|---------|----------|-------|
| `/api/register/franchise` | POST | name, zone, password, balance | fid, message | 400 if invalid zone |
| `/api/register/user` | POST | name, mobile, zone, password, pin, balance | uid, vmid, message | 400 if invalid |
| `/api/authorize` | POST | encryptedCreds, vfid, nonce, timestamp | approved, txnId, message | 200 (approved: false) |
| `/api/dispute` | POST | txnId, reason | refunded, reverseTxnId | 404 if txnId not found |
| `/api/ledger` | GET | - | [Block, ...] | 200 always |
| `/api/ledger/verify` | GET | - | valid, chainLength | 200 always |
| `/api/grid/public-key` | GET | - | {"publicKey": PEM_string} | 200 always |

### Kiosk APIs

| Endpoint | Method | Request | Response | Error |
|----------|--------|---------|----------|-------|
| `/kiosk/load-fid` | POST | fid | message, qrReady | 400 if fid invalid |
| `/kiosk/qr` | GET | - | PNG bytes | 400 if no qr ready |
| `/kiosk/payment` | POST | vmid, pin, amount | approved, message | 500 if Grid unreachable |

---

**End of Codebase Blueprint.**

All modules are ready for implementation. No comments in code files; all logic is self-explanatory via naming.

