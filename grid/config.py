import os


GRID_PORT = int(os.getenv("GRID_PORT", 5000))
KIOSK_PORT = int(os.getenv("KIOSK_PORT", 5001))
GRID_URL = os.getenv("GRID_URL", "http://localhost:5000")
KIOSK_URL = os.getenv("KIOSK_URL", "http://localhost:5001")

ASCON_KEY = bytes.fromhex("00112233445566778899aabbccddeeff")

RSA_PRIVATE_KEY_PATH = "keys/grid_private.pem"
RSA_PUBLIC_KEY_PATH = "keys/grid_public.pem"

LEDGER_PATH = "ledger.json"

VFID_TOLERANCE_SECONDS = 300
NONCE_CACHE_TTL_SECONDS = 600
PIN_FAIL_LIMIT = 3
