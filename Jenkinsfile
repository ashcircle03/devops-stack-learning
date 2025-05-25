pipeline {
    agent any
    
    environment {
        DOCKER_REGISTRY = 'docker.io'
        DOCKER_IMAGE = 'discord-bot'
        DOCKER_CREDENTIALS = credentials('dockerhub')
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
                    branches: [[name: 'refs/heads/main']],
                    extensions: [
                        [$class: 'CleanBeforeCheckout'],
                        [$class: 'CloneOption', depth: 1, noTags: true, reference: '', shallow: true]
                    ],
                    userRemoteConfigs: [[
                        credentialsId: 'github',
                        url: 'https://github.com/ashcircle03/discord_bot.git'
                    ]]
                ])
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
                sh """
                    # deployment.yaml 업데이트
                    NEW_IMAGE="docker.io/${DOCKER_USERNAME}/${DOCKER_IMAGE}:${BUILD_NUMBER}"
                    # 정확한 패턴으로 이미지 태그 교체
                    sed -i "s|image: docker.io/.*/discord-bot:[0-9]*|image: \${NEW_IMAGE}|g" deployment.yaml
                    
                    # 변경사항 확인
                    echo "Updated deployment.yaml with new image: \${NEW_IMAGE}"
                    cat deployment.yaml
                """
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