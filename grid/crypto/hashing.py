from Crypto.Hash import keccak
import json


def keccak256(data: str) -> str:
    k = keccak.new(digest_bits=256)
    k.update(data.encode('utf-8'))
    return k.hexdigest()


def generate_fid(name: str, created_at: str, password: str) -> str:
    raw = name + created_at + password
    return keccak256(raw)[:16].upper()


def generate_uid(name: str, created_at: str, password: str) -> str:
    raw = name + created_at + password
    return keccak256(raw)[:16].upper()


def generate_vmid(uid: str, mobile: str) -> str:
    raw = uid + mobile
    return keccak256(raw)[:16].upper()


def generate_txn_id(uid: str, fid: str, timestamp: str, amount: str) -> str:
    raw = uid + fid + timestamp + amount
    return keccak256(raw)


def hash_block(index: int, txn_id: str, prev_hash: str, timestamp: str,
               uid: str, fid: str, amount: float, status: str, dispute: bool) -> str:
    block_dict = {
        "index": index,
        "txn_id": txn_id,
        "previous_hash": prev_hash,
        "timestamp": timestamp,
        "uid": uid,
        "fid": fid,
        "amount": amount,
        "status": status,
        "dispute_flag": dispute
    }
    content = json.dumps(block_dict, sort_keys=True)
    return keccak256(content)
