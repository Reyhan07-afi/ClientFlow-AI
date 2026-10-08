import os

import psycopg
from psycopg.rows import tuple_row


def get_db():
    """Open one PostgreSQL connection; its context manager commits or rolls back."""
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set. Copy .env.example to .env and configure PostgreSQL.")
    return psycopg.connect(url, row_factory=tuple_row)


def init_db():
    """Create the small application schema when starting the local app."""
    schema = """
    CREATE TABLE IF NOT EXISTS users (
      id SERIAL PRIMARY KEY, name VARCHAR(120) NOT NULL,
      email VARCHAR(255) NOT NULL UNIQUE, password_hash TEXT NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE TABLE IF NOT EXISTS clients (
      id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      name VARCHAR(160) NOT NULL, email VARCHAR(255), company VARCHAR(160), phone VARCHAR(60), notes TEXT,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE TABLE IF NOT EXISTS projects (
      id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
      name VARCHAR(180) NOT NULL, description TEXT, status VARCHAR(30) NOT NULL DEFAULT 'Planning'
        CHECK(status IN ('Planning','Active','On hold','Completed')),
      deadline DATE, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE TABLE IF NOT EXISTS tasks (
      id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
      title VARCHAR(180) NOT NULL, description TEXT,
      priority VARCHAR(20) NOT NULL DEFAULT 'Medium' CHECK(priority IN ('Low','Medium','High')),
      status VARCHAR(20) NOT NULL DEFAULT 'To do' CHECK(status IN ('To do','In progress','Done')),
      deadline DATE, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE TABLE IF NOT EXISTS support_tickets (
      id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
      subject VARCHAR(180) NOT NULL, description TEXT NOT NULL, category VARCHAR(80) NOT NULL DEFAULT 'General',
      priority VARCHAR(20) NOT NULL DEFAULT 'Medium' CHECK(priority IN ('Low','Medium','High','Urgent')),
      status VARCHAR(20) NOT NULL DEFAULT 'Open' CHECK(status IN ('Open','In progress','Closed')),
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS clients_user_idx ON clients(user_id);
    CREATE INDEX IF NOT EXISTS projects_user_idx ON projects(user_id);
    CREATE INDEX IF NOT EXISTS tasks_user_idx ON tasks(user_id);
    CREATE INDEX IF NOT EXISTS tickets_user_idx ON support_tickets(user_id);
    """
    with get_db() as conn:
        conn.execute(schema)
