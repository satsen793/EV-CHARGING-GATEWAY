from dataclasses import dataclass
from grid.crypto.hashing import generate_fid, generate_uid, generate_vmid, keccak256


@dataclass
class Provider:
    name: str
    zones: list


@dataclass
class FranchiseRecord:
    fid: str
    name: str
    zone_code: str
    password_hash: str
    balance: float
    created_at: str


@dataclass
class UserRecord:
    uid: str
    vmid: str
    name: str
    mobile: str
    zone_code: str
    password_hash: str
    pin_hash: str
    balance: float
    created_at: str


class Registry:
    def __init__(self):
        self.providers = {}
        self.franchises = {}
        self.users = {}
        self._init_providers()

    def _init_providers(self):
        self.providers = {
            "TP": Provider("Tata Power", ["TP-NORTH-01", "TP-SOUTH-02", "TP-WEST-03"]),
            "NTPC": Provider("NTPC", ["NTPC-NORTH-01", "NTPC-SOUTH-02", "NTPC-WEST-03"]),
            "REL": Provider("Reliance Energy", ["REL-NORTH-01", "REL-SOUTH-02", "REL-WEST-03"])
        }

    def register_franchise(self, name: str, zone_code: str, password: str, initial_balance: float) -> str:
        from datetime import datetime, timezone
        timestamp = datetime.now(timezone.utc).isoformat()
        password_hash = keccak256(password)
        fid = generate_fid(name, timestamp, password)
        
        franchise = FranchiseRecord(
            fid=fid,
            name=name,
            zone_code=zone_code,
            password_hash=password_hash,
            balance=initial_balance,
            created_at=timestamp
        )
        self.franchises[fid] = franchise
        return fid

    def register_user(self, name: str, mobile: str, zone_code: str, password: str, pin: str, initial_balance: float) -> tuple:
        from datetime import datetime, timezone
        timestamp = datetime.now(timezone.utc).isoformat()
        password_hash = keccak256(password)
        pin_hash = keccak256(pin)
        uid = generate_uid(name, timestamp, password)
        vmid = generate_vmid(uid, mobile)

        user = UserRecord(
            uid=uid,
            vmid=vmid,
            name=name,
            mobile=mobile,
            zone_code=zone_code,
            password_hash=password_hash,
            pin_hash=pin_hash,
            balance=initial_balance,
            created_at=timestamp
        )
        self.users[vmid] = user
        return uid, vmid

    def lookup_franchise(self, fid: str):
        return self.franchises.get(fid)

    def lookup_user_by_vmid(self, vmid: str):
        return self.users.get(vmid)

    def verify_pin(self, vmid: str, pin: str) -> bool:
        user = self.lookup_user_by_vmid(vmid)
        if not user:
            return False
        return user.pin_hash == keccak256(pin)

    def deduct_balance(self, vmid: str, amount: float) -> bool:
        user = self.lookup_user_by_vmid(vmid)
        if not user:
            return False
        if user.balance >= amount:
            user.balance -= amount
            return True
        return False

    def credit_balance(self, fid: str, amount: float) -> bool:
        franchise = self.lookup_franchise(fid)
        if not franchise:
            return False
        franchise.balance += amount
        return True

    def get_user_balance(self, vmid: str) -> float:
        user = self.lookup_user_by_vmid(vmid)
        return user.balance if user else 0.0

    def get_franchise_balance(self, fid: str) -> float:
        franchise = self.lookup_franchise(fid)
        return franchise.balance if franchise else 0.0
