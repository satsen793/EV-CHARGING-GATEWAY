from dataclasses import dataclass, field
from grid.crypto.hashing import hash_block


@dataclass
class Block:
    index: int
    txn_id: str
    previous_hash: str
    timestamp: str
    uid: str
    fid: str
    amount: float
    status: str
    dispute_flag: bool = False
    block_hash: str = field(default="", init=False)

    def compute_hash(self) -> str:
        return hash_block(self.index, self.txn_id, self.previous_hash, self.timestamp,
                         self.uid, self.fid, self.amount, self.status, self.dispute_flag)

    def seal(self):
        self.block_hash = self.compute_hash()

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "txn_id": self.txn_id,
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
            "uid": self.uid,
            "fid": self.fid,
            "amount": self.amount,
            "status": self.status,
            "dispute_flag": self.dispute_flag,
            "block_hash": self.block_hash
        }


class Blockchain:
    def __init__(self):
        self.chain = []
        self._add_genesis_block()

    def _add_genesis_block(self):
        from datetime import datetime, timezone
        genesis = Block(
            index=0,
            txn_id="GENESIS",
            previous_hash="0" * 64,
            timestamp=datetime.now(timezone.utc).isoformat(),
            uid="SYSTEM",
            fid="SYSTEM",
            amount=0.0,
            status="GENESIS"
        )
        genesis.seal()
        self.chain.append(genesis)

    def add_block(self, uid: str, fid: str, amount: float, status: str = "SUCCESS") -> Block:
        from datetime import datetime, timezone
        from grid.crypto.hashing import generate_txn_id

        prev = self.chain[-1]
        timestamp = datetime.now(timezone.utc).isoformat()
        txn_id = generate_txn_id(uid, fid, timestamp, str(amount))

        block = Block(
            index=len(self.chain),
            txn_id=txn_id,
            previous_hash=prev.block_hash,
            timestamp=timestamp,
            uid=uid,
            fid=fid,
            amount=amount,
            status=status
        )
        block.seal()
        self.chain.append(block)
        return block

    def find_block(self, txn_id: str):
        for block in self.chain:
            if block.txn_id == txn_id:
                return block
        return None

    def add_reverse(self, original_txn_id: str, reason: str = "User dispute") -> Block:
        original = self.find_block(original_txn_id)
        if not original:
            raise ValueError(f"Original transaction {original_txn_id} not found")

        reverse_block = self.add_block(
            uid=original.uid,
            fid=original.fid,
            amount=-original.amount,
            status="REVERSED"
        )
        reverse_block.dispute_flag = True
        reverse_block.seal()
        return reverse_block

    def is_valid(self) -> bool:
        for i in range(len(self.chain)):
            block = self.chain[i]
            if block.block_hash != block.compute_hash():
                return False
            if i > 0:
                prev_block = self.chain[i - 1]
                if block.previous_hash != prev_block.block_hash:
                    return False
        return True

    def to_list_of_dicts(self) -> list:
        return [block.to_dict() for block in self.chain]

    def from_list_of_dicts(self, blocks_data: list):
        self.chain = []
        for block_data in blocks_data:
            block = Block(
                index=block_data["index"],
                txn_id=block_data["txn_id"],
                previous_hash=block_data["previous_hash"],
                timestamp=block_data["timestamp"],
                uid=block_data["uid"],
                fid=block_data["fid"],
                amount=block_data["amount"],
                status=block_data["status"],
                dispute_flag=block_data.get("dispute_flag", False)
            )
            block.block_hash = block_data["block_hash"]
            self.chain.append(block)
