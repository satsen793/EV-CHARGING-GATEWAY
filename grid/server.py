from flask import Flask, request, jsonify
import json
import os
from datetime import datetime, timezone

from grid.registry import Registry
from grid.blockchain import Blockchain
from grid.crypto.rsa_handler import generate_keypair, decrypt_creds
from grid.crypto.ascon_handler import is_vfid_fresh
from grid.config import GRID_PORT, RSA_PRIVATE_KEY_PATH, RSA_PUBLIC_KEY_PATH, LEDGER_PATH, PIN_FAIL_LIMIT


app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

registry = Registry()
blockchain = Blockchain()

grid_private_key = None
grid_public_key = None

pin_fail_counter = {}
nonce_cache = set()


def load_or_generate_rsa_keys():
    global grid_private_key, grid_public_key
    
    if os.path.exists(RSA_PRIVATE_KEY_PATH) and os.path.exists(RSA_PUBLIC_KEY_PATH):
        with open(RSA_PRIVATE_KEY_PATH, 'rb') as f:
            grid_private_key = f.read()
        with open(RSA_PUBLIC_KEY_PATH, 'rb') as f:
            grid_public_key = f.read()
    else:
        grid_private_key, grid_public_key = generate_keypair()
        os.makedirs('keys', exist_ok=True)
        with open(RSA_PRIVATE_KEY_PATH, 'wb') as f:
            f.write(grid_private_key)
        with open(RSA_PUBLIC_KEY_PATH, 'wb') as f:
            f.write(grid_public_key)


def save_blockchain():
    with open(LEDGER_PATH, 'w') as f:
        json.dump(blockchain.to_list_of_dicts(), f, indent=2)


def load_blockchain():
    global blockchain
    if os.path.exists(LEDGER_PATH):
        with open(LEDGER_PATH, 'r') as f:
            blocks_data = json.load(f)
        blockchain.from_list_of_dicts(blocks_data)


@app.route('/api/register/franchise', methods=['POST'])
def register_franchise():
    try:
        data = request.get_json()
        name = data.get('name')
        zone_code = data.get('zoneCode')
        password = data.get('password')
        initial_balance = float(data.get('initialBalance', 5000.0))
        
        if not all([name, zone_code, password]):
            return jsonify({"error": "Missing required fields"}), 400
        
        fid = registry.register_franchise(name, zone_code, password, initial_balance)
        return jsonify({"fid": fid, "message": "Franchise registered successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/register/user', methods=['POST'])
def register_user():
    try:
        data = request.get_json()
        name = data.get('name')
        mobile = data.get('mobile')
        zone_code = data.get('zoneCode')
        password = data.get('password')
        pin = data.get('pin')
        initial_balance = float(data.get('initialBalance', 2000.0))
        
        if not all([name, mobile, zone_code, password, pin]):
            return jsonify({"error": "Missing required fields"}), 400
        
        uid, vmid = registry.register_user(name, mobile, zone_code, password, pin, initial_balance)
        return jsonify({"uid": uid, "vmid": vmid, "message": "User registered successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/authorize', methods=['POST'])
def authorize():
    try:
        data = request.get_json()
        encrypted_creds_b64 = data.get('encryptedCredentials')
        vfid_b64 = data.get('vfid')
        vfid_nonce_b64 = data.get('vfidNonce')
        vfid_timestamp = data.get('vfidTimestamp')
        
        import base64
        encrypted_creds = base64.b64decode(encrypted_creds_b64)
        vfid_nonce = base64.b64decode(vfid_nonce_b64)
        
        if not is_vfid_fresh(vfid_nonce):
            return jsonify({"approved": False, "message": "QR code expired"}), 200
        
        nonce_key = vfid_nonce.hex()
        if nonce_key in nonce_cache:
            return jsonify({"approved": False, "message": "Replay attack detected"}), 200
        nonce_cache.add(nonce_key)
        
        try:
            creds = decrypt_creds(encrypted_creds, grid_private_key)
        except Exception:
            return jsonify({"approved": False, "message": "Invalid credentials"}), 200
        
        vmid = creds.get('vmid')
        pin = creds.get('pin')
        amount = float(creds.get('amount', 0))
        
        user = registry.lookup_user_by_vmid(vmid)
        if not user:
            return jsonify({"approved": False, "message": "Unknown VMID"}), 200
        
        fail_key = f"{vmid}_session"
        if fail_key in pin_fail_counter and pin_fail_counter[fail_key] >= PIN_FAIL_LIMIT:
            return jsonify({"approved": False, "message": "PIN locked after failed attempts"}), 200
        
        if not registry.verify_pin(vmid, pin):
            pin_fail_counter[fail_key] = pin_fail_counter.get(fail_key, 0) + 1
            return jsonify({"approved": False, "message": "Invalid PIN"}), 200
        
        pin_fail_counter[fail_key] = 0
        
        if user.balance < amount:
            return jsonify({"approved": False, "message": "Insufficient balance"}), 200
        
        registry.deduct_balance(vmid, amount)
        
        fid_from_payload = vfid_b64
        registry.credit_balance(fid_from_payload, amount)
        
        block = blockchain.add_block(user.uid, fid_from_payload, amount, status="SUCCESS")
        save_blockchain()
        
        return jsonify({
            "approved": True,
            "txnId": block.txn_id,
            "message": "Transaction approved",
            "userBalance": user.balance
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/dispute', methods=['POST'])
def dispute():
    try:
        data = request.get_json()
        txn_id = data.get('txnId')
        reason = data.get('reason', 'User dispute')
        
        original_block = blockchain.find_block(txn_id)
        if not original_block:
            return jsonify({"error": "Transaction not found"}), 404
        
        user = registry.lookup_user_by_vmid(original_block.uid)
        if user:
            user.balance += original_block.amount
        
        reverse_block = blockchain.add_reverse(txn_id, reason)
        save_blockchain()
        
        return jsonify({
            "refunded": True,
            "reverseTxnId": reverse_block.txn_id,
            "refundAmount": original_block.amount
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/ledger', methods=['GET'])
def get_ledger():
    try:
        return jsonify(blockchain.to_list_of_dicts()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/ledger/verify', methods=['GET'])
def verify_ledger():
    try:
        is_valid = blockchain.is_valid()
        return jsonify({
            "valid": is_valid,
            "chainLength": len(blockchain.chain)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/grid/public-key', methods=['GET'])
def get_public_key():
    try:
        return jsonify({
            "publicKey": grid_public_key.decode('utf-8')
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    load_or_generate_rsa_keys()
    load_blockchain()
    app.run(host='0.0.0.0', port=GRID_PORT, debug=False)
