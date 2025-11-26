pipeline {
    agent any

    environment {
        COMPOSE_FILE = 'docker-compose.yml'
    }

    stages {
        stage('Checkout') {
            steps {
                echo "📥 Checking out source code from SCM..."
                checkout scm
            }
        }

        stage('Build Docker Images') {
            steps {
                echo "🐳 Building Docker images for microservices..."
                sh 'docker compose build'
            }
        }

        stage('Run Services (Smoke Test)') {
            steps {
                echo "🚀 Starting Docker stack for smoke testing..."
                sh '''
                    docker compose up -d
                    echo "⏳ Waiting for services to start..."
                    sleep 25

                    echo "🔎 Hitting gateway through nginx on port 8096..."
                    curl -f http://localhost:8096 || (echo "❌ Health check failed" && docker compose logs && exit 1)

                    echo "✅ Smoke test passed!"
                '''
            }
        }
    }

    post {
        always {
            echo "🧹 Cleaning up Docker containers..."
            sh 'docker compose down || true'
        }
        success {
            echo "✔️ Pipeline finished successfully!"
        }
        failure {
            echo "❌ Pipeline failed"
        }
    }
}
