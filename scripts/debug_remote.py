import paramiko
import sys

HOST = "100.95.129.22"
USER = "g"
PASS = "agrivolt"

def main():
    print(f"Connecting to {HOST}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASS)
    
    # Get backend container ID
    stdin, stdout, stderr = client.exec_command("sudo -S -p '' docker ps -qf name=backend")
    stdin.write(f"{PASS}\n")
    stdin.flush()
    
    container_id = stdout.read().decode().strip()
    
    if not container_id:
        print("Backend container not found!")
        return
        
    print(f"Fetching logs for container {container_id}...")
    stdin, stdout, stderr = client.exec_command(f"sudo -S -p '' docker logs --tail 50 {container_id}")
    stdin.write(f"{PASS}\n")
    stdin.flush()
    
    print(stdout.read().decode())
    print(stderr.read().decode())
    
    # Check the file content
    print("Checking remote app/models/sensor.py...")
    stdin, stdout, stderr = client.exec_command("ls -td -- /home/g/datak_* | head -n 1")
    stdin.write(f"{PASS}\n")
    stdin.flush()
    latest_dir = stdout.read().decode().strip()
    
    if latest_dir:
        print(f"Latest dir: {latest_dir}")
        cmd = f"cat {latest_dir}/backend/app/models/sensor.py"
        stdin, stdout, stderr = client.exec_command(f"sudo -S -p '' {cmd}")
        stdin.write(f"{PASS}\n")
        stdin.flush()
        content = stdout.read().decode()
        print(content)
        if "SYSTEM" in content:
            print("SUCCESS: SYSTEM protocol found in file.")
        else:
            print("FAILURE: SYSTEM protocol NOT found in file.")
    
    client.close()

if __name__ == "__main__":
    main()
