# 리눅스로 한 학기 살기

한 학기 동안 집에서 Ubuntu를 설치하고 DevOps 도구들을 하나씩 익혀나간 기록입니다. 

📝 전체 과정은 블로그에 정리했습니다: [velog.io/@ashcircle03/series/리눅스](https://velog.io/@ashcircle03/series/%EB%A6%AC%EB%88%85%EC%8A%A4)

## 뭘 배웠나?

- Ubuntu 설치하고 기본 명령어들 익히기
- 터미널을 예쁘게 꾸미기 (Warp, Zsh)
- Docker로 컨테이너 다루기
- Kubernetes 클러스터 만들어보기
- Jenkins로 자동 배포 구축하기
- Prometheus, Grafana로 모니터링하기
- 실제로 돌아가는 Discord 봇 만들기

## 설치한 프로그램들

결국 12개나 설치했네요. 이렇게 놓고 보니까 좀 많긴 하네...

| 순서 | 프로그램 | 용도 |
|------|----------|------|
| 1 | Ubuntu | 운영체제 |
| 2 | Warp | 터미널 |
| 3 | Zsh | 쉘 |
| 4 | VS Code | 에디터 |
| 5 | Docker | 컨테이너 |
| 6 | Minikube | Kubernetes |
| 7 | Miniconda | Python 환경 |
| 8 | Jenkins | CI/CD |
| 9 | Discord.py | 봇 개발 |
| 10 | Prometheus | 모니터링 |
| 11 | Grafana | 대시보드 | 
| 12 | Alertmanager | 알림 | 


## 지금 뭐가 돌고 있나

다 만들어놓고 보니 생각보다 잘 돌아가고 있습니다.

- Discord 봇이 6시간째 안 죽고 돌아감 (기적)
- Prometheus가 30초마다 44개 메트릭 수집 중
- Grafana 대시보드도 한글로 잘 나옴
- Slack 알림도 제대로 옴
- 지금까지 45개 메시지 처리함

Discord 봇은 그냥 이상한 기능만 넣어뒀어요. :
- `?ping` - 응답 속도 재기
- `?add 1 2` - 덧셈 (계산기 쓰는게 나음)
- `?roll 2d6` - 주사위 굴리기
- `?time` - 시간 확인
- `?choose 사과 바나나` - 랜덤 선택
- `?info` - 봇 정보

그래도 모니터링은 제대로 되네요.

## 폴더 구조

```
project1/
├── src/                    # Python 코드들
│   ├── discord_bot.py      # 메인 봇 코드
│   ├── requirements.txt    # 필요한 패키지들
│   └── test_discord_bot.py # 테스트 (잘 안 씀)
│
├── docker/                 # Docker 설정
│   ├── Dockerfile          # 봇용 이미지
│   └── docker-compose.yml  # 로컬 테스트용
│
├── k8s/                    # Kubernetes 설정 파일들
│   ├── app/                # 봇 배포 설정
│   └── monitoring/         # 모니터링 스택
│       ├── prometheus/     # 메트릭 수집
│       ├── grafana/        # 대시보드
│       └── alertmanager/   # 알림
│
├── docs/                   # 문서들
└── ci/                     # Jenkins 설정
```

## 어떻게 돌려보나

현재 모든게 돌아가고 있으니까 그냥 확인만 해보세요:

```bash
# 봇 상태 확인
kubectl get pods -l app=discord-bot

# Grafana 보기 (이미 포트포워딩 되어있음)
# http://localhost:3000 접속
# admin/admin으로 로그인

# 모니터링 테스트
./test-monitoring.sh
```

## 📊 주요 메트릭

Discord 봇에서 수집하는 핵심 지표들:
- `discord_bot_commands_total` - 명령어 실행 통계
- `discord_bot_messages_sent_total` - 메시지 전송 수
- `discord_bot_errors_total` - 에러 발생 횟수
- `discord_bot_heartbeat_timestamp` - 봇 상태 확인
- `discord_bot_message_latency_seconds` - 응답 시간

## 🎯 Discord 봇 명령어

현재 지원하는 명령어들:
- `?ping` - 봇 응답 시간 및 상태 확인
- `?info` - 봇 정보 및 서버 통계 표시  
- `?add <숫자1> <숫자2>` - 두 숫자 덧셈 계산
- `?roll <NdN>` - 주사위 굴리기 (예: 2d6, 1d20)
- `?time` - 현재 한국 시간 표시
- `?choose <선택지들>` - 여러 선택지 중 무작위 선택

## CI/CD 파이프라인

```mermaid
graph TD
    A[개발자] -->|Push Code| B[GitHub]
    B -->|Webhook| C[Jenkins]
    C -->|Checkout| D[소스 코드]
    D -->|Run Tests| E[Python 테스트]
    E -->|Build| F[Docker Image]
    F -->|Push| G[Docker Hub]
    G -->|Deploy| H[Kubernetes]
    H -->|Run| I[Discord Bot]
    
    subgraph "Jenkins Pipeline"
    C
    D
    E
    F
    G
    H
    end
    
    subgraph "Infrastructure"
    J[Kubernetes Cluster]
    end
    
    H -->|Deployed on| J
```

## 뭘 배운 건가

### 기술적인 것들
- Ubuntu 명령어들 (ls, cd, grep, 등등)
- Docker로 이미지 만들고 컨테이너 돌리기
- Kubernetes Pod, Service, Deployment 개념
- Jenkins 파이프라인 짜기 (YAML 지옥)
- Prometheus 쿼리 문법 (PromQL)
- Grafana 대시보드 만들기

### 실제로 유용했던 것들
- 리눅스 환경에 익숙해짐
- 컨테이너 기반으로 생각하게 됨
- 모니터링의 중요성 깨달음
- 자동화가 얼마나 편한지 알게 됨
- 문제 생겼을 때 로그 보는 습관 생김

솔직히 처음엔 그냥 "리눅스 써보자" 였는데 어쩌다 보니 DevOps 스택을 다 만져본 셈이네요.

## 현재 상황

Jenkins Build #116까지 성공했고, 새 저장소로 이전한 후에도 자동 빌드가 잘 돌아가고 있습니다.
add 명령어 31번, roll 명령어 3번 써봤는데 별로 재미는 없어요.

근데 모니터링 대시보드 보는 건 좀 재밌네요. 
실시간으로 메트릭이 변하는 걸 보니까 뭔가 프로가 된 기분입니다.

## 마무리

한 학기 동안 Linux 써보면서 생각보다 많은 걸 배웠네요.
처음엔 무서웠는데 이제는 Terminal이 더 편한 것 같아요.

중간에 막히는 부분 많을 텐데 그냥 구글링하면 됩니다.

---

*Ubuntu 설치부터 Kubernetes 클러스터까지*

