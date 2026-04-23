import subprocess
import sys

def run_command(command, check=True):
    try:
        # shell=True is useful for Windows commands, but requires string input
        subprocess.run(command, shell=True, check=check)
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Command failed with exit code {e.returncode}: {command}")
        sys.exit(e.returncode)

def main():
    print("===")
    print("Starting Sarcasm Sync Chat App Dev Environment")
    print("===")
    print()

    print("[1/3] Starting Docker containers (Postgres, Redis)...")
    run_command("docker-compose up -d")
    
    print("\n[2/3] Building SAM Application (using container to ensure Linux compatibility)...")
    run_command("sam build --use-container")
    
    print("\n[3/3] Starting SAM Local API Gateway...")
    print("Press Ctrl+C to stop the API Gateway and exit.")
    try:
        # We don't enforce check=True here because stopping it via Ctrl+C returns a non-zero exit code
        subprocess.run("sam local start-api --env-vars env.json", shell=True)
    except KeyboardInterrupt:
        print("\nInterrupt received, stopping...")

    print("\n===")
    print("Dev environment has stopped.")
    print("===")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting.")
        sys.exit(0)
