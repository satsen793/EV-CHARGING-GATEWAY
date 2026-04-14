import pytest
from grid.crypto.rsa_handler import generate_keypair, encrypt_creds, decrypt_creds


class TestRSAEncryption:
    @pytest.fixture
    def rsa_keypair(self):
        private_key, public_key = generate_keypair()
        return private_key, public_key
    
    def test_generate_keypair_produces_valid_keys(self):
        private_key, public_key = generate_keypair()
        assert private_key is not None
        assert public_key is not None
        assert b'PRIVATE KEY' in private_key
        assert b'PUBLIC KEY' in public_key
    
    def test_encrypt_decrypt_roundtrip(self, rsa_keypair):
        private_key, public_key = rsa_keypair
        vmid = "A1B2C3D4E5F67890"
        pin = "1234"
        amount = 150.00
        
        ciphertext = encrypt_creds(vmid, pin, amount, public_key)
        decrypted_creds = decrypt_creds(ciphertext, private_key)
        
        assert decrypted_creds['vmid'] == vmid
        assert decrypted_creds['pin'] == pin
        assert decrypted_creds['amount'] == amount
    
    def test_decrypt_with_wrong_key_fails(self, rsa_keypair):
        private_key, public_key = rsa_keypair
        _, wrong_private_key = generate_keypair()
        
        vmid = "A1B2C3D4E5F67890"
        pin = "1234"
        amount = 150.00
        
        ciphertext = encrypt_creds(vmid, pin, amount, public_key)
        
        with pytest.raises(Exception):
            decrypt_creds(ciphertext, wrong_private_key)
