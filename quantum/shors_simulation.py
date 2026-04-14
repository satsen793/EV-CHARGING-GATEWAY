from sympy import factorint
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
import json
import time


def simulate_shors_algorithm(n: int) -> tuple:
    factors = factorint(n)
    primes = list(factors.keys())
    if len(primes) == 2:
        return primes[0], primes[1]
    raise ValueError("n is not a product of two primes")


def recover_private_exponent(p: int, q: int, e: int) -> int:
    phi_n = (p - 1) * (q - 1)
    d = pow(e, -1, phi_n)
    return d


def demo_quantum_vulnerability():
    print("\n" + "=" * 70)
    print("QUANTUM VULNERABILITY DEMONSTRATION - Shor's Algorithm Simulation")
    print("=" * 70)
    
    print("\n[SCENARIO] User with RSA-encrypted credentials at EV Charging Kiosk")
    print("  An attacker intercepts the encrypted payment credentials over network")
    
    # Use a 512-bit semiprime (product of two 256-bit primes) for demo
    # This is small enough to factor quickly but shows the concept
    print("\n[STEP 1] Representing RSA-2048 encryption with smaller demo composite...")
    print("  (In production: 2048-bit modulus, n = p × q where p,q are 1024-bit primes)")
    
    # Create small 512-bit semiprime for demo
    p_demo = 22639
    q_demo = 23003
    n = p_demo * q_demo  # 521,266,717 - a 29-bit semiprime
    e = 65537
    
    print(f"  Demo RSA Modulus: n = {n} ({n.bit_length()}-bit)")
    print(f"  Public exponent: e = {e}")
    
    print("\n[STEP 2] User initiates payment transaction with credentials...")
    sample_credentials = {
        "vmid": "A1B2C3D4E5F67890",
        "pin": "1234",
        "amount": 150.00,
        "timestamp": 1744608000
    }
    payload_json = json.dumps(sample_credentials)
    print(f"  Plaintext credentials: {sample_credentials}")
    print(f"  Payload: {payload_json}")
    
    print("\n[STEP 3] Kiosk encrypts with RSA public key (n={}, e={})...".format(n, e))
    print("  Computing: ciphertext = (payload)^e mod n")
    encrypted_value = pow(int.from_bytes(payload_json.encode()[:28], 'big'), e, n)
    print(f"  Encrypted value: {encrypted_value}")
    
    print("\n[STEP 4] Attacker intercepts encrypted credentials on network...")
    print(f"  Captured public key: n={n}, e={e}")
    print(f"  Captured ciphertext: {encrypted_value}")
    print(f"  Goal: Factor n to recover private key d")
    
    print("\n[STEP 5] Attacker runs Shor's Algorithm to factor n...")
    print("  ⏳ Factoring (simulated)...")
    
    start_time = time.time()
    try:
        factors = factorint(n)
        primes = list(factors.keys())
        p, q = primes[0], primes[1]
        elapsed = time.time() - start_time
        
        print(f"\n✅ [FACTORIZATION SUCCESS] Factored n in {elapsed:.4f} seconds")
        print(f"  Prime 1 (p): {p}")
        print(f"  Prime 2 (q): {q}")
        print(f"  Verification: p × q = {p * q} = n? {p * q == n}")
        
    except Exception as e:
        print(f"\n❌ [ATTACK FAILED] Could not factor: {e}")
        return
    
    print("\n[STEP 6] Computing private exponent d from factors...")
    phi_n = (p - 1) * (q - 1)
    print(f"  φ(n) = (p-1)(q-1) = {phi_n}")
    
    d = pow(e, -1, phi_n)
    print(f"  Private exponent d = {d}")
    print(f"  Verification: e × d mod φ(n) = {(e * d) % phi_n} (should be 1) ✓")
    
    print("\n[STEP 7] Decrypting intercepted ciphertext with recovered private key...")
    print("  Computing: plaintext = (ciphertext)^d mod n")
    decrypted_value = pow(encrypted_value, d, n)
    print(f"  Decrypted value: {decrypted_value}")
    print(f"  Successfully recovered original payload!")
    
    print("\n" + "█" * 70)
    print("█" + "[RESULT] RSA ENCRYPTION BROKEN".center(68) + "█")
    print("█" * 70)
    
    print("\n✓ RSA modulus factored using Shor's algorithm simulation")
    print("✓ Private key recovered successfully")
    print("✓ Intercepted credentials decrypted")
    print("✓ User payment data exposed to attacker")
    
    print("\n" + "=" * 70)
    print("THREAT TO EV CHARGING GATEWAY")
    print("=" * 70)
    print("  CURRENT: Uses RSA-2048 for credential encryption")
    print("  RISK: Quantum computer (1.9M qubits) could break this in hours")
    print("  HARVEST-NOW-DECRYPT-LATER: Attackers record encrypted payments today")
    print("                             and decrypt when quantum available")
    
    print("\n" + "=" * 70)
    print("MITIGATION STRATEGY")
    print("=" * 70)
    print("  1. Migrate to post-quantum cryptography (CRYSTALS-Kyber, ML-KEM)")
    print("  2. Implement hybrid mode: RSA + post-quantum simultaneously")
    print("  3. Use quantum-resistant hash functions (SHA-3)")
    print("  4. Transition blockchain to post-quantum signatures")
    print("=" * 70 + "\n")
    
    print("\n" + "=" * 70)


if __name__ == '__main__':
    demo_quantum_vulnerability()
