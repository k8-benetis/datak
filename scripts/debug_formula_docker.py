import paramiko
import sys
import time

HOST = "100.95.129.22"
USER = "g"
PASS = "agrivolt"

def main():
    print(f"Connecting to {HOST}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASS)
    
    # Get backend container ID
    print("Getting container ID...")
    stdin, stdout, stderr = client.exec_command("sudo -S -p '' docker ps -qf name=backend")
    stdin.write(f"{PASS}\n")
    stdin.flush()
    container_id = stdout.read().decode().strip()
    
    if not container_id:
        print("Backend container not found!")
        return

    print(f"Container ID: {container_id}")
    
    script_content = """
import sys
import os

# Ensure /app is in path
if "/app" not in sys.path:
    sys.path.append("/app")

print(f"Sys Path: {sys.path}")

try:
    from app.core.formula import validate_formula
except ImportError as e:
    print(f"IMPORT ERROR: {e}")
    sys.exit(1)

print(f"Running test in PID {os.getpid()}")
try:
    print(f"Testing 'val'...")
    # Explicitly check RestrictedPython if possible
    valid, error = validate_formula('val')
    print(f"RESULT: {valid}")
    print(f"ERROR: {error}")
except Exception as e:
    print(f"EXCEPTION: {e}")
    import traceback
    traceback.print_exc()
"""
    
    remote_path = "/home/g/debug_test.py"
    print(f"Uploading script to {remote_path} via SFTP...")
    sftp = client.open_sftp()
    with sftp.file(remote_path, "w") as f:
        f.write(script_content)
    sftp.close()
    
    print("Copying script to container...")
    cmd_cp = f"sudo -S -p '' docker cp {remote_path} {container_id}:/tmp/test.py"
    stdin, stdout, stderr = client.exec_command(cmd_cp)
    stdin.write(f"{PASS}\n")
    stdin.flush()
    
    print("Executing script inside container...")
    cmd_exec = f"sudo -S -p '' docker exec {container_id} python /tmp/test.py"
    stdin, stdout, stderr = client.exec_command(cmd_exec)
    stdin.write(f"{PASS}\n")
    stdin.flush()
    
    print("--- OUTPUT ---")
    print(stdout.read().decode())
    print("--- ERROR ---")
    print(stderr.read().decode())
    
    client.close()

if __name__ == "__main__":
    main()
