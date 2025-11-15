🚀 E-Commerce Microservices — CI/CD with Jenkins & Docker

This project is a microservices-based E-Commerce system containing 7 services:

API Gateway

Auth Service

Product Service

Shop Service

Inventory Service

Order Service

Payment Service

The entire project is fully automated using Jenkins + Docker.
Whenever you push code to GitHub → Jenkins automatically builds & deploys updated containers.

✔ Features

Microservices architecture

Individual Docker images for each service

Jenkins CI/CD pipeline

Automatic deployment on every GitHub push

Zero-downtime container replacement

📁 Project Structure
/APIGateway
/AuthService
/ProductService
/ShopService
/InventoryService
/OrderService
/PaymentService
Jenkinsfile

🛠 Tech Stack

Python / Django

Docker

Jenkins

GitHub Webhooks

REST APIs

⚙️ Setup Guide (Simple Version)
1️⃣ Install Jenkins
sudo apt update
sudo apt install openjdk-17-jdk -y
sudo apt install jenkins -y

2️⃣ Install Docker
sudo apt install docker.io -y
sudo usermod -aG docker jenkins
sudo systemctl restart jenkins

3️⃣ Add GitHub Credentials in Jenkins

Go to: Jenkins → Manage Credentials

Add:

GitHub Username

Personal Access Token (PAT)

4️⃣ Add Webhook in GitHub

GitHub → Repo → Settings → Webhooks → Add webhook

http://YOUR-SERVER-IP:8080/github-webhook/


Event: Just the push event

🧩 CI/CD Pipeline (Jenkinsfile)
pipeline {
    agent any

    stages {

        stage('Pull Latest Code') {
            steps {
                git branch: 'main', url: 'https://github.com/triptijain07/ecom-microservices.git'
            }
        }

        stage('Build Docker Images') {
            steps {
                sh '''
                docker build -t apigateway ./APIGateway
                docker build -t authservice ./AuthService
                docker build -t productservice ./ProductService
                docker build -t shopservice ./ShopService
                docker build -t inventoryservice ./InventoryService
                docker build -t orderservice ./OrderService
                docker build -t paymentservice ./PaymentService
                '''
            }
        }

        stage('Deploy Containers') {
            steps {
                sh '''
                docker rm -f apigateway authservice productservice shopservice inventoryservice orderservice paymentservice || true

                docker run -d -p 8000:8000 --name apigateway apigateway
                docker run -d -p 8001:8001 --name authservice authservice
                docker run -d -p 8002:8002 --name productservice productservice
                docker run -d -p 8003:8003 --name shopservice shopservice
                docker run -d -p 8004:8004 --name inventoryservice inventoryservice
                docker run -d -p 8005:8005 --name orderservice orderservice
                docker run -d -p 8006:8006 --name paymentservice paymentservice
                '''
            }
        }
    }
}

🔄 How Automatic Deployment Works

1️⃣ Developer pushes code to GitHub
2️⃣ GitHub sends webhook to Jenkins
3️⃣ Jenkins pipeline:

Pulls the latest code

Builds Docker images

Stops old containers

Runs updated containers
4️⃣ Application updates automatically 🚀

