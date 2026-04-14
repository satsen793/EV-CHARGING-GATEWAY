from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
import json


def encrypt_creds(vmid: str, pin: str, amount: float, grid_public_key_pem: bytes) -> bytes:
    key = RSA.import_key(grid_public_key_pem)
    cipher = PKCS1_OAEP.new(key)
    payload = {"vmid": vmid, "pin": pin, "amount": amount}
    payload_json = json.dumps(payload).encode('utf-8')
    return cipher.encrypt(payload_json)
