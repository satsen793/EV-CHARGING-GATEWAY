import struct
import time
import ascon


def encrypt_vfid(fid: str, encryption_key: bytes, timestamp: int) -> tuple[bytes, bytes]:
    nonce = struct.pack(">Q", timestamp).ljust(16, b'\x00')
    plaintext = fid.encode('ascii')
    associated_data = b"EV-KIOSK-V1"
    ciphertext = ascon.encrypt(encryption_key, nonce, associated_data, plaintext, variant="Ascon-128")
    return ciphertext, nonce


def decrypt_vfid(ciphertext: bytes, nonce: bytes, encryption_key: bytes) -> str:
    associated_data = b"EV-KIOSK-V1"
    plaintext = ascon.decrypt(encryption_key, nonce, associated_data, ciphertext, variant="Ascon-128")
    return plaintext.decode('ascii')


def is_vfid_fresh(nonce: bytes, tolerance_seconds: int = 300) -> bool:
    timestamp_bytes = nonce[:8]
    ts = struct.unpack(">Q", timestamp_bytes)[0]
    current_ts = int(time.time())
    return abs(current_ts - ts) < tolerance_seconds
