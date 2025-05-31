# 리눅스로 한 학기 살기 - 전체 시스템 아키텍처

## 🏗️ 전체 시스템 연결 구조

```mermaid
graph TB
    subgraph "Development Environment"
        DEV[개발자 💻]
        VSCODE[VS Code]
        GIT[Git Repository]
    end
    
    subgraph "CI/CD Pipeline"
        GITHUB[GitHub Repository 📁]
        JENKINS[Jenkins 🔧]
        DOCKERHUB[Docker Hub 📦]
    end
    
    subgraph "Kubernetes Cluster (Minikube)"
        subgraph "Default Namespace"
            DISCORDBOT[Discord Bot Pod 🤖]
        end
        
        subgraph "Monitoring Namespace"
            PROMETHEUS[Prometheus 📊]
            GRAFANA[Grafana 📈]
            ALERTMANAGER[AlertManager 🚨]
            SLACKBOT[Slack Bot Pod 💬]
        end
        
        subgraph "Kubernetes Services"
            DISCORD_SVC[Discord Bot Service]
            PROM_SVC[Prometheus Service]
            GRAFANA_SVC[Grafana Service]
            ALERT_SVC[AlertManager Service]
            SLACK_SVC[Slack Bot Service]
        end
    end
    
    subgraph "External Services"
        DISCORD_API[Discord API 💬]
        SLACK_API[Slack API 📢]
        DOCKER_REGISTRY[Docker Registry 🐳]
    end
    
    subgraph "Storage & Config"
        CONFIGMAPS[ConfigMaps ⚙️]
        SECRETS[Secrets 🔐]
        VOLUMES[Persistent Volumes 💾]
    end
    
    %% Development Flow
    DEV --> VSCODE
    VSCODE --> GIT
    GIT --> GITHUB
    
    %% CI/CD Flow
    GITHUB -->|Webhook| JENKINS
    JENKINS -->|Build & Test| JENKINS
    JENKINS -->|Push Image| DOCKERHUB
    JENKINS -->|Deploy| DISCORDBOT
    JENKINS -->|Deploy| SLACKBOT
    
    %% Docker Hub Connections
    DOCKERHUB -->|Pull Image| DISCORDBOT
    DOCKERHUB -->|Pull Image| SLACKBOT
    DOCKERHUB --> DOCKER_REGISTRY
    
    %% Service Connections
    DISCORDBOT --> DISCORD_SVC
    PROMETHEUS --> PROM_SVC
    GRAFANA --> GRAFANA_SVC
    ALERTMANAGER --> ALERT_SVC
    SLACKBOT --> SLACK_SVC
    
    %% Monitoring Flow
    DISCORDBOT -->|Metrics :8000/metrics| PROMETHEUS
    SLACKBOT -->|Metrics :8000/metrics| PROMETHEUS
    PROMETHEUS -->|Data Source| GRAFANA
    PROMETHEUS -->|Alerts| ALERTMANAGER
    ALERTMANAGER -->|Notifications| SLACK_API
    
    %% External API Connections
    DISCORDBOT -->|Bot Commands| DISCORD_API
    SLACKBOT -->|Messages| SLACK_API
    
    %% Configuration
    CONFIGMAPS -->|Config| PROMETHEUS
    CONFIGMAPS -->|Config| GRAFANA
    CONFIGMAPS -->|Config| ALERTMANAGER
    SECRETS -->|Tokens| DISCORDBOT
    SECRETS -->|Webhook URL| ALERTMANAGER
    VOLUMES -->|Storage| PROMETHEUS
    VOLUMES -->|Storage| GRAFANA
    
    %% Styling
    classDef development fill:#e1f5fe
    classDef cicd fill:#f3e5f5
    classDef k8s fill:#e8f5e8
    classDef external fill:#fff3e0
    classDef storage fill:#fce4ec
    
    class DEV,VSCODE,GIT development
    class GITHUB,JENKINS,DOCKERHUB cicd
    class DISCORDBOT,PROMETHEUS,GRAFANA,ALERTMANAGER,SLACKBOT,DISCORD_SVC,PROM_SVC,GRAFANA_SVC,ALERT_SVC,SLACK_SVC k8s
    class DISCORD_API,SLACK_API,DOCKER_REGISTRY external
    class CONFIGMAPS,SECRETS,VOLUMES storage
```

## 📊 포트 및 네트워크 구성

