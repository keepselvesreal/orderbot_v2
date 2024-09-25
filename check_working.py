import subprocess

try:
    # docker-compose down 명령어 실행!
    subprocess.run(['docker-compose', 'down'], check=True)
    print("Docker Compose has been successfully brought down.")
except subprocess.CalledProcessError as e:
    print(f"An error occurred: {e}")