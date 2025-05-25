pipeline {
    agent any
    
    environment {
        DOCKER_REGISTRY = 'docker.io'
        DOCKER_IMAGE = 'discord-bot'
        DOCKER_CREDENTIALS = credentials('dockerhub')
        GITHUB_CREDENTIALS = credentials('github')
        KUBECONFIG = credentials('kubeconfig')
        BOT_TOKEN = credentials('discord-bot-token')
        DOCKER_USERNAME = 'ashcircle03'
    }
    
    stages {
        stage('Checkout') {
            steps {
                cleanWs()
                
                checkout([
                    $class: 'GitSCM',
                    branches: [[name: 'refs/heads/master']],
                    extensions: [
                        [$class: 'CleanBeforeCheckout'],
                        [$class: 'CloneOption', depth: 1, noTags: true, reference: '', shallow: true],
                        [$class: 'LocalBranch', localBranch: 'master']
                    ],
                    userRemoteConfigs: [[
                        credentialsId: 'github',
                        url: 'https://github.com/ashcircle03/discord_bot.git'
                    ]]
                ])
                
                sh '''
                    git config --global user.email "jenkins@example.com"
                    git config --global user.name "Jenkins"
                    git config --global --add safe.directory /var/jenkins_home/workspace/discord-bot-pipeline
                    git checkout master
                '''
            }
        }
        
        stage('Setup Python') {
            steps {
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    python3 -m pip install --upgrade pip
                    python3 -m pip install -r requirements.txt
                '''
            }
        }
        
        stage('Run Tests') {
            steps {
                sh '''
                    . venv/bin/activate
                    python3 -m pytest test_discord_bot.py
                '''
            }
        }
        
        stage('Build and Push Docker Image') {
            steps {
                sh '''
                    echo "$DOCKER_CREDENTIALS_PSW" | docker login -u "$DOCKER_USERNAME" --password-stdin
                    docker build -t $DOCKER_USERNAME/$DOCKER_IMAGE:$BUILD_NUMBER \
                        --build-arg BOT_TOKEN=$BOT_TOKEN .
                    docker push $DOCKER_USERNAME/$DOCKER_IMAGE:$BUILD_NUMBER
                    docker rmi $DOCKER_USERNAME/$DOCKER_IMAGE:$BUILD_NUMBER
                    docker logout
                '''
            }
        }
        
        stage('Update Deployment Manifest') {
            steps {
                script {
                    withCredentials([usernamePassword(credentialsId: 'github', usernameVariable: 'GIT_USERNAME', passwordVariable: 'GIT_PASSWORD')]) {
                        sh """
                            # Git 설정
                            git config --global user.email "jenkins@example.com"
                            git config --global user.name "Jenkins"
                            
                            # 현재 브랜치 확인 및 처리
                            CURRENT_BRANCH=\$(git rev-parse --abbrev-ref HEAD)
                            if [ "\$CURRENT_BRANCH" = "HEAD" ]; then
                                git checkout -B master
                            fi
                            
                            # 원격 저장소 설정
                            git remote set-url origin https://${GIT_USERNAME}:${GIT_PASSWORD}@github.com/${GIT_USERNAME}/discord_bot.git
                            
                            # 최신 변경사항 가져오기
                            git fetch origin master
                            git reset --hard origin/master
                            
                            # deployment.yaml 업데이트
                            NEW_IMAGE="docker.io/${DOCKER_USERNAME}/${DOCKER_IMAGE}:${BUILD_NUMBER}"
                            # 정확한 패턴으로 이미지 태그 교체
                            sed -i "s|image: docker.io/.*/discord-bot:[0-9]*|image: \${NEW_IMAGE}|g" deployment.yaml
                            
                            # 변경사항 확인
                            echo "Updated deployment.yaml with new image: \${NEW_IMAGE}"
                            cat deployment.yaml
                            
                            # 변경사항 커밋 및 푸시
                            git add deployment.yaml
                            git commit -m "Update deployment image to build #${BUILD_NUMBER}"
                            git push origin master
                        """
                    }
                }
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                sh '''
                    mkdir -p ~/.kube
                    cat $KUBECONFIG > ~/.kube/config
                    chmod 600 ~/.kube/config
                    
                    echo "Applying deployment.yaml..."
                    kubectl apply -f deployment.yaml
                    
                    echo "Waiting for deployment rollout..."
                    kubectl rollout status deployment/discord-bot
                    
                    echo "Checking pod status..."
                    kubectl get pods -l app=discord-bot
                '''
            }
        }
    }
    
    post {
        always {
            cleanWs()
        }
        failure {
            sh '''
                if [ -f ~/.kube/config ]; then
                    kubectl logs -l app=discord-bot --tail=100 || true
                    kubectl describe deployment discord-bot || true
                    kubectl describe pods -l app=discord-bot || true
                fi
            '''
        }
    }
}