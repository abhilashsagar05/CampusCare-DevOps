# CampusCare — Smart Campus Issue Reporting & Technician Assignment

A beginner-friendly DevOps project: students submit campus maintenance issues, an administrator assigns each issue to a technician, and technicians update the status of their own assigned work. Docker Compose runs the app, PostgreSQL, Prometheus and Grafana.

## What changed in the assignment workflow

1. A student submits a report on the public page (`http://localhost:5000`).
2. Staff opens **Staff sign in** and logs in as the administrator.
3. The administrator opens `/admin`, selects a technician for a report and saves the assignment.
4. The report appears in that technician's dashboard at `/technician` after they sign in.
5. That technician can move their own assigned report to **In Progress** or **Resolved**. The app prevents a technician from updating a report assigned to another technician.
6. The public page shows the current status and the assigned technician's display name.

This is an in-app assignment workflow. It does not yet send email, SMS, WhatsApp, or push notifications; technicians see new assignments when they open or refresh their dashboard.

## Start the project on Windows

Open PowerShell or Command Prompt in the project folder, then run:

```powershell
docker compose up --build -d
docker compose ps
```

Open these pages:

- CampusCare public issue page: `http://localhost:5000`
- Staff sign-in: `http://localhost:5000/login`
- Prometheus: `http://localhost:9090` (try the query `up`)
- Grafana: `http://localhost:3000`

## Local demo staff accounts

| Role | Username | Demo password |
|---|---|---|
| Administrator | `admin` | `AdminDemo123!` |
| Technician | `tech1` | `TechDemo123!` |
| Technician | `tech2` | `TechDemo456!` |

These are demonstration credentials only. Before sharing the project or deploying it, set strong unique passwords and a strong `SECRET_KEY` in a local `.env` file. `.env.example` shows the variables. The application seeds accounts only if the username does not already exist; changing an environment password later does not reset an existing account's stored password.

## Existing database and reports

The app includes a small startup migration that adds the nullable `assigned_technician_id` field to an existing `issues` table if needed. It does not delete existing reports. **Do not run `docker compose down -v`** unless you intentionally want to delete the named database and monitoring volumes.

To see app logs:

```powershell
docker compose logs --tail=50 app
```

To see the issue table:

```powershell
docker compose exec db psql -U campuscare -d campuscare -c "SELECT id, title, status, assigned_technician_id FROM issues ORDER BY id DESC;"
```

## Tests

Install the packages in `requirements.txt` in a Python virtual environment, then run:

```powershell
python -m pytest -q
```

## Monitoring endpoints

- `/health` — confirms the app can query its database.
- `/ready` — readiness check.
- `/metrics` — Prometheus metrics.
- `/api/issues` — JSON list of reports, including assigned technician display name.

## DevOps components

- **Docker** packages the Flask application into an image.
- **Docker Compose** runs the application and supporting services together.
- **PostgreSQL** stores reports and staff accounts.
- **Prometheus** scrapes application metrics.
- **Grafana** connects to Prometheus for dashboards.
- **Jenkinsfile** provides a sample CI pipeline.
- **SonarQube project properties** are included as a starting point for static analysis.

## Important security note

This is an educational prototype, not production-ready software. It has password-hashed demo staff accounts and role checks, but still needs a CSRF protection layer, account administration/password-reset flows, login rate limiting, audit history, secure deployment secrets, HTTPS, and a reviewed database migration strategy before public deployment. Do not expose the demo instance to the internet.
