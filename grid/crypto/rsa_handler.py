from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
import json


def generate_keypair() -> tuple[bytes, bytes]:
    key = RSA.generate(2048)
    private_pem = key.export_key()
    public_pem = key.publickey().export_key()
    return private_pem, public_pem


def encrypt_creds(vmid: str, pin: str, amount: float, grid_public_key_pem: bytes) -> bytes:
    key = RSA.import_key(grid_public_key_pem)
    cipher = PKCS1_OAEP.new(key)
    payload = {"vmid": vmid, "pin": pin, "amount": amount}
    payload_json = json.dumps(payload).encode('utf-8')
    return cipher.encrypt(payload_json)


def decrypt_creds(ciphertext: bytes, grid_private_key_pem: bytes) -> dict:
    key = RSA.import_key(grid_private_key_pem)
    cipher = PKCS1_OAEP.new(key)
    payload_json = cipher.decrypt(ciphertext)
    return json.loads(payload_json)
