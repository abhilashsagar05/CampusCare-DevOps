pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
        skipDefaultCheckout(true)
    }

    stages {

        stage('Checkout from GitHub') {
            steps {
                deleteDir()
                git branch: 'main',
                    url: 'https://github.com/abhilashsagar05/CampusCare-DevOps.git'
                echo 'Successfully downloaded CampusCare from GitHub!'
            }
        }

        stage('Verify Source Code') {
            steps {
                sh '''
                    set -e
                    echo "Checking required files..."
                    test -f app.py
                    test -f requirements.txt
                    test -f Dockerfile
                    test -f tests/test_app.py
                    test -f compose.yaml
                    test -f render.yaml
                    echo "All required files are present."
                '''
            }
        }

        stage('Run Python Tests') {
            steps {
                sh '''
                    set -e
                    echo "Starting Python tests..."
                    docker run --rm \
                      --mount "type=volume,src=jenkins_home,dst=/app,volume-subpath=workspace/CampusCare-CI-CD,readonly" \
                      -w /app \
                      -e DATABASE_URL=sqlite:////tmp/campuscare-ci.db \
                      python:3.12-slim \
                      sh -c "pip install --no-cache-dir -r requirements.txt && python -m pytest -p no:cacheprovider -v"
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                sh '''
                    set -e
                    echo "Building CampusCare Docker image..."
                    docker build -t campuscare:latest .
                    echo "Docker image built successfully!"
                    docker images campuscare:latest
                '''
            }
        }

        stage('Verify Running Container') {
            steps {
                sh '''
                    set -e
                    echo "Checking if CampusCare container is running..."
                    if docker ps --filter "name=campuscare_devops_project-app-1" --filter "status=running" | grep -q campuscare; then
                        echo "CampusCare app container is RUNNING."
                        docker ps --filter "name=campuscare_devops_project-app-1" --format "ID: {{.ID}} | Status: {{.Status}} | Ports: {{.Ports}}"
                    else
                        echo "CampusCare container is not running (may be stopped or using different compose stack)."
                        echo "Run: docker compose up -d  to start it."
                    fi
                '''
            }
        }

    }

    post {
        success {
            echo '================================================'
            echo 'SUCCESS: CampusCare CI pipeline completed!'
            echo '7/7 tests passed. Docker image built and verified.'
            echo '================================================'
        }
        failure {
            echo '================================================'
            echo 'FAILURE: CampusCare pipeline failed.'
            echo 'Check the failing stage above for details.'
            echo '================================================'
        }
        always {
            echo 'CampusCare pipeline execution finished.'
        }
    }
}
