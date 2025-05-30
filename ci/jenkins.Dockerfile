FROM jenkins/jenkins:lts

USER root

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-full \
    curl \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    software-properties-common

# Docker 설치
RUN curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
RUN echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
RUN apt-get update && apt-get install -y docker-ce docker-ce-cli containerd.io

# kubectl 설치
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && chmod +x kubectl \
    && mv kubectl /usr/local/bin/

# Jenkins 사용자를 docker 그룹에 추가
RUN groupadd -f docker && usermod -aG docker jenkins

USER jenkins 