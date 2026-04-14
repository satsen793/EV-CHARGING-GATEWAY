#!/usr/bin/env python
"""
QUANTUM VULNERABILITY DEMONSTRATION
====================================

This script demonstrates the quantum threat to RSA encryption
using Shor's algorithm simulation.

Run with:
  python QUANTUM_DEMO.py
"""

from quantum.shors_simulation import demo_quantum_vulnerability

if __name__ == "__main__":
    print("\n" + "█" * 70)
    print("█" + " " * 68 + "█")
    print("█" + "  QUANTUM COMPUTING THREAT TO EV CHARGING GATEWAY".center(68) + "█")
    print("█" + " " * 68 + "█")
    print("█" * 70)
    
    # Run the quantum vulnerability demonstration
    demo_quantum_vulnerability()
    
    print("\n" + "=" * 70)
    print("DEMONSTRATION COMPLETE")
    print("=" * 70)
    print("\nThis simulation shows why quantum computing threatens current")
    print("cryptography. The EV Charging Gateway uses RSA-2048 which would be")
    print("broken by a sufficiently powerful quantum computer.")
    print("\nMitigation: Implement post-quantum cryptography (e.g., CRYSTALS-Kyber)")
    print("=" * 70 + "\n")
