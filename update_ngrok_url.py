import os
import re
from dotenv import load_dotenv
from github import Github

# .env 파일의 경로를 지정하여 로드
dotenv_path = os.path.join(os.path.dirname(__file__), './orderbot/.env')
load_dotenv(dotenv_path)

# 프로젝트 루트 디렉토리 설정
PROJECT_ROOT = '/home/nadle/Grow/temp/orderbot_v2'

def update_file(file_path, patterns, new_url):
    with open(file_path, 'r') as file:
        content = file.read()

    # new_url에서 http:// 또는 https:// 제거한 도메인만 추출
    domain_only = re.sub(r'^https?://', '', new_url)

    for pattern, replace_format in patterns:
        # ALLOWED_HOSTS에는 도메인만, CORS_ALLOWED_ORIGINS에는 https:// 포함된 URL 사용
        if 'ALLOWED_HOSTS' in pattern:
            content = re.sub(pattern, replace_format.format(domain_only), content)
        else:
            content = re.sub(pattern, replace_format.format(new_url), content)

    with open(file_path, 'w') as file:
        file.write(content)


def main():
    new_url = input("새로운 ngrok URL을 입력하세요 (예: https://3750-59-15-64-225.ngrok-free.app): ").strip()

    # nginx/default.conf 업데이트
    nginx_conf_path = os.path.join(PROJECT_ROOT, 'nginx', 'default.conf')
    nginx_patterns = [
        (r'server_name .*?;', 'server_name {};')
    ]
    update_file(nginx_conf_path, nginx_patterns, new_url)

    # react-frontend/env.production 업데이트
    env_prod_path = os.path.join(PROJECT_ROOT, 'react-frontend', '.env.production')
    env_prod_patterns = [
        (r'VITE_API_URL=.*', 'VITE_API_URL={}'),
        (r'VITE_WS_URL=.*', 'VITE_WS_URL={}')
    ]
    update_file(env_prod_path, env_prod_patterns, new_url)

    # VITE_WS_URL을 wss://로 변경
    with open(env_prod_path, 'r') as file:
        content = file.read()
    content = content.replace(f'VITE_WS_URL={new_url}', f'VITE_WS_URL=wss://{new_url[8:]}')
    with open(env_prod_path, 'w') as file:
        file.write(content)

    # orderbot/.env 업데이트
    env_path = os.path.join(PROJECT_ROOT, 'orderbot', '.env')
    env_patterns = [
        (r'(ALLOWED_HOSTS=.*?,).*', r'\1{}'),
        (r'(CORS_ALLOWED_ORIGINS=.*?,).*', r'\1{}')
    ]
    update_file(env_path, env_patterns, new_url)

    print("모든 파일이 성공적으로 업데이트되었습니다.")

if __name__ == "__main__":
    main()