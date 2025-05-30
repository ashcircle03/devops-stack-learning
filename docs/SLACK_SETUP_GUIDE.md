# Slack 봇 설정 가이드

## 1. Slack 앱 생성
1. https://api.slack.com/apps 접속
2. "Create New App" 클릭
3. "From scratch" 선택
4. App Name: `Kubernetes Monitor`
5. Workspace 선택 후 "Create App"

## 2. Bot Token 설정
1. 좌측 메뉴에서 "OAuth & Permissions" 클릭
2. "Scopes" 섹션에서 Bot Token Scopes 추가:
   - `chat:write` (메시지 전송)
   - `commands` (슬래시 명령어)
3. "Install to Workspace" 클릭
4. Bot User OAuth Token 복사 (xoxb-로 시작)

## 3. 슬래시 명령어 생성
1. 좌측 메뉴에서 "Slash Commands" 클릭
2. "Create New Command" 클릭
3. 설정값:
   - **Command**: `/로그`
   - **Request URL**: `http://YOUR_EXTERNAL_IP:30500/slack/commands`
   - **Short Description**: `쿠버네티스 로그 조회`
   - **Usage Hint**: `[discord|prometheus|alertmanager|grafana|status]`
4. "Save" 클릭

## 4. 앱 설정 완료
1. 좌측 메뉴에서 "Basic Information" 클릭
2. "App Credentials" 섹션에서 Signing Secret 복사
3. "Install App" 섹션에서 워크스페이스에 앱 설치

## 5. Kubernetes Secret 생성
```bash
kubectl create secret generic slack-bot-secrets \
  --from-literal=bot-token="xoxb-your-actual-bot-token" \
  --from-literal=signing-secret="your-actual-signing-secret" \
  -n monitoring
```

## 6. 외부 접근 설정
현재 사용 가능한 접근 방법:
- **NodePort**: `http://192.168.49.2:30500/slack/commands`
- **Minikube Tunnel**: `minikube tunnel` 후 LoadBalancer IP 사용

## 7. 테스트
Slack에서 `/로그` 명령어 실행:
- `/로그` - Discord 봇 로그 (기본)
- `/로그 discord` - Discord 봇 로그
- `/로그 prometheus` - Prometheus 로그
- `/로그 alertmanager` - Alertmanager 로그
- `/로그 grafana` - Grafana 로그
- `/로그 status` - 전체 모니터링 상태

## 현재 상태
✅ Slack 봇 코드 구현 완료
✅ Kubernetes 배포 완료
✅ RBAC 권한 설정 완료
⏳ Slack 앱 설정 필요
⏳ 실제 토큰 설정 필요

## 주의사항
- Request URL은 외부에서 접근 가능한 주소여야 함
- Minikube 환경에서는 `minikube tunnel`이나 ngrok 같은 터널링 도구 필요
- 프로덕션 환경에서는 HTTPS 사용 권장
