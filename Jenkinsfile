pipeline {
    agent any

    environment {
        IMAGE_NAME   = "grocery-app"
        IMAGE_TAG    = "${env.BUILD_NUMBER}"
        DOCKERHUB_REPO = "athanusha/grocery-app"   // TODO: change to your Docker Hub repo
        REGISTRY_CREDENTIALS = credentials('dockerhub-creds') // Jenkins credential ID
    }

    options {
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    stages {

        stage('Checkout') {
            steps {
                echo "Checking out source code from Git..."
                checkout scm
            }
        }

        stage('Install Dependencies') {
            steps {
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }

        stage('Lint') {
            steps {
                sh '''
                    . venv/bin/activate
                    pip install flake8
                    flake8 app --max-line-length=120 --exclude=app/templates || true
                '''
            }
        }

        stage('Run Tests') {
            steps {
                sh '''
                    . venv/bin/activate
                    PYTHONPATH=app pytest tests/ --junitxml=test-results.xml --cov=app --cov-report=xml
                '''
            }
            post {
                always {
                    junit 'test-results.xml'
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    dockerImage = docker.build("${DOCKERHUB_REPO}:${IMAGE_TAG}")
                }
            }
        }

        stage('Push Docker Image') {
            steps {
                script {
                    REGISTRY_CREDENTIALS = credentials('dockerhub-creds') {
                        dockerImage.push("${IMAGE_TAG}")
                        dockerImage.push("latest")
                    }
                }
            }
        }

        stage('Deploy with Ansible') {
            steps {
                echo "Deploying container to target host via Ansible..."
                sh '''
                    ansible-playbook -i ansible/inventory.ini ansible/playbook.yml \
                        --extra-vars "image_tag=${IMAGE_TAG} image_repo=${DOCKERHUB_REPO}"
                '''
            }
        }

        stage('Smoke Test') {
            steps {
                echo "Verifying deployment health..."
                sh '''
                    sleep 10
                    curl -f http://localhost:5000/health || exit 1
                '''
            }
        }
    }

    post {
        success {
            echo "✅ Pipeline completed successfully: Git → Jenkins → Build & Test → Docker Image → Deployment → Monitoring"
        }
        failure {
            echo "❌ Pipeline failed. Check the stage logs above."
        }
        always {
            sh 'docker system prune -f || true'
        }
    }
}
