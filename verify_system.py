#!/usr/bin/env python
"""System verification script - tests core modules without pytest dependency."""

import sys
import traceback

def test_imports():
    """Verify all modules can be imported."""
    print("=" * 60)
    print("TESTING MODULE IMPORTS")
    print("=" * 60)
    
    modules = [
        "grid.crypto.hashing",
        "grid.crypto.ascon_handler",
        "grid.crypto.rsa_handler",
        "grid.blockchain",
        "grid.registry",
        "grid.config",
        "kiosk.config",
        "user.app",
        "quantum.shors_simulation",
    ]
    
    failed = []
    for module in modules:
        try:
            __import__(module)
            print(f"[OK] {module}")
        except Exception as e:
            print(f"[FAIL] {module}: {e}")
            failed.append((module, e))
    
    return failed

def test_keccak256():
    """Test Keccak-256 hashing."""
    print("\n" + "=" * 60)
    print("TESTING KECCAK-256 HASHING")
    print("=" * 60)
    
    try:
        from grid.crypto.hashing import keccak256, generate_fid
        
        # Test deterministic hashing
        h1 = keccak256("test")
        h2 = keccak256("test")
        assert h1 == h2, "Hashing not deterministic"
        print(f"[OK] Deterministic hashing: {h1[:16]}...")
        
        # Test different inputs
        h3 = keccak256("different")
        assert h1 != h3, "Different inputs produced same hash"
        print(f"[OK] Different inputs produce different hashes")
        
        # Test FID generation
        fid = generate_fid("TestCo", "2025-01-01T00:00:00Z", "secret")
        assert len(fid) == 16, f"FID length wrong: {len(fid)}"
        assert fid.isupper(), "FID not uppercase"
        print(f"[OK] FID generation: {fid}")
        
        return []
    except Exception as e:
        print(f"[FAIL] Keccak-256 tests failed: {e}")
        traceback.print_exc()
        return [(e, traceback.format_exc())]

def test_ascon():
    """Test ASCON encryption."""
    print("\n" + "=" * 60)
    print("TESTING ASCON-128 ENCRYPTION")
    print("=" * 60)
    
    try:
        from grid.crypto.ascon_handler import AsconHandler
        
        handler = AsconHandler()
        plaintext = "Hello, World!"
        
        ciphertext = handler.encrypt(plaintext.encode())
        decrypted = handler.decrypt(ciphertext).decode()
        
        assert decrypted == plaintext, f"Decryption mismatch: {decrypted} != {plaintext}"
        print(f"[OK] Encrypt/Decrypt: '{plaintext}' -> '{decrypted}'")
        
        return []
    except Exception as e:
        print(f"[FAIL] ASCON tests failed: {e}")
        traceback.print_exc()
        return [(e, traceback.format_exc())]

def test_rsa():
    """Test RSA encryption."""
    print("\n" + "=" * 60)
    print("TESTING RSA-2048 ENCRYPTION")
    print("=" * 60)
    
    try:
        from grid.crypto.rsa_handler import RSAHandler
        
        handler = RSAHandler()
        plaintext = "SECRET_CREDENTIAL_12345"
        
        ciphertext = handler.encrypt(plaintext.encode())
        decrypted = handler.decrypt(ciphertext).decode()
        
        assert decrypted == plaintext, f"Decryption mismatch: {decrypted} != {plaintext}"
        print(f"[OK] RSA Encrypt/Decrypt: {plaintext} -> {decrypted}")
        
        return []
    except Exception as e:
        print(f"[FAIL] RSA tests failed: {e}")
        traceback.print_exc()
        return [(e, traceback.format_exc())]

def test_blockchain():
    """Test blockchain functionality."""
    print("\n" + "=" * 60)
    print("TESTING BLOCKCHAIN")
    print("=" * 60)
    
    try:
        from grid.blockchain import Blockchain
        
        chain = Blockchain()
        
        # Add blocks
        chain.add_block("transaction1")
        chain.add_block("transaction2")
        
        assert len(chain.chain) == 3, f"Chain length wrong: {len(chain.chain)}"
        print(f"[OK] Blockchain blocks created: {len(chain.chain)}")
        
        # Verify chain
        is_valid = chain.is_chain_valid()
        assert is_valid, "Blockchain validation failed"
        print(f"[OK] Blockchain validation: VALID")
        
        return []
    except Exception as e:
        print(f"[FAIL] Blockchain tests failed: {e}")
        traceback.print_exc()
        return [(e, traceback.format_exc())]

def main():
    """Run all tests."""
    all_failures = []
    
    # Test imports
    import_failures = test_imports()
    all_failures.extend(import_failures)
    
    if import_failures:
        print("\n[WARN] Some imports failed, skipping functional tests")
        return 1
    
    # Test functionality
    keccak_failures = test_keccak256()
    all_failures.extend(keccak_failures)
    
    ascon_failures = test_ascon()
    all_failures.extend(ascon_failures)
    
    rsa_failures = test_rsa()
    all_failures.extend(rsa_failures)
    
    blockchain_failures = test_blockchain()
    all_failures.extend(blockchain_failures)
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    if all_failures:
        print(f"[FAIL] {len(all_failures)} test(s) failed")
        return 1
    else:
        print("[PASS] All tests passed successfully!")
        return 0

if __name__ == "__main__":
    sys.exit(main())
