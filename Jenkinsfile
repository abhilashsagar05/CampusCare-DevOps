pipeline {
    agent any
    options {
        timestamps()
        disableConcurrentBuilds()
    }
    stages {
        stage('Checkout') {
            steps { checkout scm }
        }
        stage('Install dependencies') {
            steps {
                sh 'python3 --version'
                sh 'python3 -m venv .venv'
                sh '. .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt'
            }
        }
        stage('Automated tests') {
            steps {
                sh '. .venv/bin/activate && pytest -v'
            }
        }
        stage('Build Docker image') {
            steps {
                sh 'docker build -t campuscare:${BUILD_NUMBER} .'
            }
        }
    }
    post {
        always { echo 'Pipeline finished. Review test output above.' }
        success { echo 'Tests passed and Docker image was built.' }
        failure { echo 'Pipeline failed. Fix the failing stage before proceeding.' }
    }
}
