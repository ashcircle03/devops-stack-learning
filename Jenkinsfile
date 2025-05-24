pipeline {
    agent any
    
    environment {
        DOCKER_REGISTRY = 'docker.io'
        DOCKER_IMAGE = 'discord-bot'
        DOCKER_CREDENTIALS = credentials('dockerhub')
        GITHUB_CREDENTIALS = credentials('github')
        KUBECONFIG = credentials('kubeconfig')
        BOT_TOKEN = credentials('discord-bot-token')
        VENV_PATH = "${WORKSPACE}/venv"
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Setup Python') {
            steps {
                sh '''
                    python3 -m venv ${VENV_PATH}
                    . ${VENV_PATH}/bin/activate
                    python3 -m pip install --upgrade pip
                    python3 -m pip install -r requirements.txt
                '''
            }
        }
        
        stage('Run Tests') {
            steps {
                sh '''
                    . ${VENV_PATH}/bin/activate
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
                    git push https://$GITHUB_CREDENTIALS_USR:$GITHUB_CREDENTIALS_PSW@github.com/$GITHUB_CREDENTIALS_USR/discord_bot.git HEAD:main
                '''
            }
        }
        
        stage('Deploy to Kubernetes') {
            steps {
                sh '''
                    mkdir -p ~/.kube
                    cat $KUBECONFIG > ~/.kube/config
                    chmod 600 ~/.kube/config
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
                if [ -f ~/.kube/config ]; then
                    kubectl logs -l app=discord-bot --tail=100 || true
                    kubectl describe deployment discord-bot || true
                    kubectl describe pods -l app=discord-bot || true
                fi
            '''
        }
    }
}