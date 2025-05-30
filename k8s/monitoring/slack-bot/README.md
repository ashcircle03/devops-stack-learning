# Slack Webhook Secret 설정 가이드

AlertManager에서 Slack 알림을 보내기 위해 webhook URL을 Kubernetes secret으로 관리하는 방법입니다.

## 1. Slack Webhook URL 생성

1. Slack 워크스페이스에서 Incoming Webhooks 앱을 설치하세요
2. 알림을 받을 채널을 선택하세요
3. 생성된 webhook URL을 복사하세요 (형태: `https://hooks.slack.com/services/T.../B.../...`)

## 2. Kubernetes Secret 생성

### 방법 1: kubectl 명령어 사용 (권장)

```bash
kubectl create secret generic slack-webhook-secret \
  --from-literal=webhook-url="https://hooks.slack.com/services/YOUR/WEBHOOK/URL" \
  -n monitoring
```

### 방법 2: YAML 파일 사용

1. Webhook URL을 Base64로 인코딩:
```bash
echo -n "https://hooks.slack.com/services/YOUR/WEBHOOK/URL" | base64
```

2. `slack-webhook-secret.yaml` 파일의 `webhook-url` 값을 위에서 생성한 Base64 값으로 교체

3. Secret 적용:
```bash
kubectl apply -f slack-webhook-secret.yaml
```

## 3. AlertManager 배포

```bash
# Secret 먼저 생성
kubectl apply -f slack-webhook-secret.yaml

# AlertManager 설정 및 배포
kubectl apply -f alertmanager-configmap.yaml
kubectl apply -f alertmanager-deployment.yaml
kubectl apply -f alertmanager-service.yaml
```

## 4. 확인

```bash
# Secret 확인
kubectl get secrets -n monitoring | grep slack

# AlertManager Pod 로그 확인
kubectl logs -n monitoring deployment/alertmanager

# AlertManager 설정 확인
kubectl port-forward -n monitoring svc/alertmanager 9093:9093
# http://localhost:9093에서 설정 확인
```

## 보안 고려사항

- Webhook URL은 절대 코드에 하드코딩하지 마세요
- Secret은 암호화되어 etcd에 저장됩니다
- RBAC를 통해 Secret 접근 권한을 제한하세요
- 정기적으로 webhook URL을 갱신하는 것을 고려하세요

## 문제 해결

### AlertManager가 시작되지 않는 경우

1. Secret이 올바르게 생성되었는지 확인:
```bash
kubectl get secret slack-webhook-secret -n monitoring -o yaml
```

2. Pod 로그 확인:
```bash
kubectl logs -n monitoring deployment/alertmanager
```

3. Secret 파일이 마운트되었는지 확인:
```bash
kubectl exec -n monitoring deployment/alertmanager -- ls -la /etc/slack-secrets/
```

### 알림이 전송되지 않는 경우

1. Slack webhook URL이 유효한지 테스트:
```bash
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"Test message"}' \
  YOUR_WEBHOOK_URL
```

2. AlertManager 설정 확인:
```bash
kubectl port-forward -n monitoring svc/alertmanager 9093:9093
# http://localhost:9093/#/config에서 설정 확인
```
