![썸네일](https://velog.velcdn.com/images/ashcircle03/post/thumbnail-image.jpg)

# AlertManager로 Discord Bot 모니터링 알림 시스템 구축하기

> 🐧 **리눅스로 한 학기 살기** 시리즈 - AlertManager편

"리눅스로 한 학기 살기" 프로젝트에서 Discord Bot의 모니터링 시스템을 완성하기 위해 AlertManager를 도입했습니다. Prometheus로 메트릭을 수집하고, Grafana로 시각화한 다음, 마지막으로 AlertManager를 통해 실시간 알림 시스템을 구축했습니다.

이전 글들:
- [Ubuntu 설치부터 시작하기](https://velog.io/@ashcircle03/리눅스-한학기-1)
- [Docker와 Kubernetes 환경 구축](https://velog.io/@ashcircle03/리눅스-한학기-2)
- [Prometheus 모니터링 시스템](https://velog.io/@ashcircle03/리눅스-한학기-3)

---

## 🎯 왜 AlertManager가 필요했을까?

Discord Bot이 24시간 안정적으로 돌아가는지 확인하려면 계속 모니터링해야 하는데, 사람이 24시간 대시보드를 지켜볼 수는 없잖아요. 

![문제상황](https://velog.velcdn.com/images/ashcircle03/post/problem.png)

그래서 다음과 같은 상황에 자동으로 알림이 오도록 설정했습니다:

- ⚠️ **Discord Bot 다운**: 1분 이상 응답 없음
- 🔥 **높은 에러율**: 에러 카운트가 5개 초과  
- 🔄 **Pod 재시작**: Kubernetes에서 Pod가 재시작됨
- ⏱️ **응답 지연**: 메시지 처리 시간이 너무 오래 걸림

---

## 🏗️ 실제 구현된 아키텍처

![아키텍처 다이어그램](https://velog.velcdn.com/images/ashcircle03/post/architecture.png)

전체적인 모니터링 시스템의 구조는 다음과 같습니다:

1. **Discord Bot** → **Prometheus** (메트릭 수집)
2. **Prometheus** → **AlertManager** (Alert Rules 적용)  
3. **AlertManager** → **Slack** (Webhook 알림)

Flask 서버에서는 3개의 엔드포인트를 제공합니다:
- `/metrics` (8000 포트): Prometheus가 메트릭 수집
- `/health`: 헬스체크용
- `/test-error`: 테스트용 에러 발생

---

## 📊 Discord Bot에서 수집하는 실제 메트릭들

제가 구현한 Discord Bot에서는 다음 메트릭들을 실시간으로 수집합니다:

### 핵심 메트릭

![메트릭 예시](https://velog.velcdn.com/images/ashcircle03/post/metrics.png)

```bash
# 명령어 실행 통계 (성공/실패 구분)
discord_bot_commands_total{command="ping", status="success"} 45
discord_bot_commands_total{command="add", status="success"} 31
discord_bot_commands_total{command="roll", status="success"} 3

# 메시지 처리 시간
discord_bot_message_latency_seconds_bucket{le="0.1"} 42
discord_bot_message_latency_seconds_bucket{le="0.5"} 78

# 전송한 메시지 수
discord_bot_messages_sent_total 79

# 에러 발생 횟수 (타입별)
discord_bot_errors_total{error_type="command_error"} 2
discord_bot_errors_total{error_type="startup"} 0

# 봇 상태 확인 (하트비트)
discord_bot_heartbeat_timestamp_seconds 1717084523

# 서버 및 사용자 통계
discord_bot_active_guilds 1
discord_bot_active_users 5
```

### 🧪 특별한 테스트 엔드포인트

모니터링 시스템을 테스트하기 위해 의도적으로 에러를 발생시키는 엔드포인트도 만들었습니다:

```python
@app.route('/test-error')
def test_error():
    """테스트용 에러 발생"""
    metrics.error_count.labels(error_type='test_error').inc()
    logging.error("Test error triggered via /test-error endpoint")
    return {"status": "error", "message": "Test error generated"}, 500

@app.route('/test-crash')
def test_crash():
    """테스트용 크래시 시뮬레이션"""
    metrics.error_count.labels(error_type='crash_simulation').inc()
    logging.critical("Crash simulation triggered")
    raise Exception("Simulated crash for testing alerts")
```

---

## ⚙️ AlertManager 설정 과정

### 1️⃣ Slack Webhook을 Kubernetes Secret으로 보안 설정

처음에는 AlertManager 설정에 Slack webhook URL을 평문으로 넣었는데, 보안상 문제가 있어서 Kubernetes Secret으로 분리했습니다:

> ⚠️ **보안 주의**: Webhook URL은 절대 코드에 하드코딩하면 안됩니다!

```yaml
# slack-webhook-secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: slack-webhook-secret
  namespace: monitoring
type: Opaque
data:
  webhook-url: aHR0cHM6Ly9ob29rcy5zbGFjay5jb20vc2VydmljZXMvVDA4UUJMTlVUQjQvQjA4VUZQUzVRVEQvVEdBSnBza3B6cXU2TUNPRVM4OGVKMklX
```

### 2️⃣ AlertManager 설정 - 실제 운영 중인 설정

![AlertManager 설정](https://velog.velcdn.com/images/ashcircle03/post/alertmanager-config.png)

```yaml
# alertmanager-configmap.yaml
global:
  slack_api_url_file: '/etc/slack-secrets/webhook-url'

route:
  receiver: 'default'
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 5m
  repeat_interval: 12h
  routes:
  - match:
      alertname: DiscordBotHighErrors
    receiver: 'discord-bot-critical'
    repeat_interval: 30m
  - match:
      alertname: DiscordBotDown
    receiver: 'discord-bot-critical'
    repeat_interval: 15m

receivers:
- name: 'discord-bot-critical'
  slack_configs:
  - channel: 'C08QCUMR0GL'  # 실제 사용 중인 채널 ID
    send_resolved: true
    username: "Discord Bot Alert"
    icon_emoji: ":robot_face:"
    color: 'danger'
    title: "🚨 Discord Bot Alert: {{ .GroupLabels.alertname }}"
    text: |
      {{ range .Alerts }}
      *Summary:* {{ .Annotations.summary }}
      *Description:* {{ .Annotations.description }}
      *Started:* {{ .StartsAt.Format "2006-01-02 15:04:05" }}
      {{ end }}
```

### 3️⃣ Prometheus Alert Rules - 실제 동작하는 규칙들

> 💡 **팁**: Alert Rules는 너무 민감하게 설정하면 알림 피로도가 생기니까 적절한 임계값 설정이 중요해요!

```yaml
# prometheus-rules-configmap.yaml
groups:
- name: discord-bot-alerts
  rules:
  - alert: DiscordBotHighErrors
    expr: discord_bot_errors_total > 5
    for: 30s
    labels:
      severity: critical
      service: discord-bot
    annotations:
      summary: "Discord Bot high error count"
      description: "Error count is {{ $value }}"
      
  - alert: DiscordBotDown
    expr: up{job="discord-bot"} == 0
    for: 1m
    labels:
      severity: critical
      service: discord-bot
    annotations:
      summary: "Discord Bot is down"
      description: "Discord Bot has been down for more than 1 minute"
```

---

## 🚀 실제 배포 과정

### Step 1: Secret 생성
```bash
# 실제 webhook URL을 Base64로 인코딩
echo -n "https://hooks.slack.com/services/YOUR/WEBHOOK/URL" | base64

# Secret 적용
kubectl apply -f k8s/monitoring/slack-bot/slack-webhook-secret.yaml
```

### Step 2: AlertManager 배포
```bash
kubectl apply -f k8s/monitoring/alertmanager/alertmanager-configmap.yaml
kubectl apply -f k8s/monitoring/alertmanager/alertmanager-deployment.yaml
kubectl apply -f k8s/monitoring/alertmanager/alertmanager-service.yaml
```

### Step 3: Prometheus Rules 적용

---
```bash
kubectl apply -f k8s/monitoring/prometheus/prometheus-rules-configmap.yaml
kubectl rollout restart deployment/prometheus -n monitoring
```

## 🧪 실제 테스트 결과

### 🔴 테스트 1: Bot 다운 시뮬레이션

![Bot 다운 테스트](https://velog.velcdn.com/images/ashcircle03/post/bot-down-test.png)
```bash
# Discord Bot Pod 강제 삭제
kubectl delete pod -l app=discord-bot

# 1분 후 Slack에 도착한 알림:
```

> 📱 **실제 받은 Slack 알림**:
```
🚨 Discord Bot Alert: DiscordBotDown
Summary: Discord Bot is down
Description: Discord Bot has been down for more than 1 minute
Started: 2025-05-30 15:42:33
```

### 🟡 테스트 2: 인위적 에러 발생

![에러 테스트](https://velog.velcdn.com/images/ashcircle03/post/error-test.png)
```bash
# 테스트 에러 엔드포인트 호출
curl http://localhost:8000/test-error

# 6번 호출하여 임계값(5) 초과
for i in {1..6}; do curl http://localhost:8000/test-error; done

# 30초 후 알림 도착!
```

> 📱 **실제 받은 Slack 알림**:

---
```
🚨 Discord Bot Alert: DiscordBotHighErrors
Summary: Discord Bot high error count
Description: Error count is 6
Started: 2025-05-30 15:45:12
```

## 📈 실제 운영 통계 (일주일)

![운영 통계](https://velog.velcdn.com/images/ashcircle03/post/stats.png)

현재까지 실제로 받은 알림들:

### 📊 알림 발생 현황
- 📩 **총 알림**: 12개
- 🔴 **DiscordBotDown**: 4회 (Jenkins 재배포 시)
- 🟡 **DiscordBotHighErrors**: 2회 (테스트 중 발생)  
- 🔄 **Pod 재시작**: 1회 (메모리 부족)

### 🤖 Discord Bot 사용 통계
- 📝 **총 명령어 실행**: 79번
  - `ping`: 45번 (가장 많이 사용) 🏆
  - `add`: 31번 
  - `roll`: 3번
- 💬 **총 메시지 전송**: 79개
- ⚡ **평균 응답 시간**: 0.05초
- ❌ **에러 발생**: 2건 (모두 테스트용)

---

## 🔧 운영 중 발견한 문제와 해결

### ❌ 문제 1: 알림 피로도 (Alert Fatigue)

**문제**: 처음에는 `repeat_interval: 5m`으로 설정해서 너무 자주 알림이 왔습니다.

![알림 피로도](https://velog.velcdn.com/images/ashcircle03/post/alert-fatigue.png)

**해결**: 심각도별로 다른 주기 설정
```yaml
# Critical: 15분마다
repeat_interval: 15m
# Warning: 1시간마다  
repeat_interval: 1h
```

### ❌ 문제 2: 재배포 시 불필요한 알림

**문제**: Jenkins에서 재배포할 때마다 DiscordBotDown 알림이 발생

![재배포 알림](https://velog.velcdn.com/images/ashcircle03/post/redeploy-alert.png)

**해결**: `for: 1m` 설정으로 1분간 기다린 후 알림 발송

### ❌ 문제 3: AlertManager가 Prometheus를 찾지 못함

**문제**: Alert Rules는 있지만 AlertManager가 동작하지 않음

**해결**: prometheus.yml에 alertmanager 설정 추가
```yaml
alerting:
  alertmanagers:
  - static_configs:
    - targets:
      - alertmanager.monitoring.svc.cluster.local:9093
```

---

## 🎯 현재 모니터링 시스템 상태

![시스템 현황](https://velog.velcdn.com/images/ashcircle03/post/current-status.png)

### 🚀 실시간 동작 중인 컴포넌트들
- 🤖 **Discord Bot**: `ashcircle03/discord-bot:116` 이미지로 안정적 실행
- 📊 **Prometheus**: 30초마다 44개 메트릭 수집
- 🚨 **AlertManager**: Slack 채널 `C08QCUMR0GL`로 알림 전송
- 📈 **Grafana**: 실시간 대시보드 제공 (http://localhost:3000)

### 📋 수집 중인 핵심 지표

> 💡 **실제 운영 중인 메트릭들**: 아래는 지금 이 순간에도 수집되고 있는 실제 데이터입니다!
```bash
# 현재 수집되는 실제 메트릭 예시
discord_bot_commands_total{command="ping",status="success"} 45
discord_bot_messages_sent_total 79
discord_bot_errors_total{error_type="command_error"} 2
discord_bot_heartbeat_timestamp_seconds 1717084523
discord_bot_active_guilds 1
discord_bot_active_users 5
```

---

## 📚 배운 점과 개선 사항

### ✅ 잘한 점들

![성공 포인트](https://velog.velcdn.com/images/ashcircle03/post/success-points.png)

1. **🔐 보안 강화**: Slack webhook을 Kubernetes Secret으로 관리
2. **📊 다양한 메트릭**: 명령어별, 에러 타입별 세분화된 수집
3. **🧪 테스트 엔드포인트**: 의도적 에러 발생으로 알림 시스템 검증
4. **⚖️ 적절한 임계값**: 실제 사용 패턴을 고려한 alert rule 설정

### 🔮 개선할 점들
1. **🔄 자동 복구**: 간단한 문제는 자동으로 재시작하는 기능
2. **📱 더 다양한 알림 채널**: 심각한 장애 시 이메일/전화 알림
3. **🔮 예측적 알림**: 메모리 사용량 증가 추세 등 예측 기반 알림

---

## 🎉 마무리

![최종 결과](https://velog.velcdn.com/images/ashcircle03/post/final-result.png)

처음에는 단순히 "Discord Bot 만들어보자"였는데, 어느새 본격적인 운영 환경 수준의 모니터링 시스템을 구축하게 되었습니다.

### 🏆 최종 완성된 스택

> 🎯 **한 학기의 결과물**: Ubuntu 설치부터 시작해서 이런 시스템까지!

- ✅ **Discord Bot**: Python으로 구현, 6개 명령어 지원
- ✅ **Prometheus**: 실시간 메트릭 수집 (44개 지표)
- ✅ **Grafana**: 시각화 대시보드
- ✅ **AlertManager**: Slack 실시간 알림 ← **오늘의 주인공!**
- ✅ **Kubernetes**: 컨테이너 오케스트레이션
- ✅ **Jenkins**: CI/CD 파이프라인 (빌드 #117까지 성공)

지금은 실제로 Discord에서 `?ping` 명령어를 입력하면 45번째 실행이라고 Prometheus 메트릭에 기록되고, 만약 봇이 다운되면 1분 내에 Slack으로 알림이 옵니다.

### 🤔 소감

한 학기 동안 리눅스를 배우면서 이런 시스템까지 만들 줄은 몰랐는데, 정말 뿌듯하네요! 

처음엔 터미널도 무서웠는데 이제는 `kubectl`, `docker`, `systemctl` 같은 명령어들이 손에 익숙해졌어요. 

특히 AlertManager 설정하면서 **"아, 이게 진짜 운영이구나"** 하는 생각이 들었습니다. 🚀

---

## 🔗 관련 시리즈

이 글이 도움이 되셨다면 다른 시리즈도 확인해보세요!

- 📝 [Ubuntu 설치부터 시작하기](https://velog.io/@ashcircle03/리눅스-한학기-1)
- 🐳 [Docker와 Kubernetes 환경 구축](https://velog.io/@ashcircle03/리눅스-한학기-2)  
- 📊 [Prometheus로 Discord Bot 모니터링하기](https://velog.io/@ashcircle03/리눅스-한학기-3)
- 📈 [Grafana 대시보드 구축기](https://velog.io/@ashcircle03/리눅스-한학기-4)
- 🔧 [Jenkins CI/CD 파이프라인 구축하기](https://velog.io/@ashcircle03/리눅스-한학기-5)

### 🏷️ Tags
`#리눅스` `#AlertManager` `#DevOps` `#모니터링` `#Kubernetes` `#Slack` `#Prometheus` `#Discord봇` `#한학기` `#학습기록`

> 💬 **댓글로 질문 남겨주세요!** 
> AlertManager 설정하다가 막히는 부분이나 궁금한 점이 있으면 언제든지 댓글로 물어보세요. 같이 해결해봐요! 😊
