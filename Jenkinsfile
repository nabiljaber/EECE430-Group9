pipeline {
    agent any

    stages {
        stage('Clone Code') {
            steps {
                echo "Repo cloned successfully!"
            }
        }

        stage('Build Placeholder') {
            steps {
                echo "Running CI... (No tests configured)"
            }
        }
    }

    post {
        success {
            echo "✔️ Pipeline finished successfully!"
        }
        failure {
            echo "❌ Pipeline failed"
        }
    }
}
