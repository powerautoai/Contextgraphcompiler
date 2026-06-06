#!/usr/bin/env python3
import sys
import os
import argparse
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    parser = argparse.ArgumentParser(description="CGC Universe: Unified Engine Runner", allow_abbrev=False)
    parser.add_argument("--auto-pd", action="store_true", help="Enable Auto-PD (Platform-Device scheduling) - Triggers M4")
    parser.add_argument("--verify-m6", action="store_true", help="Directly trigger M6 Product Gate (build -> run -> verify)")
    
    args, unknown = parser.parse_known_args()
    
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.dirname(os.path.abspath(__file__)) + (os.pathsep + env["PYTHONPATH"] if "PYTHONPATH" in env else "")
    
    if args.verify_m6:
        print("[run_cgc_engine] Triggering M6 Product Verification Pipeline...")
        cmd = [sys.executable, "-m", "cgc_engine.agent.cli", "pipeline", "--milestone", "m6"] + unknown
        print(f"Executing: {' '.join(cmd)}")
        result = subprocess.run(cmd, env=env)
        sys.exit(result.returncode)
    
    cmd = [sys.executable, "-m", "cgc_engine.agent.cli", "pipeline"] + unknown
    
    if args.auto_pd:
        os.environ["CGC_MILESTONE"] = "m4"
        cmd.extend(["--milestone", "m4"])
        
    print(f"[run_cgc_engine] Dispatching to: {' '.join(cmd)}")
    result = subprocess.run(cmd, env=env)
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()