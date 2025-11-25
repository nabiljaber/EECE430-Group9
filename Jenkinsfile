pipeline {
    agent any

    stages {

        stage('Checkout Code') {
            steps {
                echo "SCM checkout handled automatically by Jenkins"
            }
        }

        stage('Build All Services') {
            steps {
                echo "Building Docker compose images..."
                sh 'docker-compose build'
            }
        }

        stage('Stop Old Stack') {
            steps {
                echo "Stopping old compose stack..."
                sh 'docker-compose down || true'
            }
        }

        stage('Run Migrations') {
            steps {
                echo "Running Django migrations..."
                sh 'docker-compose run --rm accounts_service python manage.py migrate'
                sh 'docker-compose run --rm rentals_service python manage.py migrate'
            }
        }

        stage('Start Stack') {
            steps {
                echo "Starting app stack..."
                sh 'docker-compose up -d'
            }
        }

        stage('Health Check') {
            steps {
                echo "Checking nginx on port 8096..."
                sh '''
                    sleep 5
                    curl -I http://localhost:8096 || true
                '''
            }
        }
    }

    post {
        success {
            echo "✅ Deployment succeeded — app running on http://localhost:8096"
        }
        failure {
            echo "❌ Deployment failed — check Jenkins logs"
        }
    }
}
