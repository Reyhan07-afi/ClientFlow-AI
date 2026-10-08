# ClientFlow AI: Full-Stack Learning Guide

## 1. What Flask does

Flask is a Python web framework. It receives HTTP requests, matches each request to a route, calls Python code, and turns the returned value into an HTTP response. Flask also connects templates and session support to that request cycle.

## 2. What `app.py` does

`app.py` creates the Flask application, reads environment settings, defines routes, checks login state, validates form data, runs business logic and SQL queries, and returns HTML, redirects or JSON. Keeping these pieces together makes the first version easy to follow.

## 3. What `database.py` does

`database.py` creates Psycopg connections from `DATABASE_URL` and defines the SQL schema initialization. A connection context commits a successful transaction and rolls it back if an exception escapes. The database, not Python memory, stores the application records.

## 4. How a browser request reaches Flask

The browser sends an HTTP method and URL, such as `GET /clients`. Flask's router selects the matching view function. That function may read query parameters, form data, JSON, and the session cookie. It does work and returns a response. For a rendered page, the browser receives HTML and asks for the linked CSS and JavaScript files too.

## 5. How Flask talks to PostgreSQL

The route calls `get_db()`, which reads the database URL and opens a Psycopg connection. It executes SQL using `%s` placeholders and a separate values tuple. PostgreSQL parses and runs the statement. A parameterized query keeps user input as data rather than SQL syntax. The result rows return to Python.

## 6. How PostgreSQL data reaches a page

Python passes query results to `render_template()`. Jinja fills placeholders and loops in a template such as `clients.html`. Flask returns the completed HTML. Jinja escapes ordinary values by default, and the browser parses and displays that response.

## 7. How forms work

A form declares an HTTP method and action URL. When submitted, the browser sends its named fields as form data. Flask reads them through `request.form`, trims and validates values, then writes to PostgreSQL. The route uses the Post/Redirect/Get pattern: after saving, it redirects to a GET page so refreshing does not submit the same form again.

## 8. How JavaScript interacts with APIs

`static/js/app.js` listens for the AI button click, uses `fetch()` to POST the ticket fields, awaits the JSON response, then updates the page. This gives a small interactive action without reloading the whole page. JavaScript also asks for confirmation before delete forms submit.

## 9. What REST APIs are

REST-style APIs expose resources over HTTP. The method communicates the operation: GET reads, POST creates, PUT replaces/updates, DELETE removes. This project returns JSON from `/api/...` routes, while its normal page routes return HTML. HTTP status codes such as 201, 400, 404 and 503 describe the result.

## 10. Authentication flow

Registration validates name, email and password length, hashes the password, then stores the hash and user. Login looks up the email and compares the submitted password with the stored hash. On success the user ID is saved in the signed session cookie. Logout clears the session.

## 11. Session handling

Flask sessions are stored in a browser cookie signed with `SECRET_KEY`; the browser sends it back on later requests. The cookie signature prevents undetected edits, but is not encryption. This project stores the user ID and display name in the session. Never put secrets or sensitive records in it.

## 12. Password hashing

Werkzeug's `generate_password_hash()` derives a one-way password hash with a salt. `check_password_hash()` verifies a password without storing or comparing plaintext. If a database leaks, the original passwords are not directly present in the user rows.

## 13. Database relationships

Each client row has a `user_id` foreign key. Projects point to both their owning user and client. Tasks point to their user and project. Tickets point to their user and client. These foreign keys prevent dangling relationships, and `ON DELETE CASCADE` removes dependent projects/tasks/tickets when a client or project is deleted. Routes additionally filter by the signed-in user so IDs from another account do not expose records.

## 14. CRUD operations

CRUD means Create, Read, Update and Delete. Create routes use `INSERT`; read pages use `SELECT`; edit routes use `UPDATE`; delete routes use `DELETE`. Each statement is parameterized. The user ID is included in reads and writes to scope records to the current account.

## 15. How the AI feature works

The ticket page sends subject and description to `POST /tickets/analyze`. Flask checks required values and that `OPENAI_API_KEY` exists, then requests a short JSON analysis from the configured model. Flask returns that JSON; JavaScript shows the summary and uses the suggested category and priority as editable form values. The AI does not save the ticket or take actions on its own.

## 16. One complete feature flow: creating a task

1. The user selects a project and fills the task form in `tasks.html`.
2. The browser submits a POST request to `/tasks` with the session cookie and named fields.
3. Flask's `tasks_page()` is protected by `login_required`; it reads the user ID from the session and form fields from `request.form`.
4. The route executes a parameterized `INSERT ... SELECT`. The SELECT only finds a project owned by that user, so another user's project ID cannot be used.
5. Psycopg commits the transaction when the connection context exits successfully.
6. Flask redirects to `/tasks`; the browser makes a GET request.
7. Flask selects that user's tasks and projects, passes rows to `tasks.html`, and returns rendered HTML.
8. The browser displays the new task. If something goes wrong, the server logs or returns an error; production code should add user-friendly transaction error handling and automated coverage.

## Practice before an interview

Be ready to trace a request from the browser through a route and SQL query back to a template. Explain why SQL placeholders matter, how the session identifies a user, what each foreign key means, and what changes between a normal HTML route and a JSON API. Practice adding one field end to end: schema, form, validation, SQL, display, and API response.
