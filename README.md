# Mini-EVM: Stack-based Smart Contract VM (Educational Prototype)

This package implements a tiny stack-based VM supporting simple smart contracts, nested CALLs, per-contract storage, and gas accounting — intended for learning and experimentation.

## What's included
- `src/vm.py` — VM, World, Contract implementation
- `src/demo_mini_evm.py` — demo that deploys contracts, runs transactions, and generates charts
- `charts/` — generated PNG visualizations (gas per tx, time per tx, opcode usage, call flow)
- `outputs/` — results JSON and storage snapshot
- `requirements.txt` and `run_demo.sh` for convenience

## Quick start
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
./run_demo.sh
```

## How the VM works (brief)
- Contracts are simple lists of opcode strings.
- Each transaction executes against a *snapshot* of all contract storage; if execution succeeds, changes are committed; if it fails (out of gas or runtime error), state is reverted.
- CALL <addr> <gas> <nargs> pops nargs arguments from caller stack, executes callee with provided gas, and pushes the callee's return value.
- Gas is accounted per opcode; unused gas from a callee is refunded to the caller.

## Opcode reference
- `PUSH <n>` — push integer literal
- `POP` — pop top of stack
- `ADD`, `SUB`, `MUL`, `DIV` — arithmetic (integer)
- `LOAD <key>` — push storage[key] (0 if missing)
- `STORE <key>` — pop value and store at storage[key]
- `CALL <addr> <gas> <nargs>` — call another contract
- `RETURN` — return top-of-stack
- `LOG` — pop and record a log entry (saved in call_trace)

## Visuals produced by demo
- `charts/gas_per_tx.png` — gas used per transaction
- `charts/time_per_tx.png` — execution time per transaction
- `charts/opcode_usage.png` — aggregated opcode usage
- `charts/call_flow.png` — simple call-flow diagram showing CALLs between contracts

## Next steps / ideas
- Add more opcodes (e.g., JUMP, conditional ops)
- Support persistent accounts and balances
- Add ECDSA-signed transactions and a mempool
- Integrate with the on-chain search prototype to index logs/events

## License
MIT — use for learning and experimentation.
