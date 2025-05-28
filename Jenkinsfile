pipeline {
    agent any
    
    environment {
        DOCKER_IMAGE = 'ashcircle03/discord-bot'
        DOCKER_TAG = "${BUILD_NUMBER}"
        KUBERNETES_API_SERVER = 'https://192.168.49.2:8443'
    }
    
    // tools 섹션 제거 - Jenkins에 필요한 도구가 이미 설치되어 있음
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Setup Environment') {
            }
            steps {
                sh '''
                    # 시스템 정보 확인
                    echo "시스템 정보 확인 중..."
                    uname -a
                    id
                    
                    # Docker 정보 확인
                    echo "Docker 정보 확인 중..."
                    docker info
                '''
            }
        }

        stage('Run Tests') {
            agent {
                docker {
                    image 'python:3.9'
                    args '-v ${WORKSPACE}:/app'
                }
            }
            steps {
                sh '''
                    cd /app
                    echo "디스코드 봇 테스트 실행 중..."
                    
                    # 홈 디렉토리 설정
                    export HOME=/tmp
                    mkdir -p $HOME/.local
                    
                    # 파이썬 테스트 환경 설정
                    pip install --user pytest pytest-asyncio
                    
                    # 의존성 설치
                    if [ -f "src/requirements.txt" ]; then
                        pip install --user -r src/requirements.txt
                    elif [ -f "requirements.txt" ]; then
                        pip install --user -r requirements.txt
                    fi
                    
                    # 테스트 실행
                    if [ -f "src/test_discord_bot.py" ]; then
                        python -m pytest src/test_discord_bot.py -v
                    else
                        echo "테스트 파일이 없습니다. 테스트를 건너뜁니다."
                    fi
                '''
            }
        }

        stage('Build and Push Docker Image') {
            agent {
                docker {
                    image 'docker:20.10'
                    args '-v /var/run/docker.sock:/var/run/docker.sock -v ${WORKSPACE}:/workspace'
                }
            }
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub', usernameVariable: 'DOCKER_USERNAME', passwordVariable: 'DOCKER_PASSWORD'), string(credentialsId: 'discord-bot-token', variable: 'BOT_TOKEN')]) {
                    sh '''
                        # 작업 디렉토리 확인
                        pwd
                        ls -la
                        
                        # Dockerfile 이 있는지 확인
                        if [ -f "docker/Dockerfile" ]; then
                            echo "Dockerfile 찾음: docker/Dockerfile"
                            # Docker 이미지 빌드
                            docker build -t ${DOCKER_IMAGE}:${DOCKER_TAG} --build-arg BOT_TOKEN=$BOT_TOKEN -f docker/Dockerfile .
                            
                            # Docker Hub에 로그인 및 푸시
                            export DOCKER_CONFIG="$(pwd)/.docker"
                            mkdir -p "${DOCKER_CONFIG}"
                            docker login -u $DOCKER_USERNAME -p ${DOCKER_PASSWORD}
                            docker push ${DOCKER_IMAGE}:${DOCKER_TAG}
                            
                            # 최신 태그도 함께 푸시
                            docker tag ${DOCKER_IMAGE}:${DOCKER_TAG} ${DOCKER_IMAGE}:latest
                            docker push ${DOCKER_IMAGE}:latest
                            
                            # 정리
                            docker rmi ${DOCKER_IMAGE}:${DOCKER_TAG}
                            docker logout
                        else
                            echo "Dockerfile을 찾을 수 없습니다!"
                            exit 1
                        fi
                    '''
                }
            }
        }
        
        stage('Update Deployment Manifest') {
            agent any
            steps {
                sh '''
                    # 시스템 정보 확인
                    echo "현재 디렉토리: $(pwd)"
                    ls -la
                    
                    # 전체 파일 목록 확인
                    echo "모든 YAML 파일 검색:"
                    find . -type f -name "*.yaml" | sort
                    
                    # 이미지 정보 설정
                    NEW_IMAGE="${DOCKER_IMAGE}:${DOCKER_TAG}"
                    echo "새 이미지: $NEW_IMAGE"
                    
                    # 매니페스트 파일 경로 확인
                    DEPLOYMENT_FILE="./k8s/app/deployment.yaml"
                    
                    if [ -f "${DEPLOYMENT_FILE}" ]; then
                        echo "매니페스트 파일 찾음: ${DEPLOYMENT_FILE}"
                    else
                        echo "매니페스트 파일을 찾을 수 없습니다: ${DEPLOYMENT_FILE}"
                        echo "현재 디렉토리 파일 목록:"
                        ls -la
                        exit 1
                    fi
                    
                    sed -i "s|image: .*|image: $NEW_IMAGE|g" $DEPLOYMENT_FILE
                    echo "배포 파일 $DEPLOYMENT_FILE 업데이트 완료"
                    echo "새 이미지: $NEW_IMAGE"
                    cat $DEPLOYMENT_FILE
                '''
            }
        }

        stage('Deploy to Kubernetes') {
            agent {
                kubernetes {
                    yaml '''
                    apiVersion: v1
                    kind: Pod
                    spec:
                      containers:
                      - name: kubectl
                        image: alpine/k8s:1.20.7
                        command:
                        - cat
                        tty: true
                        resources:
                          limits:
                            memory: "256Mi"
                            cpu: "200m"
                          requests:
                            memory: "128Mi"
                            cpu: "100m"
                    '''
                    defaultContainer 'kubectl'
                }
            }
            steps {
                withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
                    sh '''
                        # kubectl 명령어가 있는지 확인
                        if ! command -v kubectl &> /dev/null; then
                            echo "kubectl이 설치되어 있지 않습니다. 건너뜁니다."
                            exit 0
                        fi
                        
                        mkdir -p $HOME/.kube
                        cp $KUBECONFIG $HOME/.kube/config
                        chmod 600 $HOME/.kube/config
                        
                        echo "쿠버네티스에 배포 중..."
                        # 매니페스트 파일 경로 지정
                        DEPLOYMENT_FILE="./k8s/app/deployment.yaml"
                        
                        if [ -f "$DEPLOYMENT_FILE" ]; then
                            echo "매니페스트 파일 찾음: $DEPLOYMENT_FILE"
                            kubectl apply -f $DEPLOYMENT_FILE --insecure-skip-tls-verify || true
                            
                            echo "배포 상태 확인..."
                            kubectl get pods -l app=discord-bot --insecure-skip-tls-verify || true
                        else
                            echo "매니페스트 파일을 찾을 수 없습니다: $DEPLOYMENT_FILE"
                            echo "현재 디렉토리 파일 목록:"
                            ls -la
                            exit 0
                        fi
                    '''
                }
            }
        }
    }
    
    post {
        always {
            withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
                sh '''
                    mkdir -p $HOME/.kube
                    cp $KUBECONFIG $HOME/.kube/config
                    chmod 600 $HOME/.kube/config
                    
                    echo "배포 상태 확인 중..."
                    kubectl get pods -l app=discord-bot --insecure-skip-tls-verify || true
                    kubectl describe deployment discord-bot --insecure-skip-tls-verify || true
                '''
            }
        }
        
        success {
            echo '파이프라인이 성공적으로 완료되었습니다!'
        }
        
        failure {
            echo '파이프라인이 실패했습니다!'
        }
    }
}
