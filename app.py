import os
from datetime import date
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database import get_db, init_db

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def current_user_id():
    return session["user_id"]


@app.get("/")
def index():
    return redirect(url_for("dashboard" if session.get("user_id") else "login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or "@" not in email or len(password) < 8:
            flash("Enter a name, valid email, and password of at least 8 characters.", "error")
        else:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute("INSERT INTO users (name,email,password_hash) VALUES (%s,%s,%s) ON CONFLICT (email) DO NOTHING RETURNING id", (name,email,generate_password_hash(password)))
                    row = cur.fetchone()
                if row:
                    session["user_id"] = row[0]
                    session["user_name"] = name
                    return redirect(url_for("dashboard"))
            flash("That email is already registered.", "error")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id,name,password_hash FROM users WHERE email=%s", (email,))
                user = cur.fetchone()
        if user and check_password_hash(user[2], password):
            session.clear()
            session["user_id"], session["user_name"] = user[0], user[1]
            return redirect(url_for("dashboard"))
        flash("Email or password is incorrect.", "error")
    return render_template("login.html")


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.get("/dashboard")
@login_required
def dashboard():
    uid = current_user_id()
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM clients WHERE user_id=%s", (uid,)); clients = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM projects WHERE user_id=%s AND status='Active'", (uid,)); projects = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM tasks WHERE user_id=%s AND status <> 'Done'", (uid,)); tasks = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM support_tickets WHERE user_id=%s AND status <> 'Closed'", (uid,)); tickets = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FILTER (WHERE status='Done'), COUNT(*) FROM tasks WHERE user_id=%s", (uid,)); done, all_tasks = cur.fetchone()
            cur.execute("SELECT t.id,t.subject,t.priority,t.status,c.name AS client_name FROM support_tickets t JOIN clients c ON c.id=t.client_id WHERE t.user_id=%s ORDER BY t.created_at DESC LIMIT 5", (uid,)); recent = cur.fetchall()
    return render_template("dashboard.html", stats={"clients":clients,"projects":projects,"tasks":tasks,"tickets":tickets,"done":done,"all_tasks":all_tasks}, recent=recent)


def rows(sql, params):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()


def form_value(key):
    return request.form.get(key, "").strip() or None


def render_entity(table, template, select_sql, extra=None):
    return render_template(template, items=rows(select_sql, (current_user_id(),)), extra=extra)


@app.route("/clients", methods=["GET", "POST"])
@login_required
def clients_page():
    uid = current_user_id()
    if request.method == "POST":
        name = form_value("name")
        if name:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute("INSERT INTO clients (user_id,name,email,company,phone,notes) VALUES (%s,%s,%s,%s,%s,%s)", (uid,name,form_value("email"),form_value("company"),form_value("phone"),form_value("notes")))
            flash("Client added.", "success")
        else: flash("Client name is required.", "error")
        return redirect(url_for("clients_page"))
    query = request.args.get("q", "").strip()
    items = rows("SELECT * FROM clients WHERE user_id=%s AND (name ILIKE %s OR COALESCE(company,'') ILIKE %s OR COALESCE(email,'') ILIKE %s) ORDER BY name", (uid,f"%{query}%",f"%{query}%",f"%{query}%"))
    return render_template("clients.html", items=items, query=query)


@app.post("/clients/<int:item_id>/edit")
@login_required
def edit_client(item_id):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE clients SET name=%s,email=%s,company=%s,phone=%s,notes=%s WHERE id=%s AND user_id=%s", (form_value("name"),form_value("email"),form_value("company"),form_value("phone"),form_value("notes"),item_id,current_user_id()))
    flash("Client updated.", "success")
    return redirect(url_for("clients_page"))


@app.post("/clients/<int:item_id>/delete")
@login_required
def delete_client(item_id):
    with get_db() as conn:
        with conn.cursor() as cur: cur.execute("DELETE FROM clients WHERE id=%s AND user_id=%s", (item_id,current_user_id()))
    flash("Client deleted with its projects and tickets.", "success")
    return redirect(url_for("clients_page"))


@app.route("/projects", methods=["GET", "POST"])
@login_required
def projects_page():
    uid=current_user_id()
    if request.method == "POST":
        try:
            with get_db() as conn:
                with conn.cursor() as cur: cur.execute("INSERT INTO projects (user_id,client_id,name,description,status,deadline) SELECT %s,id,%s,%s,%s,%s FROM clients WHERE id=%s AND user_id=%s", (uid,form_value("name"),form_value("description"),form_value("status") or "Planning",form_value("deadline"),request.form.get("client_id"),uid))
            flash("Project added.", "success")
        except Exception: flash("Could not add project. Check the fields and client.", "error")
        return redirect(url_for("projects_page"))
    items=rows("SELECT p.*,c.name client_name FROM projects p JOIN clients c ON c.id=p.client_id WHERE p.user_id=%s ORDER BY p.created_at DESC",(uid,))
    clients=rows("SELECT id,name FROM clients WHERE user_id=%s ORDER BY name",(uid,))
    return render_template("projects.html",items=items,clients=clients)


