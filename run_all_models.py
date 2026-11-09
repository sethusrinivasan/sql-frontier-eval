import subprocess
import sys
import time

models = [
    "gemini-3.8-flash-high",
    "claude-sonnet-4-6",
    "claude-opus-4-6-thinking",
    "gpt-oss-120b-medium"
]

for m in models:
    print(f"\n=======================================================")
    print(f"STARTING EVALUATION RUN: agy/{m}")
    print(f"=======================================================")
    cmd = [
        sys.executable,
        "run_eval.py",
        f"--model=agy/{m}",
        "--tasks=tasks/*.json",
        "--save-results"
    ]
    t0 = time.time()
    res = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - t0
    print(f"Finished agy/{m} in {elapsed:.1f}s (Return Code: {res.returncode})")
    
    # Print summary output lines
    for line in res.stdout.splitlines():
        if "Final Score:" in line or "Saved run artifact to" in line or "Verdict:" in line:
            print("  " + line)
    if res.returncode != 0:
        print("  STDERR:", res.stderr[-500:])

print("\nALL MODEL RUNS COMPLETED SUCCESSFULLY.")
