# 🛒 Grocery Ordering App — End-to-End DevOps Project

A simple web-based **Grocery Ordering App** built with Flask, wired into a complete DevOps pipeline for build, test, containerization, deployment, and monitoring.

## Pipeline Overview

```
Developer → Git Repository → Jenkins → Build & Test → Docker Image → Deployment (Ansible) → Monitoring (Prometheus + Grafana)
```

| Stage | Tool | What it does |
|---|---|---|
| Source control | Git / GitHub | Hosts the source code, triggers Jenkins via webhook |
| CI | Jenkins | Installs deps, lints, runs pytest, builds & pushes Docker image |
| Containerization | Docker | Packages the Flask app + dependencies into a portable image |
| Configuration management & deployment | Ansible | Installs Docker on the target VM, pulls the image, runs the container |
| Monitoring | Prometheus + Grafana | Scrapes `/metrics` from the app, visualizes request rate & latency |

## Application Features

- **Products** — add/remove grocery items with category, price, and stock
- **Customers** — register customer name, email, and delivery address
- **Cart** — session-based cart, add/remove items
- **Orders** — checkout decrements stock, tracks order status (Pending / Delivered / Cancelled)
- **`/health`** — liveness endpoint used by Docker healthchecks and Ansible
- **`/metrics`** — Prometheus-format metrics endpoint (via `prometheus-flask-exporter`)
- **`/api/products`** — simple JSON API

## Project Structure

```
grocery-devops-project/
├── app/                     # Flask application
│   ├── app.py               # Routes / app factory
│   ├── models.py            # SQLAlchemy models
│   ├── templates/           # Jinja2 + Bootstrap templates
│   └── static/
├── tests/
│   └── test_app.py          # pytest test suite (8 tests)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml       # app + Prometheus + Grafana
├── Jenkinsfile               # CI/CD pipeline definition
├── ansible/
│   ├── inventory.ini
│   └── playbook.yml         # provisions Docker + deploys container
├── monitoring/
│   └── prometheus.yml
└── grafana/
    └── provisioning/        # auto-configured datasource + dashboard
```

## 1. Run Locally (no Docker)

```bash
cd grocery-devops-project
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=app python3 app/app.py
# App: http://localhost:5000
```

## 2. Run Tests

```bash
PYTHONPATH=app pytest tests/ -v
```

## 3. Run with Docker Compose (App + Prometheus + Grafana)

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| App | http://localhost:5000 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 (login: `admin` / `admin`) |

Grafana auto-loads a Prometheus datasource and a "Grocery App - Request Overview" dashboard.

## 4. Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit: Grocery Ordering App with DevOps pipeline"
git branch -M main
git remote add origin https://github.com/<your-username>/grocery-devops-project.git
git push -u origin main
```

## 5. Set Up Jenkins

1. Install Jenkins plugins: **Docker Pipeline**, **Git**, **JUnit**, **Pipeline**.
2. Add a **Docker Hub credential** in Jenkins (Manage Jenkins → Credentials) with ID `dockerhub-credentials`.
3. Create a new **Pipeline** job → point it at your GitHub repo → Jenkins will auto-detect the `Jenkinsfile`.
4. (Optional) Add a GitHub webhook so pushes trigger the pipeline automatically.
5. Edit the `DOCKERHUB_REPO` variable in the `Jenkinsfile` to your own Docker Hub repo name.

The pipeline stages: **Checkout → Install Dependencies → Lint → Run Tests → Build Docker Image → Push Docker Image → Deploy with Ansible → Smoke Test**.

## 6. Deploy with Ansible (manually, or via Jenkins)

Edit `ansible/inventory.ini` with your target VM's IP/SSH details, then:

```bash
ansible-playbook -i ansible/inventory.ini ansible/playbook.yml \
  --extra-vars "image_repo=yourdockerhubusername/grocery-app image_tag=latest"
```

This installs Docker on the target host, pulls the image, and runs the container — this is the **configuration management + automated deployment** step.

## 7. Monitoring

- The app exposes Prometheus metrics at `/metrics` (request counts, latency histograms, status codes).
- `monitoring/prometheus.yml` scrapes the app every 15s.
- Grafana is pre-provisioned with a dashboard showing **requests/sec** and **p95 latency**.

## Notes for Submission

- Replace `yourdockerhubusername` in `Jenkinsfile` and `ansible/playbook.yml` with your actual Docker Hub username.
- Replace the placeholder IP in `ansible/inventory.ini` with your VM/cloud instance.
- Push this repository to GitHub (or Bitbucket) before submission, and include the repo link in your TAE-II submission email.