@app.post("/projects/<int:item_id>/edit")
@login_required
def edit_project(item_id):
    with get_db() as conn:
        with conn.cursor() as cur: cur.execute("UPDATE projects SET name=%s,description=%s,status=%s,deadline=%s WHERE id=%s AND user_id=%s", (form_value("name"),form_value("description"),form_value("status"),form_value("deadline"),item_id,current_user_id()))
    flash("Project updated.", "success"); return redirect(url_for("projects_page"))


@app.post("/projects/<int:item_id>/delete")
@login_required
def delete_project(item_id):
    with get_db() as conn:
        with conn.cursor() as cur: cur.execute("DELETE FROM projects WHERE id=%s AND user_id=%s", (item_id,current_user_id()))
    flash("Project and its tasks deleted.", "success"); return redirect(url_for("projects_page"))


@app.route("/tasks", methods=["GET", "POST"])
@login_required
def tasks_page():
    uid=current_user_id()
    if request.method == "POST":
        with get_db() as conn:
            with conn.cursor() as cur: cur.execute("INSERT INTO tasks (user_id,project_id,title,description,priority,status,deadline) SELECT %s,id,%s,%s,%s,%s,%s FROM projects WHERE id=%s AND user_id=%s", (uid,form_value("title"),form_value("description"),form_value("priority") or "Medium",form_value("status") or "To do",form_value("deadline"),request.form.get("project_id"),uid))
        flash("Task added.", "success"); return redirect(url_for("tasks_page"))
    items=rows("SELECT t.*,p.name project_name,c.name client_name FROM tasks t JOIN projects p ON p.id=t.project_id JOIN clients c ON c.id=p.client_id WHERE t.user_id=%s ORDER BY t.deadline NULLS LAST,t.created_at DESC",(uid,))
    projects=rows("SELECT id,name FROM projects WHERE user_id=%s ORDER BY name",(uid,))
    return render_template("tasks.html",items=items,projects=projects)


@app.post("/tasks/<int:item_id>/edit")
@login_required
def edit_task(item_id):
    with get_db() as conn:
        with conn.cursor() as cur: cur.execute("UPDATE tasks SET title=%s,description=%s,priority=%s,status=%s,deadline=%s WHERE id=%s AND user_id=%s", (form_value("title"),form_value("description"),form_value("priority"),form_value("status"),form_value("deadline"),item_id,current_user_id()))
    flash("Task updated.", "success"); return redirect(url_for("tasks_page"))


@app.post("/tasks/<int:item_id>/delete")
@login_required
def delete_task(item_id):
    with get_db() as conn:
        with conn.cursor() as cur: cur.execute("DELETE FROM tasks WHERE id=%s AND user_id=%s", (item_id,current_user_id()))
    flash("Task deleted.", "success"); return redirect(url_for("tasks_page"))


@app.route("/tickets", methods=["GET", "POST"])
@login_required
def tickets_page():
    uid=current_user_id()
    if request.method == "POST":
        with get_db() as conn:
            with conn.cursor() as cur: cur.execute("INSERT INTO support_tickets (user_id,client_id,subject,description,category,priority,status) SELECT %s,id,%s,%s,%s,%s,%s FROM clients WHERE id=%s AND user_id=%s", (uid,form_value("subject"),form_value("description"),form_value("category") or "General",form_value("priority") or "Medium",form_value("status") or "Open",request.form.get("client_id"),uid))
        flash("Support ticket created.", "success"); return redirect(url_for("tickets_page"))
    items=rows("SELECT t.*,c.name client_name FROM support_tickets t JOIN clients c ON c.id=t.client_id WHERE t.user_id=%s ORDER BY t.created_at DESC",(uid,))
    clients=rows("SELECT id,name FROM clients WHERE user_id=%s ORDER BY name",(uid,))
    return render_template("tickets.html",items=items,clients=clients)


@app.post("/tickets/<int:item_id>/edit")
@login_required
def edit_ticket(item_id):
    with get_db() as conn:
        with conn.cursor() as cur: cur.execute("UPDATE support_tickets SET subject=%s,description=%s,category=%s,priority=%s,status=%s WHERE id=%s AND user_id=%s", (form_value("subject"),form_value("description"),form_value("category"),form_value("priority"),form_value("status"),item_id,current_user_id()))
    flash("Ticket updated.", "success"); return redirect(url_for("tickets_page"))


