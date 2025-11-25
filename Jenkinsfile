pipeline {
    agent any

    stages {

        stage('Clone Code') {
            steps {
                echo "Repository cloned by Jenkins"
            }
        }

        stage('Install Dependencies') {
            steps {
                sh 'pip3 install -r requirements.txt'
            }
        }

        stage('Static Code Check') {
            steps {
                echo "Running Django check"
                sh 'python3 manage.py check || true'
            }
        }
    }

    post {
        success {
            echo "✔️ Pipeline successfully finished"
        }
        failure {
            echo "❌ Pipeline failed — check logs"
        }
    }
}
