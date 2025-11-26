pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                echo "📥 Checking out source code from SCM..."
                // Uses the same repo & branch that triggered the build
                checkout scm
            }
        }

        stage('Build Placeholder') {
            steps {
                echo "🏗️ Running CI pipeline on Windows agent..."
                echo "Here we would normally build Docker images and run tests."
            }
        }

        stage('Smoke Test Placeholder') {
            steps {
                echo "🚦 Smoke test placeholder (Docker/minikube/K8s handled outside Jenkins for now)."
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
