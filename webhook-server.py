from flask import Flask, request
import subprocess
import os
import traceback

app = Flask(__name__)

@app.route('/deploy', methods=['POST'])
def deploy():
    try:
        print("Received deployment request!")
        
        # 작업 디렉토리 확인
        print(f"Current working directory: {os.getcwd()}")
        
        # Git pull
        print("Executing git pull...")
        result = subprocess.run(['git', 'pull', 'origin', 'refactor/settings-split'], check=True, capture_output=True, text=True)
        print(f"Git pull output: {result.stdout}")
        
        # Docker compose down (ignore errors)
        print("Executing docker-compose down...")
        result = subprocess.run(['docker-compose', 'down'], check=False, capture_output=True, text=True)
        print(f"Docker compose down output: {result.stdout}")
        
        # Docker compose up
        print("Executing docker-compose up...")
        result = subprocess.run(['docker-compose', 'up', '--build', '-d'], check=True, capture_output=True, text=True)
        print(f"Docker compose up output: {result.stdout}")
        
        print("Deployment steps completed successfully")
        return 'Deployment successful', 200
    except subprocess.CalledProcessError as e:
        error_message = f"Deployment failed: {str(e)}\nCommand output: {e.output}"
        print(error_message)
        return error_message, 500
    except Exception as e:
        error_message = f"Unexpected error: {str(e)}\n{traceback.format_exc()}"
        print(error_message)
        return error_message, 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9000, debug=True)
