#!/bin/sh
# 서버에서 최신 main 으로 다시 띄우기 (GitHub Actions 가 main 머지 때 SSH 로 실행, 손으로 돌려도 됨)
#   cd ~/nova-fin-assistant && git pull && sh deploy/update.sh
#
# 자동 배포 처음 설정 (서버에서 한 번):
#   1) 배포 전용 키 만들기
#        ssh-keygen -t ed25519 -N "" -C github-actions -f ~/.ssh/github_deploy
#        cat ~/.ssh/github_deploy.pub >> ~/.ssh/authorized_keys
#   2) GitHub 레포 > Settings > Secrets and variables > Actions 에 세 개 등록
#        DEPLOY_HOST         서버 IP
#        DEPLOY_SSH_KEY      cat ~/.ssh/github_deploy 의 내용 전체 (BEGIN ~ END 줄까지)
#        DEPLOY_KNOWN_HOSTS  ssh-keyscan -t ed25519 <서버IP> 의 출력
#      등록한 뒤 서버의 개인 키 파일은 지워도 됩니다: rm ~/.ssh/github_deploy
#   3) GitHub Actions 는 IP 가 매번 달라서, 방화벽의 SSH(22) 규칙을 Anywhere 로 열고
#      비밀번호 로그인은 끕니다 (키로만 접속): /etc/ssh/sshd_config 의 PasswordAuthentication no
set -e
cd "$(dirname "$0")/.."
DC="docker compose -f docker-compose.prod.yml --env-file .env.prod"

$DC up -d --build
docker image prune -f >/dev/null

# 백엔드가 살아났는지 확인 (마이그레이션 포함 최대 2분)
i=0
until $DC exec -T backend python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" 2>/dev/null; do
  i=$((i + 1))
  if [ "$i" -ge 24 ]; then
    echo "백엔드가 2분 안에 켜지지 않았습니다. 로그:"
    $DC logs --tail 40 backend
    exit 1
  fi
  sleep 5
done
$DC ps
echo "배포 완료"
