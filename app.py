from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os
from werkzeug.utils import secure_filename
from datetime import datetime


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret") 


DATABASE = os.path.join(os.getcwd(), "database.db")

from init_db import init_db

if not os.path.exists(DATABASE):
    init_db()

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  
    return conn


@app.route("/")
def index():
    if "user" in session:
        return redirect(url_for("dashboard"))
    return render_template("switch-panel.html")


@app.route("/home")
def home():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("/user/home.html", username=session["user"])


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user"] = user["username"]
            session["department"] = user["department"]
            return redirect(url_for("home"))
        else:
            flash("Invalid username or password", "error")

    return render_template("/user/login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if "admin" not in session:
        return redirect(url_for("admin_login"))
       
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        department = request.form["department"]
        password = request.form["password"]
        confirm = request.form["confirm_password"]

        if not department:
            flash("Please select a department!", "error")
            return render_template("admin/register.html")

        if password != confirm:
            flash("Passwords do not match!", "error")
            return render_template("admin/register.html")

        hashed_password = generate_password_hash(password)

        try:
            conn = get_db()
            conn.execute(
                "INSERT INTO users (username, email, department, password) VALUES (?, ? , ?, ?)",
                (username, email, department, hashed_password)
            )
            conn.commit()
            conn.close()

            flash("Registration successful! Please login.", "success")
            return redirect(url_for("register"))

        except sqlite3.IntegrityError:
            flash("Username or Email already exists!", "error")

    return render_template("admin/register.html")


@app.route("/voter_registered")
def voter_registered():
    if "admin" not in session:
        return redirect(url_for("admin_login"))
    
    conn = get_db()

    users = conn.execute(
        "SELECT * FROM users"
    ).fetchall()

    conn.close()

    return render_template("admin/voter_registered.html" , users=users)



@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    candidates = conn.execute(
        "SELECT * FROM candidates WHERE department = ?",
        (session["department"],)
    ).fetchall()

    voted_candidate = conn.execute("""
        SELECT c.name, c.image
        FROM user_votes uv
        JOIN candidates c ON uv.candidate_id = c.id
        JOIN users u ON uv.user_id = u.id
        WHERE u.username = ?
    """, (session["user"],)).fetchone()

    result_row = conn.execute(
        "SELECT result_datetime FROM settings WHERE id = 1"
    ).fetchone()

    show_result = False
    winners = []  

    if result_row and result_row["result_datetime"]:
        result_time = datetime.fromisoformat(result_row["result_datetime"])

        if datetime.now() >= result_time:
            show_result = True
            
            highest_votes_row = conn.execute("""
                SELECT MAX(votes) as max_votes
                FROM candidates
                WHERE department = ?
            """, (session["department"],)).fetchone()

            if highest_votes_row and highest_votes_row["max_votes"] is not None:
                max_votes = highest_votes_row["max_votes"]
                
                winners = conn.execute("""
                    SELECT name, image, votes
                    FROM candidates
                    WHERE department = ? AND votes = ?
                """, (session["department"], max_votes)).fetchall()

    conn.close()

    
    department = session.get("department")
    if department == "BSCS":
        template = "/user/bscs_dashboard.html"
    elif department == "BSIT":
        template = "/user/bsit_dashboard.html"
    else:
        flash("Department not found!", "error")
        return redirect(url_for("login"))

    return render_template(
        template,
        candidates=candidates,
        voted_candidate=voted_candidate,
        show_result=show_result,
        winners=winners 
    )


@app.route("/set-result-time", methods=["POST"])
def set_result_time():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    result_datetime = request.form["result_datetime"]

    conn = get_db()
    conn.execute(
        "UPDATE settings SET result_datetime = ? WHERE id = 1",
        (result_datetime,)
    )
    conn.commit()
    conn.close()

    flash("Result announcement time set successfully!", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/logout")
def logout():
    session.pop("user", None)
    return render_template("switch-panel.html")


@app.route("/admin-logout")
def admin_logout():
    session.pop("admin", None)
    return render_template("switch-panel.html")


@app.route("/admin-home")
def admin_home():
    if "admin" not in session:
        return redirect(url_for("admin_login"))
    return render_template("/admin/admin_home.html", username=session["admin"])


@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        admin = conn.execute(
            "SELECT * FROM admin WHERE username = ?", (username,)
        ).fetchone()
        conn.close()

        if admin and check_password_hash(admin["password"], password):
            session["admin"] = admin["username"]
            return redirect(url_for("admin_home"))
        else:
            flash("Invalid admin username or password", "error")

    return render_template("/admin/admin_login.html")


@app.route("/admin-dashboard")
def admin_dashboard():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = get_db()
    candidates = conn.execute("SELECT * FROM candidates").fetchall()
    result_time = conn.execute(
        "SELECT result_datetime FROM settings WHERE id = 1"
    ).fetchone()
    conn.close()

    return render_template(
        "/admin/admin_dashboard.html",
        username=session["admin"],
        candidates=candidates,
        result_time=result_time["result_datetime"] if result_time else None
    )



@app.route("/create-candidate", methods=["GET", "POST"])
def create_candidate():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = get_db()

    if request.method == "POST":
        name = request.form["name"]
        description = request.form["description"]
        department = request.form["department"]
        image = request.files["image"]

        if not name or not description or not image:
            flash("All fields are required!", "error")
            return redirect(url_for("create_candidate"))

        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
           
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(filepath)

            
            conn.execute(
                "INSERT INTO candidates (name, description, department, image) VALUES (?, ?, ?, ?)",
                (name, description, department, filename)
            )
            conn.commit()
            flash("Candidate created successfully!", "success")
        else:
            flash("Invalid image file!", "error")

        return redirect(url_for("admin_dashboard"))

    return render_template("admin/create_candidate.html")


@app.route("/vote", methods=["POST"])
def vote():
    if "user" not in session:
        return redirect(url_for("login"))

    candidate_id = request.form.get("candidate_id")

    conn = get_db()

    
    user = conn.execute(
        "SELECT id FROM users WHERE username = ?",
        (session["user"],)
    ).fetchone()

    if not user:
        conn.close()
        flash("User not found!", "error")
        return redirect(url_for("dashboard"))

    user_id = user["id"]

    
    voted = conn.execute(
        "SELECT * FROM user_votes WHERE user_id = ?",
        (user_id,)
    ).fetchone()

    if voted:
        conn.close()
        flash("You have already voted!", "error")
        return redirect(url_for("dashboard"))

    
    conn.execute(
        "UPDATE candidates SET votes = votes + 1 WHERE id = ?",
        (candidate_id,)
    )

    
    conn.execute(
        "INSERT INTO user_votes (user_id, candidate_id) VALUES (?, ?)",
        (user_id, candidate_id)
    )

    conn.commit()
    conn.close()

    flash("Vote submitted successfully!", "success")
    return redirect(url_for("dashboard"))





@app.route("/edit-candidate/<int:candidate_id>", methods=["GET", "POST"])
def edit_candidate(candidate_id):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = get_db()
    candidate = conn.execute(
        "SELECT * FROM candidates WHERE id = ?",
        (candidate_id,)
    ).fetchone()

    if not candidate:
        conn.close()
        flash("Candidate not found!", "error")
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        name = request.form["name"]
        description = request.form["description"]
        image = request.files.get("image")

        if image and image.filename != "":
            
            if allowed_file(image.filename):
                filename = secure_filename(image.filename)
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image.save(filepath)

               
                conn.execute(
                    "UPDATE candidates SET name = ?, description = ?, image = ? WHERE id = ?",
                    (name, description, filename, candidate_id)
                )
            else:
                flash("Invalid image file!", "error")
                conn.close()
                return redirect(url_for("edit_candidate", candidate_id=candidate_id))
        else:
            
            conn.execute(
                "UPDATE candidates SET name = ?, description = ? WHERE id = ?",
                (name, description, candidate_id)
            )

        conn.commit()
        conn.close()
        flash("Candidate updated successfully!", "success")
        return redirect(url_for("admin_dashboard"))

    conn.close()
    return render_template("admin/edit_candidate.html", candidate=candidate)


@app.route("/delete-candidate/<int:candidate_id>")
def delete_candidate(candidate_id):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = get_db()

    
    conn.execute(
        "DELETE FROM user_votes WHERE candidate_id = ?",
        (candidate_id,)
    )

    
    conn.execute(
        "DELETE FROM candidates WHERE id = ?",
        (candidate_id,)
    )

    conn.commit()
    conn.close()

    flash("Candidate deleted successfully!", "success")
    return redirect(url_for("admin_dashboard"))


if __name__ == "__main__":
    app.run(debug=True)
