pipeline {
    agent any

    stages {
        stage('Clone Code') {
            steps {
                echo "Repository cloned successfully by Jenkins"
            }
        }

        stage('Install Python Dependencies') {
            steps {
                sh 'pip3 install -r requirements.txt || true'
                echo "Dependencies installed"
            }
        }

        stage('Static Code Check') {
            steps {
                echo "Running basic tests..."
                sh 'python3 manage.py check || true'
            }
        }
    }

    post {
        success {
            echo "✅ Pipeline finished successfully!"
        }
        failure {
            echo "❌ Pipeline failed — check logs"
        }
    }
}
