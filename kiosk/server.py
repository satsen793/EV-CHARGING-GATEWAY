from flask import Flask, request, jsonify, send_file
from io import BytesIO
import base64
import time
import requests

from kiosk.config import KIOSK_PORT, GRID_URL, ASCON_KEY
from kiosk.crypto.ascon_handler import encrypt_vfid, decrypt_vfid
from kiosk.crypto.rsa_handler import encrypt_creds
import qrcode
import json


app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

kiosk_fid = None
kiosk_vfid_ciphertext = None
kiosk_vfid_nonce = None
kiosk_vfid_timestamp = None
kiosk_qr_image = None
grid_public_key = None


def fetch_grid_public_key():
    global grid_public_key
    try:
        response = requests.get(f"{GRID_URL}/api/grid/public-key", timeout=5)
        if response.status_code == 200:
            grid_public_key = response.json().get('publicKey').encode('utf-8')
    except Exception as e:
        print(f"Error fetching Grid public key: {e}")


def generate_vfid_and_qr():
    global kiosk_vfid_ciphertext, kiosk_vfid_nonce, kiosk_vfid_timestamp, kiosk_qr_image
    
    if not kiosk_fid:
        return False
    
    timestamp = int(time.time())
    kiosk_vfid_ciphertext, kiosk_vfid_nonce = encrypt_vfid(kiosk_fid, ASCON_KEY, timestamp)
    kiosk_vfid_timestamp = json.dumps({"timestamp": timestamp})
    
    qr_payload = {
        "vfid": base64.b64encode(kiosk_vfid_ciphertext).decode(),
        "nonce": base64.b64encode(kiosk_vfid_nonce).decode()
    }
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(json.dumps(qr_payload))
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    kiosk_qr_image = img_bytes.getvalue()
    
    return True


@app.route('/kiosk/load-fid', methods=['POST'])
def load_fid():
    global kiosk_fid
    try:
        data = request.get_json()
        fid = data.get('fid')
        
        if not fid or len(fid) != 16:
            return jsonify({"error": "Invalid FID format"}), 400
        
        kiosk_fid = fid
        if not generate_vfid_and_qr():
            return jsonify({"error": "Failed to generate QR"}), 500
        
        return jsonify({"message": "FID loaded", "qrReady": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/kiosk/qr', methods=['GET'])
def get_qr():
    try:
        if not kiosk_qr_image:
            return jsonify({"error": "No QR code available"}), 400
        
        return send_file(
            BytesIO(kiosk_qr_image),
            mimetype='image/png',
            as_attachment=True,
            download_name='qr_code.png'
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/kiosk/payment', methods=['POST'])
def payment():
    try:
        if not kiosk_fid or not kiosk_vfid_ciphertext or not kiosk_vfid_nonce:
            return jsonify({"approved": False, "message": "Kiosk not ready"}), 200
        
        data = request.get_json()
        vmid = data.get('vmid')
        pin = data.get('pin')
        amount = float(data.get('amount', 0))
        
        try:
            decrypted_fid = decrypt_vfid(kiosk_vfid_ciphertext, kiosk_vfid_nonce, ASCON_KEY)
            if decrypted_fid != kiosk_fid:
                return jsonify({"approved": False, "message": "VFID validation failed"}), 200
        except Exception:
            return jsonify({"approved": False, "message": "Invalid VFID"}), 200
        
        if not grid_public_key:
            return jsonify({"approved": False, "message": "Grid public key not available"}), 200
        
        encrypted_creds = encrypt_creds(vmid, pin, amount, grid_public_key)
        
        grid_payload = {
            "encryptedCredentials": base64.b64encode(encrypted_creds).decode(),
            "vfid": base64.b64encode(kiosk_vfid_ciphertext).decode(),
            "vfidNonce": base64.b64encode(kiosk_vfid_nonce).decode(),
            "vfidTimestamp": json.loads(kiosk_vfid_timestamp)["timestamp"]
        }
        
        try:
            response = requests.post(f"{GRID_URL}/api/authorize", json=grid_payload, timeout=10)
            if response.status_code == 200:
                auth_result = response.json()
                
                if auth_result.get('approved'):
                    return jsonify({
                        "approved": True,
                        "message": "Transaction approved. Charging authorized.",
                        "txnId": auth_result.get('txnId'),
                        "userBalance": auth_result.get('userBalance')
                    }), 200
                else:
                    return jsonify({
                        "approved": False,
                        "message": auth_result.get('message', 'Transaction rejected')
                    }), 200
            else:
                return jsonify({"approved": False, "message": "Grid returned error"}), 200
        except requests.Timeout:
            return jsonify({"approved": False, "message": "Grid server unreachable (timeout)"}), 200
        except Exception as e:
            return jsonify({"approved": False, "message": f"Communication error: {str(e)}"}), 200
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    fetch_grid_public_key()
    app.run(host='0.0.0.0', port=KIOSK_PORT, debug=False)