@app.post("/tickets/<int:item_id>/delete")
@login_required
def delete_ticket(item_id):
    with get_db() as conn:
        with conn.cursor() as cur: cur.execute("DELETE FROM support_tickets WHERE id=%s AND user_id=%s", (item_id,current_user_id()))
    flash("Ticket deleted.", "success"); return redirect(url_for("tickets_page"))


@app.post("/tickets/analyze")
@login_required
def analyze_ticket():
    subject=request.form.get("subject","").strip(); description=request.form.get("description","").strip()
    if not subject or not description: return jsonify({"error":"Subject and description are required."}),400
    api_key=os.getenv("OPENAI_API_KEY")
    if not api_key: return jsonify({"error":"AI analysis is unavailable. Set OPENAI_API_KEY in .env."}),503
    try:
        from openai import OpenAI
        client=OpenAI(api_key=api_key)
        response=client.chat.completions.create(model=os.getenv("OPENAI_MODEL","gpt-4o-mini"),temperature=0.2,response_format={"type":"json_object"},messages=[{"role":"system","content":"Analyze a customer support issue. Return JSON with summary, category, priority, next_action. Keep each concise; category and priority should be plain labels."},{"role":"user","content":f"Subject: {subject}\nDescription: {description}"}])
        import json
        return jsonify(json.loads(response.choices[0].message.content))
    except Exception:
        app.logger.exception("Ticket analysis failed")
        return jsonify({"error":"The AI service could not analyze this ticket. Check your API key and connection."}),502


@app.get("/api/clients")
@login_required
def api_clients():
    return jsonify([dict(id=r[0],name=r[1],email=r[2],company=r[3],phone=r[4],notes=r[5]) for r in rows("SELECT id,name,email,company,phone,notes FROM clients WHERE user_id=%s ORDER BY name",(current_user_id(),))])


@app.post("/api/clients")
@login_required
def api_create_client():
    data=request.get_json(silent=True) or {}; name=str(data.get("name","")).strip()
    if not name: return jsonify({"error":"name is required"}),400
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO clients (user_id,name,email,company,phone,notes) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",(current_user_id(),name,data.get("email"),data.get("company"),data.get("phone"),data.get("notes"))); item_id=cur.fetchone()[0]
    return jsonify({"id":item_id,"name":name}),201


@app.route("/api/clients/<int:item_id>", methods=["PUT","DELETE"])
@login_required
def api_client_detail(item_id):
    if request.method=="DELETE":
        with get_db() as conn:
            with conn.cursor() as cur: cur.execute("DELETE FROM clients WHERE id=%s AND user_id=%s RETURNING id",(item_id,current_user_id())); deleted=cur.fetchone()
        return ("",204) if deleted else (jsonify({"error":"Client not found"}),404)
    data=request.get_json(silent=True) or {}; name=str(data.get("name","")).strip()
    if not name: return jsonify({"error":"name is required"}),400
    with get_db() as conn:
        with conn.cursor() as cur: cur.execute("UPDATE clients SET name=%s,email=%s,company=%s,phone=%s,notes=%s WHERE id=%s AND user_id=%s RETURNING id",(name,data.get("email"),data.get("company"),data.get("phone"),data.get("notes"),item_id,current_user_id())); updated=cur.fetchone()
    return (jsonify({"id":item_id,"name":name}) if updated else (jsonify({"error":"Client not found"}),404))


@app.get("/api/projects")
@login_required
def api_projects():
    data=rows("SELECT id,client_id,name,description,status,deadline FROM projects WHERE user_id=%s ORDER BY created_at DESC",(current_user_id(),))
    return jsonify([dict(zip(("id","client_id","name","description","status","deadline"),[str(v) if isinstance(v,date) else v for v in row])) for row in data])


@app.get("/api/tasks")
@login_required
def api_tasks():
    data=rows("SELECT id,project_id,title,description,priority,status,deadline FROM tasks WHERE user_id=%s ORDER BY created_at DESC",(current_user_id(),))
    return jsonify([dict(zip(("id","project_id","title","description","priority","status","deadline"),[str(v) if isinstance(v,date) else v for v in row])) for row in data])


@app.get("/api/tickets")
@login_required
def api_tickets():
    data=rows("SELECT id,client_id,subject,description,category,priority,status FROM support_tickets WHERE user_id=%s ORDER BY created_at DESC",(current_user_id(),))
    return jsonify([dict(zip(("id","client_id","subject","description","category","priority","status"),row)) for row in data])


@app.get("/health")
def health():
    try:
        with get_db() as conn:
            with conn.cursor() as cur: cur.execute("SELECT 1")
        return jsonify({"status":"ok","database":"connected"})
    except Exception:
        return jsonify({"status":"error","database":"unavailable"}),503


if __name__ == "__main__":
    with app.app_context(): init_db()
    app.run(debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
