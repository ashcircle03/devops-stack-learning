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
                        docker build -t ${DOCKER_IMAGE}:${DOCKER_TAG} --build-arg BOT_TOKEN=$BOT_TOKEN .
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
                    sed -i "s|image: .*|image: $NEW_IMAGE|g" deployment.yaml
                    echo "Updated deployment.yaml with new image: $NEW_IMAGE"
                    cat deployment.yaml
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
                        kubectl apply -f deployment.yaml --insecure-skip-tls-verify
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
            echo 'Pipeline completed successfully!'
        }
        
        failure {
            echo 'Pipeline failed!'
        }
    }
}