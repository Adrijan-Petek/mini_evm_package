"""
mini_evm - a tiny stack-based smart contract VM for educational/demo purposes.

Features:
- Stack-based opcodes: PUSH, ADD, SUB, MUL, DIV, LOAD, STORE, CALL, RETURN, LOG
- Simple storage per contract (key -> integer)
- CALL into other contracts with gas accounting and nested call tracing
- Transaction-level snapshot: state changes commit only on success (revert on OOG/error)
- Call trace collection for visualization
"""

import time
from collections import defaultdict

class VMExecutionError(Exception):
    pass

class Contract:
    def __init__(self, address: str, code: list):
        self.address = address
        self.code = code[:]  # list of opcode strings
        self.storage = {}    # simple key->int storage

class World:
    def __init__(self):
        self.contracts = {}  # address -> Contract

    def deploy(self, address: str, code: list):
        if address in self.contracts:
            raise ValueError("Address already used")
        self.contracts[address] = Contract(address, code)

    def get_contract(self, address: str):
        return self.contracts.get(address)

class VM:
    OPCOST = {
        "PUSH": 1, "POP": 1,
        "ADD": 3, "SUB": 3, "MUL": 5, "DIV": 5,
        "LOAD": 5, "STORE": 20,
        "CALL": 10, "RETURN": 0,
        "LOG": 1
    }

    def __init__(self, world: World):
        self.world = world

    def execute_transaction(self, to_addr: str, caller: str, gas_limit: int, input_args: list):
        # Snapshot all storage: simple deep copy for demo purposes
        snapshot = {addr: dict(c.storage) for addr, c in self.world.contracts.items()}
        call_trace = []
        op_counts_total = defaultdict(int)
        start = time.perf_counter()
        try:
            ret, gas_used, op_counts = self._exec_contract_frame(to_addr, caller, gas_limit, list(input_args), snapshot, call_trace)
            # commit snapshot to real world
            for addr in snapshot:
                self.world.contracts[addr].storage = snapshot[addr]
            success = True
        except VMExecutionError as e:
            ret = None
            gas_used = gas_limit  # assume consumed
            success = False
            op_counts = {}
        duration = time.perf_counter() - start
        # aggregate op counts
        for k,v in op_counts.items():
            op_counts_total[k] += v
        return {
            "success": success,
            "return": ret,
            "gas_used": gas_used,
            "op_counts": dict(op_counts_total),
            "call_trace": call_trace,
            "duration_s": duration
        }

    def _exec_contract_frame(self, contract_addr: str, caller: str, gas_limit: int, stack: list, snapshot: dict, call_trace: list):
        if contract_addr not in self.world.contracts:
            raise VMExecutionError(f"Contract {contract_addr} not found")
        contract = self.world.contracts[contract_addr]
        code = contract.code
        ip = 0
        gas_remaining = gas_limit
        op_counts = defaultdict(int)
        # local reference to this contract's storage in snapshot
        local_storage = snapshot[contract_addr]

        # helper to charge gas
        def charge(op):
            nonlocal gas_remaining
            cost = self.OPCOST.get(op, 1)
            gas_remaining -= cost
            op_counts[op] += 1
            if gas_remaining < 0:
                raise VMExecutionError("Out of gas")

        while ip < len(code):
            instr = code[ip].strip()
            if instr == "":
                ip += 1
                continue
            parts = instr.split()
            op = parts[0].upper()
            # base gas cost
            charge(op)
            if op == "PUSH":
                if len(parts) < 2:
                    raise VMExecutionError("PUSH missing argument")
                val = int(parts[1])
                stack.append(val)
            elif op == "POP":
                if not stack:
                    raise VMExecutionError("POP from empty stack")
                stack.pop()
            elif op in ("ADD","SUB","MUL","DIV"):
                if len(stack) < 2:
                    raise VMExecutionError(f"{op} needs two operands")
                a = stack.pop()
                b = stack.pop()
                if op == "ADD":
                    stack.append(b + a)
                elif op == "SUB":
                    stack.append(b - a)
                elif op == "MUL":
                    stack.append(b * a)
                elif op == "DIV":
                    if a == 0:
                        raise VMExecutionError("Division by zero")
                    stack.append(b // a)
            elif op in ("LOAD","SLOAD"):
                if len(parts) < 2:
                    raise VMExecutionError("LOAD missing key")
                key = parts[1]
                stack.append(local_storage.get(key, 0))
            elif op in ("STORE","SSTORE"):
                if len(parts) < 2:
                    raise VMExecutionError("STORE missing key")
                key = parts[1]
                if not stack:
                    raise VMExecutionError("STORE needs a value on stack")
                val = stack.pop()
                local_storage[key] = val
            elif op == "LOG":
                if not stack:
                    raise VMExecutionError("LOG empty stack")
                val = stack.pop()
                call_trace.append({"type":"log","contract":contract_addr,"value":val})
            elif op == "CALL":
                # CALL <addr> <gas_amount> <nargs>
                if len(parts) < 4:
                    raise VMExecutionError("CALL needs addr, gas, nargs")
                callee = parts[1]
                gas_amount = int(parts[2])
                nargs = int(parts[3])
                if gas_remaining < gas_amount:
                    raise VMExecutionError("Insufficient gas for CALL")
                # pop nargs args (top-of-stack first)
                if len(stack) < nargs:
                    raise VMExecutionError("Not enough args for CALL")
                args = [stack.pop() for _ in range(nargs)][::-1]
                # reserve gas_amount
                gas_remaining -= gas_amount
                # execute callee with its own gas budget
                try:
                    ret, child_gas_used, child_op_counts = self._exec_contract_frame(callee, contract_addr, gas_amount, list(args), snapshot, call_trace)
                except VMExecutionError as e:
                    # child revert: propagate
                    raise
                # refund unused gas to caller
                gas_remaining += (gas_amount - child_gas_used)
                # merge child op counts into current
                for k,v in child_op_counts.items():
                    op_counts[k] += v
                # push return value (or 0 if None)
                stack.append(ret if ret is not None else 0)
                # record the call event
                call_trace.append({
                    "type":"call",
                    "caller": contract_addr,
                    "callee": callee,
                    "gas_provided": gas_amount,
                    "gas_used": child_gas_used,
                    "return": ret
                })
            elif op == "RETURN":
                # return top of stack if present
                ret = stack.pop() if stack else 0
                gas_used = gas_limit - gas_remaining
                return ret, gas_used, op_counts
            else:
                raise VMExecutionError(f"Unknown op {op}")
            ip += 1
        # if code finishes without RETURN, return top of stack
        ret = stack.pop() if stack else 0
        gas_used = gas_limit - gas_remaining
        return ret, gas_used, op_counts
