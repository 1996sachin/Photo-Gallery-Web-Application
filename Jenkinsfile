pipeline {
    agent any

    environment {
        COMPOSE_PROJECT_NAME = "photo-gallery"
    }

    stages {

        stage('Prepare Workspace') {
            steps {
                cleanWs()
                checkout scm
            }
        }

        stage('Copy Environment File') {
            steps {
                withCredentials([file(credentialsId: 'backend-env', variable: 'ENV_FILE')]) {
                    sh '''
                        cp "$ENV_FILE" backend/.env
                    '''
                }
            }
        }

        stage('Stop Old Containers') {
            steps {
                sh '''
                    docker compose down --remove-orphans --volumes || true

                    docker rm -f photo-gallery-api || true
                    docker rm -f photo-gallery-frontend || true
                    docker rm -f photo-gallery-db || true

                    docker network prune -f || true
                '''
            }
        }

        stage('Build Images') {
            steps {
                sh 'docker compose build --no-cache'
            }
        }

        stage('Deploy') {
            steps {
                sh 'docker compose up -d'
            }
        }

        stage('Wait') {
            steps {
                sh 'sleep 20'
            }
        }

        stage('Health Check') {
            steps {
                sh '''
                    curl --fail http://localhost:8005/docs
                '''
            }
        }
    }

    post {
        always {
            sh '''
                docker ps -a
                docker compose logs --tail=50 || true
            '''
        }

        success {
            echo 'Deployment Successful'
        }

        failure {
            echo 'Deployment Failed'
        }
    }
}