```mermaid
graph LR
    subgraph "Host Machine (Ubuntu)"
        HOST_30090[":30090 NodePort"]
        HOST_30300[":30300 NodePort"]
        HOST_30500[":30500 NodePort"]
        HOST_9093[":9093 Port-Forward"]
    end
    
    subgraph "Kubernetes Cluster"
        subgraph "Discord Bot"
            DISCORD_POD[Discord Bot Pod]
            DISCORD_8000[":8000 Metrics"]
        end
        
        subgraph "Prometheus"
            PROM_POD[Prometheus Pod]
            PROM_9090[":9090 Web UI"]
        end
        
        subgraph "Grafana"
            GRAFANA_POD[Grafana Pod]
            GRAFANA_3000[":3000 Web UI"]
        end
        
        subgraph "AlertManager"
            ALERT_POD[AlertManager Pod]
            ALERT_9093_INT[":9093 Web UI"]
        end
        
        subgraph "Slack Bot"
            SLACK_POD[Slack Bot Pod]
            SLACK_8000[":8000 Metrics"]
            SLACK_5000[":5000 Test Endpoint"]
        end
    end
    
    %% Port Mappings
    HOST_30090 --> PROM_9090
    HOST_30300 --> GRAFANA_3000
    HOST_30500 --> SLACK_5000
    HOST_9093 --> ALERT_9093_INT
    
    %% Internal Connections
    PROM_POD -->|Scrape| DISCORD_8000
    PROM_POD -->|Scrape| SLACK_8000
    GRAFANA_POD -->|Query| PROM_9090
    PROM_POD -->|Send Alerts| ALERT_9093_INT
    
    classDef host fill:#ffeb3b
    classDef internal fill:#4caf50
    class HOST_30090,HOST_30300,HOST_30500,HOST_9093 host
    class DISCORD_8000,PROM_9090,GRAFANA_3000,ALERT_9093_INT,SLACK_8000,SLACK_5000 internal
```

## 🔄 데이터 플로우

```mermaid
sequenceDiagram
    participant User as 사용자
    participant Discord as Discord Bot
    participant Prom as Prometheus
    participant Grafana as Grafana
    participant Alert as AlertManager
    participant Slack as Slack
    
    Note over User,Slack: 정상 운영 플로우
    User->>Discord: ?ping 명령어
    Discord->>User: 응답 + 메트릭 업데이트
    Discord->>Prom: 메트릭 노출 (:8000/metrics)
    
    Note over Prom: 30초마다 스크래핑
    Prom->>Discord: GET /metrics
    Prom->>Grafana: 데이터 제공
    Grafana->>User: 대시보드 표시 (:30300)
    
    Note over User,Slack: 알람 플로우
    Discord->>Discord: 에러 발생 (5회 이상)
    Prom->>Prom: 알람 규칙 평가
    Prom->>Alert: 알람 전송
    Alert->>Slack: Slack 알림 전송
    Slack->>User: 알림 메시지
```

## 🛠️ 배포 플로우

```mermaid
sequenceDiagram
    participant Dev as 개발자
    participant Git as GitHub
    participant Jenkins as Jenkins
    participant Hub as Docker Hub
    participant K8s as Kubernetes
    participant Bot as Discord Bot
    
    Dev->>Git: git push
    Git->>Jenkins: Webhook 트리거
    
    Note over Jenkins: Jenkins Pipeline 실행
    Jenkins->>Jenkins: 1. Checkout 코드
    Jenkins->>Jenkins: 2. Python 테스트
    Jenkins->>Jenkins: 3. Docker 이미지 빌드
    Jenkins->>Hub: 4. 이미지 푸시
    Jenkins->>K8s: 5. Deployment 업데이트
    
    K8s->>Hub: 새 이미지 Pull
    K8s->>Bot: Pod 재배포
    Bot->>Bot: 새 버전 실행
```

## 📋 주요 연결점 요약

### 1. **개발 → 배포**
- GitHub → Jenkins (Webhook)
- Jenkins → Docker Hub (Image Push)
- Jenkins → Kubernetes (Deployment)

### 2. **모니터링 체인**
- Discord Bot → Prometheus (Metrics :8000)
- Slack Bot → Prometheus (Metrics :8000)
- Prometheus → Grafana (Data Source)
- Prometheus → AlertManager (Alerts)

### 3. **알림 체인**
- Prometheus → AlertManager (Alert Rules)
- AlertManager → Slack (Webhook Notifications)

### 4. **네트워크 접근**
- Prometheus: `localhost:30090`
- Grafana: `localhost:30300`
- Slack Bot Test: `localhost:30500`
- AlertManager: `kubectl port-forward` 필요

### 5. **설정 관리**
- ConfigMaps: Prometheus, Grafana, AlertManager 설정
- Secrets: Discord Token, Slack Webhook URL
- Persistent Volumes: Prometheus, Grafana 데이터 저장

이 구조를 통해 **코드 변경부터 모니터링, 알림까지** 완전 자동화된 DevOps 파이프라인이 구현되어 있습니다! 🚀
