from flask import Flask, request
import subprocess

app = Flask(__name__)

@app.route('/deploy', methods=['POST'])
def deploy():
    try:
        print("Received deployment request!!")
        subprocess.run(['git', 'pull', 'origin', 'refactor/modularize'], check=True)
        subprocess.run(['docker-compose', 'down'], check=True)
        subprocess.run(['docker-compose', 'up', '--build', '-d'], check=True)
        return 'Deployment successful', 200
    except subprocess.CalledProcessError as e:
        return f'Deployment failed: {str(e)}', 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9000)
