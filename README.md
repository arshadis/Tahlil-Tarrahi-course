# Daily Learning Game - Dockerized Sprint 1 Starter

This starter begins SCRUM-1: login foundation.

## What is included

- PostgreSQL database container
- FastAPI backend container
- Nginx frontend container
- Auto database table creation on backend startup
- Development admin user creation on first run
- Login page with username/password only
- Temporary database login for MVP
- Isolated placeholder for future LDAP / Active Directory authentication

## Run with Docker

From the project root:

```bash
docker compose up --build
```

Open:

```text
http://localhost:5173
```

Backend API:

```text
http://localhost:8000
```

API docs:

```text
http://localhost:8000/docs
```

## Test user

```text
username: admin
password: admin123
```

## Stop

```bash
docker compose down
```

## Reset database completely

```bash
docker compose down -v
docker compose up --build
```

## Jira status suggestion

For SCRUM-1:

- Dockerize development environment: Done
- Create database schema: Done
- Create login API: In Progress
- Create login page: In Progress
- Database login for MVP: In Progress
- LDAP / Active Directory adapter: To Do
- Login tests: To Do
