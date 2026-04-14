import requests
import base64
import json
import io
from PIL import Image
import qrcode
from datetime import datetime, timezone


GRID_URL = "http://localhost:5000"
KIOSK_URL = "http://localhost:5001"


def register_user():
    try:
        print("\n=== User Registration ===")
        name = input("Enter name: ")
        mobile = input("Enter mobile number (10 digits): ")
        zone_code = input("Enter zone code (e.g., TP-NORTH-01): ")
        password = input("Enter password: ")
        pin = input("Enter PIN (4 digits): ")
        initial_balance = float(input("Enter initial balance (default 2000): ") or "2000")
        
        payload = {
            "name": name,
            "mobile": mobile,
            "zoneCode": zone_code,
            "password": password,
            "pin": pin,
            "initialBalance": initial_balance
        }
        
        response = requests.post(f"{GRID_URL}/api/register/user", json=payload, timeout=5)
        if response.status_code == 200:
            result = response.json()
            uid = result.get('uid')
            vmid = result.get('vmid')
            print(f"\nRegistration successful!")
            print(f"UID: {uid}")
            print(f"VMID: {vmid}")
            return vmid
        else:
            print(f"Registration failed: {response.text}")
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None


def scan_and_pay():
    try:
        print("\n=== Scan QR & Make Payment ===")
        vmid = input("Enter your VMID: ")
        pin = input("Enter your PIN: ")
        amount = float(input("Enter charging amount: "))
        
        qr_image_path = input("Enter path to QR code image (or press Enter to fetch from kiosk): ").strip()
        
        if not qr_image_path:
            response = requests.get(f"{KIOSK_URL}/kiosk/qr", timeout=5)
            if response.status_code != 200:
                print("Failed to fetch QR code from kiosk")
                return
            
            qr_image = Image.open(io.BytesIO(response.content))
            qr_image_path = "/tmp/qr_temp.png"
            qr_image.save(qr_image_path)
        
        decoder_available = False
        try:
            from pyzbar.pyzbar import decode
            qr_image = Image.open(qr_image_path)
            decoded_objects = decode(qr_image)
            if decoded_objects:
                qr_data_str = decoded_objects[0].data.decode('utf-8')
                qr_data = json.loads(qr_data_str)
                decoder_available = True
        except Exception:
            pass
        
        if not decoder_available:
            print("QR decoder not available. Manually enter QR data.")
            print("QR should contain: {\"vfid\": \"...\", \"nonce\": \"...\"}")
            qr_data_str = input("Enter QR data JSON: ")
            qr_data = json.loads(qr_data_str)
        
        vfid_b64 = qr_data.get('vfid')
        nonce_b64 = qr_data.get('nonce')
        
        if not vfid_b64 or not nonce_b64:
            print("Invalid QR data")
            return
        
        payload = {
            "vmid": vmid,
            "pin": pin,
            "amount": amount
        }
        
        response = requests.post(f"{KIOSK_URL}/kiosk/payment", json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('approved'):
                print(f"\n✓ Payment Approved!")
                print(f"Transaction ID: {result.get('txnId')}")
                print(f"Message: {result.get('message')}")
                print(f"New Balance: {result.get('userBalance')}")
            else:
                print(f"\n✗ Payment Rejected")
                print(f"Reason: {result.get('message')}")
        else:
            print(f"Payment failed: {response.text}")
    except Exception as e:
        print(f"Error: {e}")


def view_balance():
    try:
        print("\n=== View Balance ===")
        vmid = input("Enter your VMID: ")
        
        response = requests.get(f"{GRID_URL}/api/ledger", timeout=5)
        if response.status_code == 200:
            blocks = response.json()
            print(f"\nTotal transactions: {len(blocks) - 1}")
            
            total_spent = 0
            user_blocks = [b for b in blocks if b.get('vmid') == vmid or vmid in json.dumps(b)]
            
            for block in blocks:
                if block.get('uid') and block.get('status') == 'SUCCESS':
                    pass
            
            print("Note: Full balance tracking requires user ID lookup on Grid")
            print("For demo, check your transaction details above")
    except Exception as e:
        print(f"Error: {e}")


def main():
    print("=" * 50)
    print("EV CHARGING GATEWAY - USER APP")
    print("=" * 50)
    
    while True:
        print("\n1. Register User")
        print("2. Scan QR & Make Payment")
        print("3. View Balance")
        print("0. Exit")
        
        choice = input("\nEnter choice: ").strip()
        
        if choice == '1':
            register_user()
        elif choice == '2':
            scan_and_pay()
        elif choice == '3':
            view_balance()
        elif choice == '0':
            print("Goodbye!")
            break
        else:
            print("Invalid choice")


if __name__ == '__main__':
    main()
