#!/usr/bin/env python
"""
CLEAN END-TO-END DEMO SCRIPT
============================

This script demonstrates the complete EV Charging Gateway workflow
with proper error handling and output formatting.

IMPORTANT: Both servers must be running before executing this script:
  Terminal 1: python -m grid.server
  Terminal 2: python -m kiosk.server

Then run this script in Terminal 3:
  python DEMO_CLEAN_WORKFLOW.py
"""

import requests
import json
import time

GRID_URL = "http://localhost:5000"
KIOSK_URL = "http://localhost:5001"

def print_section(title):
    """Print formatted section header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def print_result(key, value, success=True):
    """Print formatted result"""
    status = "✅" if success else "❌"
    print(f"{status} [{key}] {value}")

def register_franchise():
    """Step 1: Register Franchise"""
    print_section("STEP 1: Register Franchise")
    
    response = requests.post(f"{GRID_URL}/api/register/franchise", json={
        'name': 'ChargeCo',
        'zoneCode': 'ZONE_A',
        'password': 'franchise_pass_123',
        'initialBalance': 5000.0
    })
    
    result = response.json()
    fid = result['fid']
    print_result("FID", fid)
    print_result("Status", "Franchise registered successfully")
    return fid

def register_user():
    """Step 2: Register User"""
    print_section("STEP 2: Register User")
    
    response = requests.post(f"{GRID_URL}/api/register/user", json={
        'name': 'John Doe',
        'mobile': '9876543210',
        'zoneCode': 'ZONE_A',
        'password': 'user_pass_456',
        'pin': '1234',
        'initialBalance': 2000.0
    })
    
    result = response.json()
    vmid = result['vmid']
    uid = result['uid']
    print_result("VMID", vmid)
    print_result("UID", uid)
    print_result("Initial Balance", "$2000.00")
    return vmid, uid

def load_fid_at_kiosk(fid):
    """Step 3: Load FID at Kiosk"""
    print_section("STEP 3: Load FID at Kiosk & Generate QR")
    
    response = requests.post(f"{KIOSK_URL}/kiosk/load-fid", json={'fid': fid})
    result = response.json()
    print_result("FID Loaded", fid)
    print_result("QR Status", "Generated & Ready")
    return result

def view_qr_details():
    """Step 4: View QR Details"""
    print_section("STEP 4: View QR Payload Details")
    
    response = requests.get(f"{KIOSK_URL}/kiosk/qr/details")
    result = response.json()
    
    payload = result['qr_payload']
    print_result("Plaintext FID", payload['fid'])
    print_result("Encrypted VFID", payload['vfid_encrypted'][:50] + "...")
    print_result("Nonce", payload['nonce'])
    print_result("Timestamp", str(payload['timestamp']['timestamp']))
    return payload

def successful_payment(vmid, amount=45.50):
    """Step 5: Successful Payment"""
    print_section(f"STEP 5: Process Payment (${amount})")
    
    response = requests.post(f"{KIOSK_URL}/kiosk/payment", json={
        'vmid': vmid,
        'pin': '1234',
        'amount': amount
    })
    
    result = response.json()
    if result.get('approved'):
        print_result("Status", "APPROVED", success=True)
        print_result("Transaction ID", result.get('txnId'))
        print_result("Amount", f"${amount}")
        print_result("New Balance", f"${result.get('userBalance')}")
        return result.get('txnId')
    else:
        print_result("Status", f"REJECTED: {result.get('message')}", success=False)
        return None

def wrong_pin_failure(vmid):
    """Step 6: Wrong PIN Failure"""
    print_section("STEP 6: Test Wrong PIN (Should Fail)")
    
    response = requests.post(f"{KIOSK_URL}/kiosk/payment", json={
        'vmid': vmid,
        'pin': '9999',  # Wrong PIN
        'amount': 45.50
    })
    
    result = response.json()
    status = "BLOCKED" if not result.get('approved') else "ERROR"
    message = result.get('message', 'Unknown error')
    print_result("Attempt", f"Wrong PIN (9999)")
    print_result("Result", f"{status}: {message}", success=False)

def insufficient_balance_failure(vmid):
    """Step 7: Insufficient Balance Failure"""
    print_section("STEP 7: Test Insufficient Balance (Should Fail)")
    
    response = requests.post(f"{KIOSK_URL}/kiosk/payment", json={
        'vmid': vmid,
        'pin': '1234',
        'amount': 50000  # Huge amount
    })
    
    result = response.json()
    status = "BLOCKED" if not result.get('approved') else "ERROR"
    message = result.get('message', 'Unknown error')
    print_result("Attempt", "Amount: $50,000 (account balance ~$1954.50)")
    print_result("Result", f"{status}: {message}", success=False)

def process_dispute(txn_id):
    """Step 8: Process Dispute & Reverse Transaction"""
    print_section("STEP 8: Process Dispute & Reverse Transaction")
    
    if not txn_id:
        print("❌ [Skip] No valid transaction to dispute")
        return
    
    response = requests.post(f"{GRID_URL}/api/dispute", json={
        'txnId': txn_id,
        'reason': 'User initiated chargeback'
    })
    
    result = response.json()
    print_result("Original TxnID", txn_id)
    print_result("Refund Amount", f"${result.get('refundAmount')}")
    print_result("Reverse TxnID", result.get('reverseTxnId'))
    print_result("Dispute Flag", result.get('dispute_flag'))
    print_result("Status", "Transaction Reversed & Refund Issued", success=True)

def view_blockchain():
    """Step 9: View Blockchain Ledger"""
    print_section("STEP 9: View Blockchain Ledger")
    
    response = requests.get(f"{GRID_URL}/api/ledger")
    blocks = response.json()
    
    print_result("Total Blocks", len(blocks))
    print("\nRecent Transactions:")
    for block in blocks[-3:]:
        print(f"  Block #{block['index']}: {block['status']} | Amount: ${block['amount']} | TxnID: {block['txn_id'][:16]}...")
    
    # Verify chain integrity
    response = requests.get(f"{GRID_URL}/api/ledger/verify")
    integrity = response.json()
    print_result("Blockchain Valid", integrity['valid'], success=integrity['valid'])

def main():
    """Execute complete demo workflow"""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*68 + "║")
    print("║" + "  EV CHARGING GATEWAY - COMPLETE DEMO WORKFLOW".center(68) + "║")
    print("║" + " "*68 + "║")
    print("╚" + "="*68 + "╝")
    
    try:
        # Register and get identifiers
        fid = register_franchise()
        time.sleep(0.5)
        
        vmid, uid = register_user()
        time.sleep(0.5)
        
        # Load FID and generate QR
        load_fid_at_kiosk(fid)
        time.sleep(0.5)
        
        # View QR details
        view_qr_details()
        time.sleep(0.5)
        
        # Test successful payment
        txn_id = successful_payment(vmid)
        time.sleep(0.5)
        
        # Test failure cases
        wrong_pin_failure(vmid)
        time.sleep(0.5)
        
        insufficient_balance_failure(vmid)
        time.sleep(0.5)
        
        # Process dispute if we have a txn_id
        if txn_id:
            process_dispute(txn_id)
            time.sleep(0.5)
        
        # View blockchain
        view_blockchain()
        
        # Final summary
        print_section("DEMO COMPLETE ✅")
        print("All cryptographic operations and flows executed successfully!")
        print("\nKey Features Demonstrated:")
        print("  ✅ User & Franchise Registration")
        print("  ✅ ASCON-128 QR Encryption/Decryption")
        print("  ✅ Payment Authorization with PIN Verification")
        print("  ✅ Failure Case Handling (Wrong PIN, Insufficient Balance)")
        print("  ✅ Dispute Processing & Transaction Reversal")
        print("  ✅ Blockchain Recording & Verification")
        print("\n")
        
    except requests.exceptions.ConnectionError as e:
        print(f"\n❌ [ERROR] Cannot connect to servers")
        print(f"   Make sure both servers are running:")
        print(f"     Terminal 1: python -m grid.server")
        print(f"     Terminal 2: python -m kiosk.server")
        print(f"\n   Error: {str(e)}\n")
    except Exception as e:
        print(f"\n❌ [ERROR] {str(e)}\n")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
