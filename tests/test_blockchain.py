import pytest
from grid.blockchain import Block, Blockchain
from datetime import datetime, timezone


class TestBlock:
    def test_block_creation_and_sealing(self):
        block = Block(
            index=1,
            txn_id="ABC123DEF456",
            previous_hash="0" * 64,
            timestamp=datetime.now(timezone.utc).isoformat(),
            uid="UID123",
            fid="FID456",
            amount=100.0,
            status="SUCCESS"
        )
        block.seal()
        
        assert block.block_hash != ""
        assert len(block.block_hash) == 64
    
    def test_block_hash_deterministic(self):
        block1 = Block(
            index=1,
            txn_id="ABC123",
            previous_hash="0" * 64,
            timestamp="2025-01-01T00:00:00Z",
            uid="UID1",
            fid="FID1",
            amount=100.0,
            status="SUCCESS"
        )
        block1.seal()
        hash1 = block1.block_hash
        
        block2 = Block(
            index=1,
            txn_id="ABC123",
            previous_hash="0" * 64,
            timestamp="2025-01-01T00:00:00Z",
            uid="UID1",
            fid="FID1",
            amount=100.0,
            status="SUCCESS"
        )
        block2.seal()
        hash2 = block2.block_hash
        
        assert hash1 == hash2


class TestBlockchain:
    def test_blockchain_initialization(self):
        bc = Blockchain()
        assert len(bc.chain) == 1
        assert bc.chain[0].status == "GENESIS"
    
    def test_add_block_creates_linked_chain(self):
        bc = Blockchain()
        block1 = bc.add_block("UID1", "FID1", 100.0)
        block2 = bc.add_block("UID2", "FID2", 150.0)
        
        assert len(bc.chain) == 3
        assert block1.previous_hash == bc.chain[0].block_hash
        assert block2.previous_hash == block1.block_hash
    
    def test_find_block_by_txn_id(self):
        bc = Blockchain()
        block = bc.add_block("UID1", "FID1", 100.0)
        
        found = bc.find_block(block.txn_id)
        assert found is not None
        assert found.txn_id == block.txn_id
    
    def test_find_nonexistent_block(self):
        bc = Blockchain()
        found = bc.find_block("NONEXISTENT")
        assert found is None
    
    def test_blockchain_is_valid(self):
        bc = Blockchain()
        bc.add_block("UID1", "FID1", 100.0)
        bc.add_block("UID2", "FID2", 150.0)
        
        assert bc.is_valid() == True
    
    def test_blockchain_detects_tampering(self):
        bc = Blockchain()
        bc.add_block("UID1", "FID1", 100.0)
        
        bc.chain[1].amount = 200.0
        
        assert bc.is_valid() == False
    
    def test_add_reverse_block(self):
        bc = Blockchain()
        block = bc.add_block("UID1", "FID1", 100.0)
        
        reverse = bc.add_reverse(block.txn_id)
        
        assert reverse.amount == -100.0
        assert reverse.status == "REVERSED"
        assert reverse.dispute_flag == True
        assert len(bc.chain) == 3
