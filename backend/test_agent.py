import os
from dotenv import load_dotenv
load_dotenv()

from backend.orchestrator import run_resolution

print("Testing TX9281 (Auto Reversal)")
res = run_resolution("TX9281")
print(res.investigation_narrative)
for e in res.events:
    if e.type == "INVESTIGATION":
        print(f"  {e.step}: {e.status}")
