# ClientFlow AI

A small full-stack client operations app built to make the browser-to-database request cycle visible and explainable. It helps a signed-in user track clients, projects, tasks, and support tickets, with optional LLM suggestions for a ticket.

## Features

- Register, sign in and sign out with hashed passwords and Flask sessions
- User-scoped client, project, task and ticket management
- Dashboard counts and task completion calculated from PostgreSQL
- Client search and JSON endpoints for basic integrations
- Optional support ticket summary, category, priority and next-action suggestions

## Technology and architecture

Python 3, Flask, PostgreSQL, Psycopg 3, Jinja, HTML, CSS and vanilla JavaScript. `app.py` contains page/API routes and business logic. `database.py` opens PostgreSQL connections and creates the five-table schema. Jinja renders pages on the server; JavaScript calls the ticket-analysis endpoint. This is one Flask application, with no separate API server.

## Database overview

`users` owns `clients`; each client can have many `projects` and `support_tickets`; each project can have many `tasks`. Foreign keys cascade deletion down the relationship. Every record query is scoped to the signed-in user. See `database.py` for the complete schema and constraints.

## Setup

1. Install Python 3.10 or later and PostgreSQL. Create a PostgreSQL database named `clientflow` (or use a database URL to another database).
2. Create and activate a virtual environment: `python -m venv .venv`. On Windows use `.venv\Scripts\Activate.ps1`; on macOS/Linux use `source .venv/bin/activate`.
3. Install dependencies: `pip install -r requirements.txt`.
4. Copy `.env.example` to `.env`, then set `DATABASE_URL` and a long random `SECRET_KEY`. `OPENAI_API_KEY` is optional unless you want ticket analysis.
5. Run `python app.py`. On startup, the app creates missing tables. Open `http://127.0.0.1:5000` and register an account.

The application needs a reachable PostgreSQL server. The optional AI feature uses the OpenAI API and requires a valid key, network access and a model available to that key. No credentials are included in this repository. Keep `.env` private.

## Environment variables

| Name | Purpose |
|---|---|
| `DATABASE_URL` | Psycopg PostgreSQL connection URL |
| `SECRET_KEY` | Signs Flask session cookies; set a private random value |
| `OPENAI_API_KEY` | Enables optional ticket analysis |
| `OPENAI_MODEL` | Model name; defaults to `gpt-4o-mini` |
| `FLASK_DEBUG` | Set to `true` only for local development |

## API examples

All `/api` routes require a logged-in session cookie. From a browser session, list clients with `GET /api/clients`. Create a client with JSON:

```http
POST /api/clients
Content-Type: application/json

{"name":"Northwind Studio","email":"hello@example.com","company":"Northwind"}
```

`PUT /api/clients/<id>` updates a client, and `DELETE /api/clients/<id>` deletes it and its dependent records. `GET /api/projects`, `/api/tasks` and `/api/tickets` return the current user's records. `GET /health` checks database connectivity.

## AI ticket analysis

On the Tickets page, enter a subject and description and click **Analyze with AI**. The browser posts these fields to `POST /tickets/analyze`. Flask sends them to the configured OpenAI chat completion endpoint and requests JSON containing a summary, category, priority and next action. The result is displayed and suggested category/priority are filled into the form; the user chooses whether to save the ticket. The AI response is a suggestion and should be reviewed.

## Run and verify

Run `python app.py` after setting up PostgreSQL and the environment. The `/health` endpoint reports whether the database is reachable. This repository's code should be smoke-checked in an environment with PostgreSQL; no successful runtime result is claimed here unless that check has been performed.

## Future improvements

- Add CSRF protection, stronger production cookie settings and rate limiting
- Add automated tests and a migration tool as the schema evolves
- Add pagination and richer filtering for larger datasets
- Expand JSON create/update/delete APIs for each resource
- Add ticket history and user roles if the learning scope calls for them

See [LEARNING_GUIDE.md](LEARNING_GUIDE.md) for an explanation of the full-stack flow.
