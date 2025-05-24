pipeline {
    agent any
    
    environment {
        DOCKER_REGISTRY = 'docker.io'
        DOCKER_IMAGE = 'discord-bot'
        DOCKER_CREDENTIALS = credentials('dockerhub')
        GITHUB_CREDENTIALS = credentials('github')
        KUBECONFIG = credentials('kubeconfig')
        BOT_TOKEN = credentials('discord-bot-token')
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Run Tests') {
            steps {
                sh '''
                    python3 -m pip install -r requirements.txt
                    python3 -m pytest test_discord_bot.py
                '''
            }
        }
        
        stage('Build and Push Docker Image') {
            steps {
                sh '''
                    echo "$DOCKER_CREDENTIALS_PSW" | docker login $DOCKER_REGISTRY -u "$DOCKER_CREDENTIALS_USR" --password-stdin
                    docker build -t $DOCKER_REGISTRY/$DOCKER_CREDENTIALS_USR/$DOCKER_IMAGE:$BUILD_NUMBER \
                        --build-arg BOT_TOKEN=$BOT_TOKEN .
                    docker push $DOCKER_REGISTRY/$DOCKER_CREDENTIALS_USR/$DOCKER_IMAGE:$BUILD_NUMBER
                    docker rmi $DOCKER_REGISTRY/$DOCKER_CREDENTIALS_USR/$DOCKER_IMAGE:$BUILD_NUMBER
                    docker logout $DOCKER_REGISTRY
                '''
            }
        }
        
        stage('Update Deployment Manifest') {
            steps {
                sh '''
                    sed -i "s|\${DOCKER_REGISTRY}|\${DOCKER_REGISTRY}|g" deployment.yaml
                    sed -i "s|\${DOCKER_CREDENTIALS_USR}|\${DOCKER_CREDENTIALS_USR}|g" deployment.yaml
                    sed -i "s|\${DOCKER_IMAGE}|\${DOCKER_IMAGE}|g" deployment.yaml
                    sed -i "s|\${BUILD_NUMBER}|\${BUILD_NUMBER}|g" deployment.yaml
                    
                    git config user.email "jenkins@example.com"
                    git config user.name "Jenkins"
                    
                    git add deployment.yaml
                    git commit -m "Update deployment image to build #$BUILD_NUMBER"
                    git push https://$GITHUB_CREDENTIALS_USR:$GITHUB_CREDENTIALS_PSW@github.com/$GITHUB_CREDENTIALS_USR/project1.git HEAD:main
                '''
            }
        }
        
        stage('Prepare Kubernetes') {
            steps {
                sh '''
                    export KUBECONFIG=$KUBECONFIG
                    
                    # Create Docker registry secret
                    kubectl create secret docker-registry dockerhub-secret \
                        --docker-server=$DOCKER_REGISTRY \
                        --docker-username=$DOCKER_CREDENTIALS_USR \
                        --docker-password=$DOCKER_CREDENTIALS_PSW \
                        --docker-email=jenkins@example.com \
                        -o yaml --dry-run=client | kubectl apply -f -
                    
                    # Create Discord bot token secret
                    kubectl create secret generic discord-bot-secret \
                        --from-literal=bot-token=$BOT_TOKEN \
                        -o yaml --dry-run=client | kubectl apply -f -
                '''
            }
        }
        
        stage('Deploy to Kubernetes') {
            steps {
                sh '''
                    export KUBECONFIG=$KUBECONFIG
                    kubectl apply -f deployment.yaml
                    kubectl rollout status deployment/discord-bot
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
                export KUBECONFIG=$KUBECONFIG
                kubectl logs -l app=discord-bot --tail=100
                kubectl describe deployment discord-bot
                kubectl describe pods -l app=discord-bot
            '''
        }
    }
}