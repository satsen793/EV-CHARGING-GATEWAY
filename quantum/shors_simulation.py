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
    
    print("\n[STEP 1] Generating small RSA key for factoring demo (512-bit)...")
    small_key = RSA.generate(512)
    n = small_key.n
    e = small_key.e
    print(f"  RSA Public Key: n={n}, e={e}")
    print(f"  n bit length: {n.bit_length()}")
    
    print("\n[STEP 2] Simulating user payment transaction...")
    sample_credentials = {
        "vmid": "A1B2C3D4E5F67890",
        "pin": "1234",
        "amount": 150.00
    }
    payload_json = json.dumps(sample_credentials).encode('utf-8')
    print(f"  Plaintext credentials: {sample_credentials}")
    
    cipher = PKCS1_OAEP.new(small_key.publickey())
    encrypted_payload = cipher.encrypt(payload_json)
    print(f"  Encrypted payload (hex): {encrypted_payload.hex()[:64]}...")
    print(f"  Ciphertext length: {len(encrypted_payload)} bytes")
    
    print("\n[STEP 3] Intercepting encrypted credentials on network...")
    print(f"  Intercepted ciphertext stored for attack")
    
    print("\n[STEP 4] Attacker runs Shor's Algorithm simulation to factor n...")
    print(f"  This would take centuries on classical computer")
    print(f"  But we demonstrate the principle with classical factoring...")
    
    start_time = time.time()
    try:
        p, q = simulate_shors_algorithm(n)
        elapsed = time.time() - start_time
        
        print(f"\n[ATTACK SUCCESS] Factored n in {elapsed:.3f} seconds")
        print(f"  Prime 1 (p): {p}")
        print(f"  Prime 2 (q): {q}")
        print(f"  Verification: p × q = {p * q} = n? {p * q == n}")
        
    except Exception as e:
        print(f"\n[ATTACK FAILED] Could not factor: {e}")
        return
    
    print("\n[STEP 5] Computing private key from recovered factors...")
    phi_n = (p - 1) * (q - 1)
    print(f"  φ(n) = (p-1)(q-1) = {phi_n}")
    
    d = recover_private_exponent(p, q, e)
    print(f"  Private exponent d = {d}")
    print(f"  Verification: e × d mod φ(n) = {(e * d) % phi_n} (should be 1)")
    
    print("\n[STEP 6] Reconstructing private key and decrypting ciphertext...")
    recovered_private_key = RSA.construct((n, e, d, p, q))
    recovered_cipher = PKCS1_OAEP.new(recovered_private_key)
    
    try:
        decrypted_payload = recovered_cipher.decrypt(encrypted_payload)
        decrypted_creds = json.loads(decrypted_payload.decode('utf-8'))
        print(f"  Decryption successful!")
        print(f"  Recovered credentials: {decrypted_creds}")
        
    except Exception as e:
        print(f"  Decryption failed: {e}")
        return
    
    print("\n[RESULT] CLASSICAL CRYPTOGRAPHY IS BROKEN")
    print("  • RSA modulus factored using Shor's algorithm (simulated)")
    print("  • Private key recovered successfully")
    print("  • Intercepted credentials decrypted")
    print("  • User payment data exposed")
    
    print("\n[IMPLICATIONS]")
    print("  • Post-quantum migration needed immediately")
    print("  • Replace RSA-2048 with CRYSTALS-Kyber or similar")
    print("  • All archived RSA-encrypted data is already compromised")
    
    print("\n" + "=" * 70)


if __name__ == '__main__':
    demo_quantum_vulnerability()
