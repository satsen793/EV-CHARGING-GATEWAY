import os


KIOSK_PORT = int(os.getenv("KIOSK_PORT", 5001))
GRID_URL = os.getenv("GRID_URL", "http://localhost:5000")

ASCON_KEY = bytes.fromhex("00112233445566778899aabbccddeeff")

VFID_TOLERANCE_SECONDS = 300
