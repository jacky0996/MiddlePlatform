// Middle_Platform CD pipeline — Jenkins (本機) 觸發
//
// 流程:GitHub merge to main → Jenkins webhook → 跑這個 pipeline
//   1. Checkout
//   2. Build image(Dockerfile.prod)
//   3. Push 到 Artifact Registry
//   4. Deploy 到 Cloud Run(帶上 secret env / SQL connection)
//   5. Smoke test:curl /healthz,回 200 才算成功
//   6. 失敗 → 自動 rollback 到上一個 revision
//
// 前置條件(README.md 第 3 節):
//   - Jenkins credential: gcp-sa-key(Secret file,SA JSON)
//   - 容器內已 apt-get install google-cloud-cli

pipeline {
    agent any

    environment {
        // GCP project 對應這個服務的 project(每個服務獨立一個 GCP project)
        GCP_PROJECT   = 'middleplatform-496708'
        GCP_REGION    = 'asia-east1'
        AR_REPO       = 'middle-platform'  // Artifact Registry repo
        SERVICE_NAME  = 'middle-platform'  // Cloud Run service name

        // 完整 image tag,用 git short SHA 標記 — 永遠可追溯到 commit
        IMAGE_TAG     = "${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/${AR_REPO}/${SERVICE_NAME}:${GIT_COMMIT.take(7)}"
        IMAGE_LATEST  = "${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/${AR_REPO}/${SERVICE_NAME}:latest"
    }

    options {
        // 一次只跑一個 deploy,避免兩個 build 同時打 Cloud Run
        disableConcurrentBuilds()
        timeout(time: 20, unit: 'MINUTES')
        timestamps()
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Authenticate GCP') {
            steps {
                withCredentials([file(credentialsId: 'gcp-sa-key', variable: 'GCP_KEY')]) {
                    sh '''
                        gcloud auth activate-service-account --key-file=$GCP_KEY
                        gcloud config set project $GCP_PROJECT
                        gcloud auth configure-docker $GCP_REGION-docker.pkg.dev --quiet
                    '''
                }
            }
        }

        stage('Build image') {
            steps {
                sh 'docker build -f Dockerfile.prod -t $IMAGE_TAG -t $IMAGE_LATEST .'
            }
        }

        stage('Push to Artifact Registry') {
            steps {
                sh '''
                    docker push $IMAGE_TAG
                    docker push $IMAGE_LATEST
                '''
            }
        }

        stage('Deploy to Cloud Run') {
            steps {
                // 注意:env / secret 由 Cloud Run secret manager / env 注入,不寫死在 image
                // 第一次部署前要在 GCP Console / gcloud 設好 secret 與 service env
                sh '''
                    gcloud run deploy $SERVICE_NAME \
                        --image=$IMAGE_TAG \
                        --region=$GCP_REGION \
                        --platform=managed \
                        --allow-unauthenticated \
                        --min-instances=1 \
                        --max-instances=5 \
                        --memory=512Mi \
                        --cpu=1 \
                        --port=8080 \
                        --timeout=60 \
                        --quiet
                '''
            }
        }

        stage('Smoke test') {
            steps {
                script {
                    def url = sh(
                        script: "gcloud run services describe $SERVICE_NAME --region=$GCP_REGION --format='value(status.url)'",
                        returnStdout: true
                    ).trim()

                    // 拉幾次,Cloud Run 冷啟動可能需要幾秒
                    def maxRetries = 6
                    def ok = false
                    for (int i = 0; i < maxRetries; i++) {
                        def status = sh(
                            script: "curl -s -o /dev/null -w '%{http_code}' ${url}/healthz",
                            returnStdout: true
                        ).trim()
                        if (status == '200') {
                            ok = true
                            echo "Smoke test passed: ${url}/healthz returned 200"
                            break
                        }
                        echo "Attempt ${i+1}: status=${status},等 5 秒再試"
                        sleep 5
                    }
                    if (!ok) {
                        error 'Smoke test failed — 觸發 rollback'
                    }
                }
            }
        }
    }

    post {
        failure {
            // Deploy 完才失敗 → rollback 到前一個 revision
            // (Build/Push 階段失敗則不需,因為 Cloud Run 還沒更新)
            script {
                def prev = sh(
                    script: """
                        gcloud run revisions list \
                            --service=$SERVICE_NAME \
                            --region=$GCP_REGION \
                            --format='value(metadata.name)' \
                            --limit=2 | tail -n1
                    """,
                    returnStdout: true
                ).trim()
                if (prev) {
                    echo "Rolling back to revision: ${prev}"
                    sh """
                        gcloud run services update-traffic $SERVICE_NAME \
                            --region=$GCP_REGION \
                            --to-revisions=${prev}=100 \
                            --quiet
                    """
                }
            }
        }
        always {
            // 清掉本機 image,避免 Jenkins host 撐爆
            sh 'docker image prune -f --filter "until=24h" || true'
        }
    }
}
