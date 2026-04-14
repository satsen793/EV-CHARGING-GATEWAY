import pytest
from grid.crypto.hashing import (
    keccak256, generate_fid, generate_uid, generate_vmid, generate_txn_id, hash_block
)


class TestKeccak256:
    def test_keccak256_deterministic(self):
        result1 = keccak256("test_input")
        result2 = keccak256("test_input")
        assert result1 == result2
    
    def test_keccak256_different_inputs(self):
        result1 = keccak256("input1")
        result2 = keccak256("input2")
        assert result1 != result2
    
    def test_keccak256_output_length(self):
        result = keccak256("test")
        assert len(result) == 64


class TestIDGeneration:
    def test_generate_fid_length(self):
        fid = generate_fid("Test Franchise", "2025-01-01T00:00:00Z", "password")
        assert len(fid) == 16
        assert fid.isupper()
        assert all(c in "0123456789ABCDEF" for c in fid)
    
    def test_generate_fid_deterministic(self):
        fid1 = generate_fid("Test", "2025-01-01T00:00:00Z", "pass")
        fid2 = generate_fid("Test", "2025-01-01T00:00:00Z", "pass")
        assert fid1 == fid2
    
    def test_generate_uid_length(self):
        uid = generate_uid("Test User", "2025-01-01T00:00:00Z", "password")
        assert len(uid) == 16
        assert uid.isupper()
    
    def test_generate_vmid_length(self):
        uid = generate_uid("Test", "2025-01-01T00:00:00Z", "pass")
        vmid = generate_vmid(uid, "9876543210")
        assert len(vmid) == 16
        assert vmid.isupper()
    
    def test_generate_txn_id_length(self):
        txn_id = generate_txn_id("UID123", "FID456", "2025-01-01T00:00:00Z", "150.00")
        assert len(txn_id) == 64


class TestBlockHashing:
    def test_hash_block_deterministic(self):
        hash1 = hash_block(0, "TXN1", "0"*64, "2025-01-01T00:00:00Z", "UID1", "FID1", 100.0, "SUCCESS", False)
        hash2 = hash_block(0, "TXN1", "0"*64, "2025-01-01T00:00:00Z", "UID1", "FID1", 100.0, "SUCCESS", False)
        assert hash1 == hash2
    
    def test_hash_block_different_values(self):
        hash1 = hash_block(0, "TXN1", "0"*64, "2025-01-01T00:00:00Z", "UID1", "FID1", 100.0, "SUCCESS", False)
        hash2 = hash_block(0, "TXN1", "0"*64, "2025-01-01T00:00:00Z", "UID1", "FID1", 150.0, "SUCCESS", False)
        assert hash1 != hash2
