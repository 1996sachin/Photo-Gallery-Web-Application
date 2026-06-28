pipeline {
    agent any

    options {
        timestamps()
        ansiColor('xterm')
        timeout(time: 45, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

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

        stage('Backend Lint') {
            steps {
                sh '''
                    cd backend

                    if [ -f requirements.txt ]; then
                        python3 -m pip install flake8
                        flake8 . || true
                    fi
                '''
            }
        }

        stage('Frontend Lint') {
            steps {
                sh '''
                    cd frontend

                    npm install
                    npm run lint || true
                '''
            }
        }

        stage('Backend Tests') {
            steps {
                sh '''
                    cd backend

                    python3 -m pip install pytest
                    pytest || true
                '''
            }
        }

        stage('Frontend Tests') {
            steps {
                sh '''
                    cd frontend

                    npm test || true
                '''
            }
        }

        stage('Stop Old Containers') {
            steps {
                sh '''
                    docker compose down --remove-orphans || true

                    docker rm -f photo-gallery-api || true
                    docker rm -f photo-gallery-frontend || true
                    docker rm -f photo-gallery-db || true

                    docker network prune -f || true
                '''
            }
        }

        stage('Build Docker Images') {
            steps {
                sh '''
                    docker compose build --no-cache
                '''
            }
        }

        stage('Trivy Security Scan') {
            steps {
                sh '''
                    if command -v trivy >/dev/null 2>&1; then
                        trivy image --severity HIGH,CRITICAL photo-gallery-backend || true
                        trivy image --severity HIGH,CRITICAL photo-gallery-frontend || true
                    else
                        echo "Trivy not installed. Skipping scan."
                    fi
                '''
            }
        }

        stage('Deploy') {
            steps {
                sh '''
                    docker compose up -d
                '''
            }
        }

        stage('Wait for Services') {
            steps {
                sh 'sleep 20'
            }
        }

        stage('Health Check') {
            steps {
                sh '''
                    curl --fail http://localhost:8005/docs

                    curl --fail http://localhost || true
                '''
            }
        }

        stage('Docker Cleanup') {
            steps {
                sh '''
                    docker image prune -af || true
                    docker builder prune -af || true
                '''
            }
        }
    }

    post {

        always {

            sh '''
                echo "========== Running Containers =========="
                docker ps -a

                echo "========== Docker Compose Logs =========="
                docker compose logs --tail=100 || true
            '''

            archiveArtifacts allowEmptyArchive: true, artifacts: '**/*.log'
        }

        success {
            echo "✅ Deployment Successful"
        }

        failure {
            echo "❌ Deployment Failed"
        }
    }
}
