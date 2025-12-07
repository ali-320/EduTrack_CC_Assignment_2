# EduTrack Microservices (v1.0.1)

This repository contains the backend microservices for EduTrack, an online learning platform. These services are designed to run on Google Kubernetes Engine (GKE) and integrate with Google Cloud SQL.

## Table of Contents
1.  [Overview](#1-overview)
2.  [Microservices](#2-microservices)
3.  [Deployment Architecture](#3-deployment-architecture)
4.  [Prerequisites](#4-prerequisites)
5.  [Setup Instructions](#5-setup-instructions)
    *   [Google Cloud Setup](#google-cloud-setup)
    *   [Kubernetes Setup](#kubernetes-setup)
6.  [Interacting with the API](#7-interacting-with-the-api)
7.  [Troubleshooting](#8-troubleshooting)

## 1. Overview

EduTrack's backend is composed of several microservices, each handling a specific domain: Student Management, Course Catalog, and Enrollment. All services connect to their dedicated PostgreSQL Cloud SQL instances via the Cloud SQL Auth Proxy running as a sidecar container.

## 2. Microservices

*   **Student Service:** Manages student registration and profiles.
    *   **Database:** `student_db` on `student-db-instance`
    *   **Endpoints:**
        *   `GET /students`: List all registered students.
        *   `POST /students`: Register a new student.
        *   `GET /students/<id>`: View a student's profile (Needs implementation).
*   **Course Service:** Manages the course catalog.
    *   **Database:** `course_db` on `course-db-instance`
    *   **Endpoints:**
        *   `GET /courses`: List all available courses.
        *   `GET /courses/<id>`: View details of a specific course.
        *   `POST /courses`: Add a new course (Needs implementation).
*   **Enrollment Service:** Handles student enrollments in courses.
    *   **Database:** `enrollment_db` on `enrollment-db-instance`
    *   **Endpoints:**
        *   `POST /enrollments`: Enroll a student in a course.
        *   `GET /enrollments/<student_id>`: List courses a specific student is enrolled in.

## 3. Deployment Architecture

The services are deployed to GKE. Each microservice runs in its own Kubernetes Deployment, and each pod contains:
*   An application container (Flask app)
*   A `cloudsql-proxy` sidecar container for secure, encrypted connections to Cloud SQL.

Traffic is exposed externally via a GKE Ingress, which provisions a Google Cloud HTTP(S) Load Balancer.

**Key Components:**
*   **GKE Cluster:** `edutrack-gke-cluster`
*   **Cloud SQL (PostgreSQL):** `student-db-instance`, `course-db-instance`, `enrollment-db-instance`
*   **Container Registry:** `us-central1-docker.pkg.dev/edutrack-cc-ass-2/edutrack-docker-repo`
*   **Kubernetes Secrets:** Used to securely inject database passwords and Cloud SQL Proxy service account keys.

## 4. Prerequisites

Before deploying, ensure you have:
*   A Google Cloud Project (`edutrack-cc-ass-2`).
*   The `gcloud` CLI and `kubectl` installed and configured.
*   A GKE cluster named `edutrack-gke-cluster` in `us-central1-a`.
*   Cloud SQL instances (`student-db-instance`, `course-db-instance`, `enrollment-db-instance`) created within your project.
*   Dedicated databases (e.g., `student_db`, `course_db`, `enrollment_db`) and users within each Cloud SQL instance.
*   Initial database schemas (tables) created in each database.

## 5. Setup Instructions

### Google Cloud Setup

1.  **Create Cloud SQL Instances:**
    Ensure you have created the three PostgreSQL instances: `student-db-instance`, `course-db-instance`, `enrollment-db-instance`. Note their connection names (e.g., `edutrack-cc-ass-2:us-central1-a:student-db-instance`).

2.  **Create Databases and Users:**
    Within each Cloud SQL instance, create the respective database (e.g., `student_db`) and a dedicated user (e.g., `student_user`) with a strong password.

3.  **Create Cloud SQL Proxy Service Accounts & Keys:**
    For each service, create a Google Cloud Service Account with the `roles/cloudsql.client` role and download its JSON key file.
    *   `student-db-proxy-sa` (for `student-service`)
    *   `course-db-proxy-sa` (for `course-service`)
    *   `enrollment-db-proxy-sa` (for `enrollment-service`)
    *   **Remember to keep these JSON key files secure and do not commit them to Git.**

### Kubernetes Setup

1.  **Create Kubernetes Secrets for DB Passwords:**
    For each service, create a Kubernetes Secret containing the database user's password.
    ```bash
    kubectl create secret generic student-db-password-secret --from-literal=db_password='YOUR_STUDENT_DB_PASSWORD'
    kubectl create secret generic course-db-password-secret --from-literal=db_password='YOUR_COURSE_DB_PASSWORD'
    kubectl create secret generic enrollment-db-password-secret --from-literal=db_password='YOUR_ENROLLMENT_DB_PASSWORD'
    ```

2.  **Create Kubernetes Secrets for Cloud SQL Proxy Keys:**
    For each service, create a Kubernetes Secret from the downloaded JSON key files.
    ```bash
    kubectl create secret generic student-db-proxy-secret --from-file=credentials.json=student-db-proxy-key.json
    kubectl create secret generic course-db-proxy-secret --from-file=credentials.json=course-db-proxy-key.json
    kubectl create secret generic enrollment-db-proxy-secret --from-file=credentials.json=enrollment-db-proxy-key.json
    ```

3.  **Update `app.py` Files:**
    Ensure all `app.py` files (student, course, enrollment) have:
    *   The `GET /` health check endpoint.
    *   `DB_HOST` set to `127.0.0.1` in the Deployment YAML (not directly in `app.py`).
    *   Correct `DB_NAME`, `DB_USER` environment variables in their Deployment YAMLs.
    *   The `register_student` method in `student-service/app.py` updated to accept `first_name`, `last_name`, and `email`.
    *   All SQL queries updated to match the exact column names (e.g., `first_name`, `last_name`, `registration_date` for students; `course_id`, `start_date`, `end_date`, `price` for courses; `enrollment_id`, `status` for enrollments).

4.  **Update `requirements.txt` (Recommended):**
    Change `psycopg2` to `psycopg2-binary` for simpler and faster Docker builds:
    ```
    Flask
    psycopg2-binary
    ```

5.  **Update `Dockerfile` (if using `psycopg2-binary`):**
    Remove the `RUN apt-get update && apt-get install -y libpq-dev gcc` line. Your Dockerfile should look like the standard Python Flask one.

6.  **Rebuild and Push Docker Images:**
    Build new Docker images for each service with the `v1.0.1` tag and push them to your Artifact Registry:
    ```bash
    # For student-service
    cd student-service && docker build -t us-central1-docker.pkg.dev/edutrack-cc-ass-2/edutrack-docker-repo/student-service:v1.0.1 . && docker push us-central1-docker.pkg.dev/edutrack-cc-ass-2/edutrack-docker-repo/student-service:v1.0.1 && cd ..
    # For course-service
    cd course-service && docker build -t us-central1-docker.pkg.dev/edutrack-cc-ass-2/edutrack-docker-repo/course-service:v1.0.1 . && docker push us-central1-docker.pkg.dev/edutrack-cc-ass-2/edutrack-docker-repo/course-service:v1.0.1 && cd ..
    # For enrollment-service
    cd enrollment-service && docker build -t us-central1-docker.pkg.dev/edutrack-cc-ass-2/edutrack-docker-repo/enrollment-service:v1.0.1 . && docker push us-central1-docker.pkg.dev/edutrack-cc-ass-2/edutrack-docker-repo/enrollment-service:v1.0.1 && cd ..
    ```

7.  **Update Kubernetes Deployment YAMLs:**
    Modify `k8s/*.yaml` files to reference the new `v1.0.1` image tag for each service and ensure the `cloudsql-proxy` sidecar is configured with `edutrack-cc-ass-2:<REGION>:<INSTANCE_NAME>` and `--credentials-file=/secrets/cloudsql/credentials.json`. Also, ensure `DB_HOST` in the app container points to `127.0.0.1`.

8.  **Apply Kubernetes Deployments and Ingress:**
    ```bash
    kubectl apply -f k8s/student-service-deployment.yaml
    kubectl apply -f k8s/course-service-deployment.yaml
    kubectl apply -f k8s/enrollment-service-deployment.yaml
    kubectl apply -f k8s/edutrack-ingress.yaml # Ensure this Ingress is correctly defined
    ```

## 7. Interacting with the API

First, get your Ingress IP:
`kubectl get ingress edutrack-ingress -o jsonpath='{.status.loadBalancer.ingress[0].ip}'`

Replace `YOUR_INGRESS_IP` with the obtained IP address.

**Student Service:**
*   **Register Student:**
    ```bash
    curl -X POST -H "Content-Type: application/json" \
         -d '{"first_name": "Jane", "last_name": "Doe", "email": "jane.doe@example.com"}' \
         http://YOUR_INGRESS_IP/students
    ```
*   **List Students:**
    ```bash
    curl http://YOUR_INGRESS_IP/students
    ```

**Course Service:**
*   *(If `POST /courses` endpoint is implemented):*
    ```bash
    curl -X POST -H "Content-Type: application/json" \
         -d '{"title": "GKE Fundamentals", "description": "Intro to K8s on GCP", "instructor": "Cloud Guru", "start_date": "2024-06-01", "end_date": "2024-07-01", "price": 199.99}' \
         http://YOUR_INGRESS_IP/courses
    ```
*   **List Courses:**
    ```bash
    curl http://YOUR_INGRESS_IP/courses
    ```
*   **Get Specific Course (e.g., ID 1):**
    ```bash
    curl http://YOUR_INGRESS_IP/courses/1
    ```

**Enrollment Service:**
*   **Enroll Student (e.g., student_id=1, course_id=1):**
    ```bash
    curl -X POST -H "Content-Type: application/json" \
         -d '{"student_id": 1, "course_id": 1, "status": "enrolled"}' \
         http://YOUR_INGRESS_IP/enrollments
    ```
*   **Get Student Enrollments (e.g., student_id=1):**
    ```bash
    curl http://YOUR_INGRESS_IP/enrollments/1
    ```

## 8. Troubleshooting

*   **502 Bad Gateway from Ingress:**
    *   Check Backend Services health in GCP Load Balancing console. If unhealthy, check application logs.
    *   Ensure your `app.py` has a `GET /` endpoint returning `200 OK`.
    *   Verify Docker image builds and correct tag usage in Deployments.
*   **Pod `CrashLoopBackOff`:**
    *   Run `kubectl logs <pod-name> -c <container-name> --previous` to see why the container crashed.
    *   Common issues: incorrect environment variables, missing dependencies, application code errors, incorrect Cloud SQL Proxy flags (`--credentials-file` vs `-credentials-file`).
*   **Database Connection Errors in App Logs:**
    *   Verify `cloudsql-proxy` sidecar logs (`kubectl logs <pod-name> -c cloudsql-proxy`).
    *   Check Cloud SQL Proxy service account permissions (`roles/cloudsql.client`).
    *   Ensure Kubernetes Secrets for proxy credentials and DB passwords are correct.
    *   Confirm `DB_HOST` in app is `127.0.0.1` and `DB_PORT` is `5432`.
    *   Check `DB_NAME` and `DB_USER` environment variables are correct for the specific Cloud SQL database.
*   **`pg_config executable not found` during Docker build:**
    *   Ensure you are using `psycopg2-binary` in `requirements.txt` to avoid compilation.
    *   If you must use `psycopg2`, add `RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev gcc` to your Dockerfile before `pip install`.
