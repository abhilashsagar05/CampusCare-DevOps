pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
        skipDefaultCheckout(true)
    }

    environment {
        APP_CONTAINER   = 'campuscare_devops_project-app-1'
        DB_CONTAINER    = 'campuscare_devops_project-db-1'
        IMAGE_NAME      = 'campuscare:latest'
        APP_PORT        = '5000'
    }

    stages {

        // ── Stage 1: CI ─────────────────────────────────────────────
        stage('Checkout from GitHub') {
            steps {
                deleteDir()
                git branch: 'main',
                    url: 'https://github.com/abhilashsagar05/CampusCare-DevOps.git'
                echo 'Successfully downloaded CampusCare from GitHub!'
            }
        }

        // ── Stage 2: CI ─────────────────────────────────────────────
        stage('Verify Source Code') {
            steps {
                sh '''
                    set -e
                    echo "Checking required files..."
                    test -f app.py          && echo "  app.py           OK"
                    test -f requirements.txt && echo "  requirements.txt OK"
                    test -f Dockerfile       && echo "  Dockerfile       OK"
                    test -f tests/test_app.py && echo "  tests/test_app.py OK"
                    test -f compose.yaml     && echo "  compose.yaml     OK"
                    test -f render.yaml      && echo "  render.yaml      OK"
                    echo "All required files are present."
                '''
            }
        }

        // ── Stage 3: CI ─────────────────────────────────────────────
        stage('Run Python Tests') {
            steps {
                sh '''
                    set -e
                    echo "Starting Python tests inside Docker..."
                    docker run --rm \
                      --mount "type=volume,src=jenkins_home,dst=/app,volume-subpath=workspace/CampusCare-CI-CD,readonly" \
                      -w /app \
                      -e DATABASE_URL=sqlite:////tmp/campuscare-ci.db \
                      python:3.12-slim \
                      sh -c "pip install --no-cache-dir -r requirements.txt && python -m pytest -p no:cacheprovider -v"
                '''
            }
        }

        // ── Stage 4: CI ─────────────────────────────────────────────
        stage('Build Docker Image') {
            steps {
                sh '''
                    set -e
                    echo "Building CampusCare Docker image..."
                    docker build -t campuscare:latest .
                    echo "Image built successfully:"
                    docker images campuscare:latest
                '''
            }
        }

        // ── Stage 5: CD ─────────────────────────────────────────────
        stage('Deploy: Restart App Container') {
            steps {
                sh '''
                    set -e
                    echo "============================================"
                    echo "CD: Deploying new campuscare:latest image..."
                    echo "============================================"

                    # Read env vars directly from the existing app container
                    # Use single quotes on --format so shell does NOT expand $k/$v
                    DATABASE_URL=$(docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' ${APP_CONTAINER} | grep '^DATABASE_URL=' | cut -d= -f2-)
                    SECRET_KEY=$(docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' ${APP_CONTAINER} | grep '^SECRET_KEY=' | cut -d= -f2-)
                    ADMIN_PASS=$(docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' ${APP_CONTAINER} | grep '^CAMPUSCARE_ADMIN_PASSWORD=' | cut -d= -f2-)
                    TECH_PASS=$(docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' ${APP_CONTAINER} | grep '^CAMPUSCARE_TECH_PASSWORD=' | grep -v TECH2 | cut -d= -f2-)
                    TECH2_PASS=$(docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' ${APP_CONTAINER} | grep '^CAMPUSCARE_TECH2_PASSWORD=' | cut -d= -f2-)

                    # Use single quotes on --format so shell does NOT expand $k/$v
                    NETWORK=$(docker inspect --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}}{{end}}' ${APP_CONTAINER})

                    echo "DATABASE_URL: $DATABASE_URL"
                    echo "Docker network: $NETWORK"

                    # Stop and remove the old app container
                    echo "Stopping old container..."
                    docker stop ${APP_CONTAINER} || true
                    docker rm   ${APP_CONTAINER} || true

                    # Start fresh container from the newly built image
                    echo "Starting new container from campuscare:latest..."
                    docker run -d \
                      --name ${APP_CONTAINER} \
                      --network ${NETWORK} \
                      -p ${APP_PORT}:5000 \
                      -e DATABASE_URL="${DATABASE_URL}" \
                      -e SECRET_KEY="${SECRET_KEY}" \
                      -e CAMPUSCARE_ADMIN_PASSWORD="${ADMIN_PASS}" \
                      -e CAMPUSCARE_TECH_PASSWORD="${TECH_PASS}" \
                      -e CAMPUSCARE_TECH2_PASSWORD="${TECH2_PASS}" \
                      --restart unless-stopped \
                      ${IMAGE_NAME}

                    echo "Waiting for app to become healthy..."
                    sleep 8

                    # Confirm container is running
                    STATUS=$(docker inspect --format '{{.State.Status}}' ${APP_CONTAINER})
                    echo "Container status: $STATUS"
                    if [ "$STATUS" != "running" ]; then
                        echo "ERROR: Container failed to start!"
                        docker logs ${APP_CONTAINER} --tail 30
                        exit 1
                    fi

                    echo "============================================"
                    echo "DEPLOYED: campuscare:latest is now running"
                    echo "URL: http://localhost:${APP_PORT}"
                    echo "============================================"
                '''
            }
        }

        // ── Stage 6: CD Smoke Test ───────────────────────────────────
        stage('Smoke Test: Health Check') {
            steps {
                sh '''
                    set -e
                    echo "Running post-deployment smoke test..."
                    sleep 5

                    RESPONSE=$(docker exec ${APP_CONTAINER} python -c \
                      "import urllib.request, json; \
                       r = urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=5); \
                       print(r.read().decode())")

                    echo "Health response: $RESPONSE"

                    if echo "$RESPONSE" | grep -q "healthy"; then
                        echo "SMOKE TEST PASSED: App is healthy and connected to DB!"
                    else
                        echo "SMOKE TEST FAILED: App returned unexpected response!"
                        exit 1
                    fi
                '''
            }
        }

    }

    post {
        success {
            echo '============================================'
            echo 'CI/CD PIPELINE COMPLETE!'
            echo 'Tests passed -> Image built -> App deployed'
            echo 'CampusCare is live at http://localhost:5000'
            echo '============================================'
        }
        failure {
            echo '============================================'
            echo 'PIPELINE FAILED - check the stage above'
            echo '============================================'
        }
        always {
            echo 'Pipeline finished.'
        }
    }
}
