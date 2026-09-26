pipeline {
    agent any

    environment {
        IMAGE_NAME   = "grocery-app"
        IMAGE_TAG    = "${env.BUILD_NUMBER}"
        DOCKERHUB_REPO = "athanusha/grocery-app"
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
                sh "docker build -t ${DOCKERHUB_REPO}:${IMAGE_TAG} -t ${DOCKERHUB_REPO}:latest ."
            }
        }

        stage('Push Docker Image') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub-creds', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
                    sh '''
                        echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin
                        docker push ${DOCKERHUB_REPO}:${IMAGE_TAG}
                        docker push ${DOCKERHUB_REPO}:latest
                    '''
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
                    sleep 5
                    docker exec grocery-app python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')"
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