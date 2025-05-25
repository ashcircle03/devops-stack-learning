pipeline {
    agent any
    
    environment {
        DOCKER_REGISTRY = 'docker.io'
        DOCKER_IMAGE = 'discord-bot'
        DOCKER_CREDENTIALS = credentials('dockerhub-credentials')
        BOT_TOKEN = credentials('discord-bot-token')
        KUBECONFIG = credentials('kubeconfig')
        DOCKER_USERNAME = 'ashcircle03'
        KUBERNETES_API_SERVER = 'https://192.168.49.2:8443'
    }
    
    stages {
        stage('Checkout') {
            steps {
                cleanWs()
                checkout scm
            }
        }
        
        stage('Build and Push Docker Image') {
            steps {
                sh '''
                    echo $DOCKER_CREDENTIALS_PSW | docker login -u $DOCKER_CREDENTIALS_USR --password-stdin
                    docker build -t ashcircle03/discord-bot:${BUILD_NUMBER} --build-arg BOT_TOKEN=$BOT_TOKEN .
                    docker push ashcircle03/discord-bot:${BUILD_NUMBER}
                    docker rmi ashcircle03/discord-bot:${BUILD_NUMBER}
                    docker logout
                '''
            }
        }
        
        stage('Update Deployment Manifest') {
            steps {
                sh '''
                    NEW_IMAGE="docker.io/ashcircle03/discord-bot:${BUILD_NUMBER}"
                    sed -i "s|image: docker.io/.*/discord-bot:[0-9]*|image: $NEW_IMAGE|g" deployment.yaml
                    echo "Updated deployment.yaml with new image: $NEW_IMAGE"
                    cat deployment.yaml
                '''
            }
        }
        
        stage('Deploy to Kubernetes') {
            steps {
                sh '''
                    # kubeconfig 설정
                    mkdir -p $HOME/.kube
                    echo "$KUBECONFIG" > $HOME/.kube/config
                    chmod 600 $HOME/.kube/config
                    
                    echo "Applying deployment.yaml..."
                    kubectl apply -f deployment.yaml --validate=false --server=$KUBERNETES_API_SERVER --insecure-skip-tls-verify
                '''
            }
        }
    }
    
    post {
        always {
            cleanWs()
            sh '''
                # kubeconfig 설정
                mkdir -p $HOME/.kube
                echo "$KUBECONFIG" > $HOME/.kube/config
                chmod 600 $HOME/.kube/config
                
                echo "Checking deployment status..."
                kubectl get pods -l app=discord-bot --validate=false --server=$KUBERNETES_API_SERVER --insecure-skip-tls-verify || true
                kubectl describe deployment discord-bot --validate=false --server=$KUBERNETES_API_SERVER --insecure-skip-tls-verify || true
            '''
        }
    }
}