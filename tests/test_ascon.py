import pytest
from grid.crypto.ascon_handler import encrypt_vfid, decrypt_vfid, is_vfid_fresh
from grid.config import ASCON_KEY
import time


class TestASCONEncryption:
    def test_encrypt_decrypt_roundtrip(self):
        fid = "A1B2C3D4E5F67890"
        timestamp = int(time.time())
        
        ciphertext, nonce = encrypt_vfid(fid, ASCON_KEY, timestamp)
        decrypted = decrypt_vfid(ciphertext, nonce, ASCON_KEY)
        
        assert decrypted == fid
    
    def test_decrypt_with_wrong_key_fails(self):
        fid = "A1B2C3D4E5F67890"
        timestamp = int(time.time())
        wrong_key = bytes.fromhex("11223344556677889900aabbccddee00")
        
        ciphertext, nonce = encrypt_vfid(fid, ASCON_KEY, timestamp)
        
        with pytest.raises(Exception):
            decrypt_vfid(ciphertext, nonce, wrong_key)
    
    def test_vfid_freshness_check(self):
        current_time = int(time.time())
        import struct
        nonce = struct.pack(">Q", current_time).ljust(16, b'\x00')
        
        assert is_vfid_fresh(nonce, tolerance_seconds=300) == True
    
    def test_vfid_expiry_check(self):
        old_time = int(time.time()) - 400
        import struct
        nonce = struct.pack(">Q", old_time).ljust(16, b'\x00')
        
        assert is_vfid_fresh(nonce, tolerance_seconds=300) == False
