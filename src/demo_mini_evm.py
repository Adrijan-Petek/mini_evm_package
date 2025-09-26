"""
demo_mini_evm.py - deploys two contracts and executes transactions that call them.
Generates charts and outputs for visualization.
"""
import json, time
from pathlib import Path
import matplotlib.pyplot as plt
from vm import World, VM

OUT = Path(__file__).parent.parent / "outputs"
CHARTS = Path(__file__).parent.parent / "charts"
OUT.mkdir(exist_ok=True)
CHARTS.mkdir(exist_ok=True)

# Define two contracts:
# Contract A: increments 'counter' by input arg and returns new value
contract_a_code = [
    "LOAD counter",    # push current counter
    "ADD",             # add input arg (already on stack)
    "STORE counter",   # store new counter
    "LOAD counter",    # push return value
    "RETURN"
]

# Contract B: calls A with arg 2, multiplies result by 10, stores to 'myvalue' and returns it
contract_b_code = [
    "PUSH 2",
    "CALL A 200 1",  # call contract A with gas=200 and 1 arg
    "PUSH 10",
    "MUL",
    "STORE myvalue",
    "LOAD myvalue",
    "RETURN"
]

# Deploy world and contracts
world = World()
world.deploy("A", contract_a_code)
world.deploy("B", contract_b_code)
vm = VM(world)

# Transactions to execute
txs = [
    {"from":"alice","to":"A","gas":500,"args":[7]},
    {"from":"bob","to":"B","gas":800,"args":[]} ,
    {"from":"carol","to":"A","gas":300,"args":[3]},
    {"from":"dave","to":"B","gas":800,"args":[]} ,
]

results = []
for tx in txs:
    print(f"Executing tx -> to: {tx['to']} from: {tx['from']} gas: {tx['gas']} args: {tx['args']}")
    res = vm.execute_transaction(tx["to"], tx["from"], tx["gas"], tx["args"])
    print("  result:", res["success"], "return:", res["return"], "gas_used:", res["gas_used"])
    results.append({"tx": tx, "res": res})

# Save outputs
with open(OUT / "tx_results.json","w") as f:
    json.dump(results, f, indent=2)

# Aggregate metrics for charts
gas_used = [r["res"]["gas_used"] for r in results]
durations = [r["res"]["duration_s"] for r in results]

# Aggregate opcode counts
from collections import defaultdict
op_counts = defaultdict(int)
for r in results:
    for k,v in r["res"]["op_counts"].items():
        op_counts[k] += v

# Chart: gas used per transaction
plt.figure()
plt.bar(range(len(gas_used)), gas_used)
plt.xlabel("Transaction index")
plt.ylabel("Gas used")
plt.title("Gas used per transaction")
plt.tight_layout()
plt.savefig(CHARTS / "gas_per_tx.png")
plt.close()

# Chart: execution time per tx
plt.figure()
plt.bar(range(len(durations)), durations)
plt.xlabel("Transaction index")
plt.ylabel("Execution time (s)")
plt.title("Execution time per transaction")
plt.tight_layout()
plt.savefig(CHARTS / "time_per_tx.png")
plt.close()

# Chart: opcode counts
plt.figure()
plt.bar(list(op_counts.keys()), list(op_counts.values()))
plt.xlabel("Opcode")
plt.ylabel("Count")
plt.title("Opcode usage across transactions")
plt.tight_layout()
plt.savefig(CHARTS / "opcode_usage.png")
plt.close()

# Call flow visualization (simple boxes + arrows)
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrow
fig, ax = plt.subplots(figsize=(8,3))
ax.axis('off')

# Unique nodes in order of appearance
positions = {"TX Origin": (0.5, 1.5)}
x = 2.0
y = 1.5
# collect call events across all txs
events = []
for r in results:
    for ev in r["res"]["call_trace"]:
        if ev["type"] == "call":
            events.append(ev)
# nodes: include caller and callee addresses
for ev in events:
    for n in (ev["caller"], ev["callee"]):
        if n not in positions:
            positions[n] = (x, y)
            x += 2.0

# draw boxes
for name, (xx, yy) in positions.items():
    rect = Rectangle((xx-0.6, yy-0.25), 1.2, 0.5, fill=False)
    ax.add_patch(rect)
    ax.text(xx, yy, name, ha='center', va='center')

# draw arrows for events
for i, ev in enumerate(events):
    caller = ev["caller"]
    callee = ev["callee"]
    cx, cy = positions[caller]
    txx, tyy = positions[callee]
    ax.annotate("", xy=(txx-0.6, tyy), xytext=(cx+0.6, cy), arrowprops=dict(arrowstyle="->"))
    # annotate gas used above arrow
    mx = (cx + txx)/2
    my = cy + 0.1 + (i%2)*0.05
    ax.text(mx, my, f"gas={ev['gas_used']}", ha='center', va='bottom', fontsize=8)

ax.set_title("Call flow (across transactions)")
plt.tight_layout()
plt.savefig(CHARTS / "call_flow.png")
plt.close()

# Save world storage snapshot
storage_snapshot = {addr: c.storage for addr, c in world.contracts.items()}
with open(OUT / "storage.json","w") as f:
    json.dump(storage_snapshot, f, indent=2)

print("Demo complete. Outputs and charts written to outputs/ and charts/.")