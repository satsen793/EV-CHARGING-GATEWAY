import pytest
from grid.registry import Registry, UserRecord, FranchiseRecord


class TestRegistry:
    @pytest.fixture
    def registry(self):
        return Registry()
    
    def test_register_franchise(self, registry):
        fid = registry.register_franchise("Test Franchise", "TP-NORTH-01", "password", 5000.0)
        
        assert fid is not None
        assert len(fid) == 16
        
        franchise = registry.lookup_franchise(fid)
        assert franchise is not None
        assert franchise.name == "Test Franchise"
        assert franchise.balance == 5000.0
    
    def test_register_user(self, registry):
        uid, vmid = registry.register_user("Test User", "9876543210", "TP-NORTH-01", "password", "1234", 2000.0)
        
        assert uid is not None
        assert vmid is not None
        assert len(uid) == 16
        assert len(vmid) == 16
        
        user = registry.lookup_user_by_vmid(vmid)
        assert user is not None
        assert user.name == "Test User"
        assert user.balance == 2000.0
    
    def test_verify_pin_correct(self, registry):
        uid, vmid = registry.register_user("Test User", "9876543210", "TP-NORTH-01", "password", "1234", 2000.0)
        
        assert registry.verify_pin(vmid, "1234") == True
    
    def test_verify_pin_incorrect(self, registry):
        uid, vmid = registry.register_user("Test User", "9876543210", "TP-NORTH-01", "password", "1234", 2000.0)
        
        assert registry.verify_pin(vmid, "5678") == False
    
    def test_deduct_balance_sufficient(self, registry):
        uid, vmid = registry.register_user("Test User", "9876543210", "TP-NORTH-01", "password", "1234", 2000.0)
        
        result = registry.deduct_balance(vmid, 500.0)
        assert result == True
        
        user = registry.lookup_user_by_vmid(vmid)
        assert user.balance == 1500.0
    
    def test_deduct_balance_insufficient(self, registry):
        uid, vmid = registry.register_user("Test User", "9876543210", "TP-NORTH-01", "password", "1234", 500.0)
        
        result = registry.deduct_balance(vmid, 1000.0)
        assert result == False
        
        user = registry.lookup_user_by_vmid(vmid)
        assert user.balance == 500.0
    
    def test_credit_balance(self, registry):
        fid = registry.register_franchise("Test Franchise", "TP-NORTH-01", "password", 5000.0)
        
        registry.credit_balance(fid, 500.0)
        
        franchise = registry.lookup_franchise(fid)
        assert franchise.balance == 5500.0
