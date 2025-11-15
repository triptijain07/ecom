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

        stage('Stop Old Containers') {
            steps {
                sh '''
                docker stop apigateway || true
                docker stop authservice || true
                docker stop productservice || true
                docker stop shopservice || true
                docker stop inventoryservice || true
                docker stop orderservice || true
                docker stop paymentservice || true
                '''
            }
        }

        stage('Remove Old Containers') {
            steps {
                sh '''
                docker rm apigateway || true
                docker rm authservice || true
                docker rm productservice || true
                docker rm shopservice || true
                docker rm inventoryservice || true
                docker rm orderservice || true
                docker rm paymentservice || true
                '''
            }
        }

        stage('Run New Containers') {
            steps {
                sh '''
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
