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
            agent {
                docker {
                    image 'python:3.9'
                    args '-v ${WORKSPACE}:/app'
                    reuseNode true
                }
            }
            steps {
                sh '''
                    echo "디스코드 봇 테스트 실행 중..."
                    cd /app
                    
                    # 파이썬 테스트 환경 설정
                    pip install pytest pytest-asyncio
                    
                    # 의존성 설치
                    if [ -f "src/requirements.txt" ]; then
                        pip install -r src/requirements.txt
                    elif [ -f "requirements.txt" ]; then
                        pip install -r requirements.txt
                    fi
                    
                    # 테스트 실행
                    if [ -f "src/test_discord_bot.py" ]; then
                        cd src && python -m pytest test_discord_bot.py -v
                    elif [ -f "test_discord_bot.py" ]; then
                        python -m pytest test_discord_bot.py -v
                    fi
                '''
            }
        }

        stage('Build and Push Docker Image') {
            agent {
                docker {
                    image 'docker:20.10'
                    args '-v /var/run/docker.sock:/var/run/docker.sock -v ${WORKSPACE}:/workspace'
                    reuseNode true
                }
            }
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
                        cd /workspace
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
            agent {
                docker {
                    image 'alpine:3.14'
                    args '-v ${WORKSPACE}:/workspace'
                    reuseNode true
                }
            }
            steps {
                sh '''
                    cd /workspace
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
            agent {
                docker {
                    image 'bitnami/kubectl:latest'
                    args '-v ${WORKSPACE}:/workspace'
                    reuseNode true
                }
            }
            steps {
                withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
                sh '''
                        cd /workspace
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
            script {
                docker.image('bitnami/kubectl:latest').inside('-v ${WORKSPACE}:/workspace') {
                    withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
                        sh '''
                            cd /workspace
                            mkdir -p $HOME/.kube
                            cp $KUBECONFIG $HOME/.kube/config
                            chmod 600 $HOME/.kube/config
                            
                            echo "Checking deployment status..."
                            kubectl get pods -l app=discord-bot --insecure-skip-tls-verify || true
                            kubectl describe deployment discord-bot --insecure-skip-tls-verify || true
                        '''
                    }
                }
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