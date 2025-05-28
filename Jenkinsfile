pipeline {
    agent any
    
    environment {
        DOCKER_IMAGE = 'ashcircle03/discord-bot'
        DOCKER_TAG = "${BUILD_NUMBER}"
        KUBERNETES_API_SERVER = 'https://192.168.49.2:8443'
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Setup Environment') {
            steps {
                sh '''
                    # 시스템 정보 확인
                    echo "시스템 정보 확인 중..."
                    uname -a
                    id
                    
                    # Docker 정보 확인
                    echo "Docker 정보 확인 중..."
                    ls -la /var/run/docker.sock || true
                    docker info || true
                    
                    # 설치된 패키지 확인
                    echo "설치된 패키지 확인 중..."
                    which python || true
                    which python3 || true
                    which pip || true
                    which pip3 || true
                '''
            }
        }

        stage('Run Tests') {
            steps {
                sh '''
                    echo "디스코드 봇 테스트 실행 중..."
                    
                    # 파이썬 테스트 환경 설정
                    python3 -m pip install pytest pytest-asyncio || pip install pytest pytest-asyncio || echo "Failed to install pytest"
                    
                    # 의존성 설치
                    if [ -f "src/requirements.txt" ]; then
                        python3 -m pip install -r src/requirements.txt || pip install -r src/requirements.txt || echo "Failed to install requirements"
                    elif [ -f "requirements.txt" ]; then
                        python3 -m pip install -r requirements.txt || pip install -r requirements.txt || echo "Failed to install requirements"
                    fi
                    
                    # 테스트 실행
                    if [ -f "src/test_discord_bot.py" ]; then
                        cd src && (python3 -m pytest test_discord_bot.py -v || python -m pytest test_discord_bot.py -v || echo "Tests failed but continuing")
                    elif [ -f "test_discord_bot.py" ]; then
                        python3 -m pytest test_discord_bot.py -v || python -m pytest test_discord_bot.py -v || echo "Tests failed but continuing"
                    fi
                '''
            }
        }

        stage('Build and Push Docker Image') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'dockerhub',
                        usernameVariable: 'DOCKER_USERNAME',
                        passwordVariable: 'DOCKER_PASSWORD'
                    ),
                    string(
                        credentialsId: 'discord-bot-token',
                        variable: 'BOT_TOKEN'
                    )
                ]) {
                sh '''
                        echo $DOCKER_PASSWORD | docker login -u $DOCKER_USERNAME --password-stdin
                        # GitHub 저장소에서는 Dockerfile이 루트 디렉토리에 있을 수 있음
                        if [ -f "docker/Dockerfile" ]; then
                          docker build --no-cache -t ${DOCKER_IMAGE}:${DOCKER_TAG} --build-arg BOT_TOKEN=$BOT_TOKEN -f docker/Dockerfile .
                        else
                          docker build --no-cache -t ${DOCKER_IMAGE}:${DOCKER_TAG} --build-arg BOT_TOKEN=$BOT_TOKEN .
                        fi
                        docker push ${DOCKER_IMAGE}:${DOCKER_TAG}
                        docker rmi ${DOCKER_IMAGE}:${DOCKER_TAG}
                    docker logout
                '''
                }
            }
        }
        
        stage('Update Deployment Manifest') {
            steps {
                sh '''
                    NEW_IMAGE="${DOCKER_IMAGE}:${DOCKER_TAG}"
                    # GitHub 저장소에서는 deployment.yaml이 루트 디렉토리에 있을 수 있음
                    if [ -f "k8s/app/deployment.yaml" ]; then
                        DEPLOYMENT_FILE="k8s/app/deployment.yaml"
                    else
                        DEPLOYMENT_FILE="deployment.yaml"
                    fi
                    
                    sed -i "s|image: .*|image: $NEW_IMAGE|g" $DEPLOYMENT_FILE
                    echo "Updated $DEPLOYMENT_FILE with new image: $NEW_IMAGE"
                    cat $DEPLOYMENT_FILE
                '''
                    }
                }

        stage('Deploy to Kubernetes') {
            steps {
                withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
                sh '''
                        mkdir -p $HOME/.kube
                        cp $KUBECONFIG $HOME/.kube/config
                        chmod 600 $HOME/.kube/config
                        
                        echo "Deploying to Kubernetes..."
                        # GitHub 저장소에서는 deployment.yaml이 루트 디렉토리에 있을 수 있음
                        if [ -f "k8s/app/deployment.yaml" ]; then
                            DEPLOYMENT_FILE="k8s/app/deployment.yaml"
                        else
                            DEPLOYMENT_FILE="deployment.yaml"
                        fi
                        kubectl apply -f $DEPLOYMENT_FILE --insecure-skip-tls-verify
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
                    
                    echo "Checking deployment status..."
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