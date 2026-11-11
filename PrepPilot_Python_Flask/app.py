import os, json, random
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix

load_dotenv()
app = Flask(__name__)
app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_proto=1,
    x_host=1
)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-this-development-secret")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///preppilot.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
oauth = OAuth(app)

if os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET"):
    oauth.register(
        name="google",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"}
    )

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    google_id = db.Column(db.String(150), unique=True)
    role = db.Column(db.String(20), default="student")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    question = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(255), nullable=False)
    option_b = db.Column(db.String(255), nullable=False)
    option_c = db.Column(db.String(255), nullable=False)
    option_d = db.Column(db.String(255), nullable=False)
    answer = db.Column(db.String(1), nullable=False)
    explanation = db.Column(db.Text, default="")

class Bookmark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("question.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    question = db.relationship("Question")
    __table_args__ = (db.UniqueConstraint("user_id", "question_id", name="unique_user_bookmark"),)

class StudyPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    subject = db.Column(db.String(60), nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class DailyGoal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True, nullable=False)
    target_tests = db.Column(db.Integer, default=2)

class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Integer, nullable=False)
    taken_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("User", backref="results")

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to continue.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def admin_required(fn):
    @wraps(fn)
    @login_required
    def wrapper(*args, **kwargs):
        user = db.session.get(User, session["user_id"])
        if not user or user.role != "admin":
            flash("Administrator access is required.", "danger")
            return redirect(url_for("dashboard"))
        return fn(*args, **kwargs)
    return wrapper

def current_user():
    return db.session.get(User, session["user_id"]) if "user_id" in session else None

@app.context_processor
def inject_user():
    return {"current_user": current_user()}

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 6:
            flash("Enter your name, a valid email, and a password of at least 6 characters.", "danger")
        elif User.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "warning")
        else:
            user = User(name=name, email=email, password_hash=generate_password_hash(password))
            db.session.add(user); db.session.commit()
            session["user_id"] = user.id
            flash("Your account is ready. Welcome to PrepPilot!", "success")
            return redirect(url_for("dashboard"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and user.password_hash and check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            flash("Signed in successfully.", "success")
            return redirect(url_for("dashboard"))
        flash("Incorrect email or password.", "danger")
    return render_template("login.html", google_enabled=bool(os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET")))

@app.route("/auth/google")
def google_login():
    if "google" not in oauth._clients:
        flash("Google sign-in is not configured yet. Add your Google OAuth credentials to .env.", "warning")
        return redirect(url_for("login"))
    redirect_uri = url_for("google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@app.route("/auth/google/callback")
def google_callback():
    token = oauth.google.authorize_access_token()
    info = token.get("userinfo")
    if not info:
        info = oauth.google.userinfo()
    email = info.get("email", "").lower()
    google_id = info.get("sub")
    if not email or not info.get("email_verified"):
        flash("Google did not provide a verified email address.", "danger")
        return redirect(url_for("login"))
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(name=info.get("name") or email.split("@")[0], email=email, google_id=google_id)
        db.session.add(user)
    else:
        user.google_id = google_id
    db.session.commit()
    session["user_id"] = user.id
    flash("Signed in with Google.", "success")
    return redirect(url_for("dashboard"))

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    recent = Result.query.filter_by(user_id=user.id).order_by(Result.taken_at.desc()).limit(5).all()
    total_tests = Result.query.filter_by(user_id=user.id).count()
    avg = db.session.query(db.func.avg(Result.score * 100.0 / Result.total)).filter_by(user_id=user.id).scalar()
    categories = ["Aptitude", "Reasoning", "Verbal", "Programming"]
    today = datetime.utcnow().date()
    today_tests = Result.query.filter(Result.user_id == user.id, db.func.date(Result.taken_at) == today).count()
    goal = DailyGoal.query.filter_by(user_id=user.id).first()
    goal_target = goal.target_tests if goal else 2
    category_stats = []
    for category in categories:
        attempts = Result.query.filter_by(user_id=user.id, category=category).all()
        cat_avg = round(sum((r.score / r.total) * 100 for r in attempts) / len(attempts)) if attempts else 0
        category_stats.append({"name": category, "average": cat_avg, "attempts": len(attempts)})
    return render_template("dashboard.html", recent=recent, total_tests=total_tests, avg=round(avg or 0), categories=categories, today_tests=today_tests, goal_target=goal_target, category_stats=category_stats)

@app.route("/quiz/<category>")
@login_required
def quiz(category):
    allowed = ["Aptitude", "Reasoning", "Verbal", "Programming"]
    if category not in allowed:
        flash("Unknown practice category.", "danger"); return redirect(url_for("dashboard"))
    questions = Question.query.filter_by(category=category).all()
    if not questions:
        flash("No questions are available in this category yet.", "warning")
        return redirect(url_for("dashboard"))
    questions = random.sample(questions, min(10, len(questions)))
    saved_ids = {b.question_id for b in Bookmark.query.filter_by(user_id=session["user_id"]).all()}
    return render_template("quiz.html", category=category, questions=questions, saved_ids=saved_ids, duration=max(5, len(questions) * 60))

@app.route("/submit-quiz", methods=["POST"])
@login_required
def submit_quiz():
    payload = request.get_json(silent=True) or {}
    category = payload.get("category")
    answers = payload.get("answers", {})
    ids = [int(x) for x in answers.keys() if str(x).isdigit()]
    questions = Question.query.filter(Question.id.in_(ids), Question.category==category).all()
    score = sum(1 for q in questions if answers.get(str(q.id)) == q.answer)
    total = len(questions)
    if total == 0:
        return jsonify({"error": "No answers received"}), 400
    result = Result(user_id=session["user_id"], category=category, score=score, total=total)
    db.session.add(result); db.session.commit()
    return jsonify({"score": score, "total": total, "percentage": round(score*100/total), "result_id": result.id})

@app.route("/results")
@login_required
def results():
    items = Result.query.filter_by(user_id=session["user_id"]).order_by(Result.taken_at.desc()).all()
    return render_template("results.html", results=items)

@app.route("/leaderboard")
@login_required
def leaderboard():
    rows = db.session.query(User.name, db.func.sum(Result.score).label("points"), db.func.sum(Result.total).label("total")).join(Result).group_by(User.id).order_by(db.desc("points")).limit(10).all()
    return render_template("leaderboard.html", rows=rows)

@app.route("/tools", methods=["GET", "POST"])
@login_required
def tools_page():
    user_id = session["user_id"]
    if request.method == "POST":
        action = request.form.get("action")
        if action == "goal":
            try:
                target = max(1, min(20, int(request.form.get("target_tests", 2))))
                goal = DailyGoal.query.filter_by(user_id=user_id).first()
                if not goal:
                    goal = DailyGoal(user_id=user_id)
                    db.session.add(goal)
                goal.target_tests = target
                db.session.commit()
                flash("Daily goal updated.", "success")
            except ValueError:
                flash("Enter a valid daily target.", "danger")
        elif action == "plan":
            title = request.form.get("title", "").strip()
            subject = request.form.get("subject", "Aptitude").strip()
            due_text = request.form.get("due_date", "")
            try:
                due_date = datetime.strptime(due_text, "%Y-%m-%d").date()
                if title:
                    db.session.add(StudyPlan(user_id=user_id, title=title, subject=subject, due_date=due_date))
                    db.session.commit()
                    flash("Study task added.", "success")
                else:
                    flash("Enter a task title.", "danger")
            except ValueError:
                flash("Choose a valid due date.", "danger")
        return redirect(url_for("tools_page"))
    bookmarks = Bookmark.query.filter_by(user_id=user_id).order_by(Bookmark.created_at.desc()).all()
    plans = StudyPlan.query.filter_by(user_id=user_id).order_by(StudyPlan.completed.asc(), StudyPlan.due_date.asc()).all()
    goal = DailyGoal.query.filter_by(user_id=user_id).first()
    return render_template("tools.html", bookmarks=bookmarks, plans=plans, goal=goal)

@app.route("/bookmark/<int:question_id>", methods=["POST"])
@login_required
def toggle_bookmark(question_id):
    question = db.session.get(Question, question_id)
    if not question:
        flash("Question not found.", "danger")
    else:
        saved = Bookmark.query.filter_by(user_id=session["user_id"], question_id=question_id).first()
        if saved:
            db.session.delete(saved)
            flash("Question removed from bookmarks.", "info")
        else:
            db.session.add(Bookmark(user_id=session["user_id"], question_id=question_id))
            flash("Question bookmarked for revision.", "success")
        db.session.commit()
    return redirect(request.referrer or url_for("dashboard"))

@app.route("/study-plan/<int:plan_id>/toggle", methods=["POST"])
@login_required
def toggle_plan(plan_id):
    task = StudyPlan.query.filter_by(id=plan_id, user_id=session["user_id"]).first_or_404()
    task.completed = not task.completed
    db.session.commit()
    return redirect(url_for("tools_page"))

@app.route("/study-plan/<int:plan_id>/delete", methods=["POST"])
@login_required
def delete_plan(plan_id):
    task = StudyPlan.query.filter_by(id=plan_id, user_id=session["user_id"]).first_or_404()
    db.session.delete(task)
    db.session.commit()
    flash("Study task deleted.", "info")
    return redirect(url_for("tools_page"))

@app.route("/admin")
@admin_required
def admin():
    return render_template("admin.html", questions=Question.query.order_by(Question.category).all(), users=User.query.count(), results=Result.query.count())

@app.route("/admin/add-question", methods=["POST"])
@admin_required
def add_question():
    q = Question(category=request.form["category"], question=request.form["question"],
        option_a=request.form["a"], option_b=request.form["b"], option_c=request.form["c"],
        option_d=request.form["d"], answer=request.form["answer"], explanation=request.form.get("explanation", ""))
    db.session.add(q); db.session.commit()
    flash("Question added successfully.", "success")
    return redirect(url_for("admin"))

@app.route("/admin/delete-question/<int:qid>", methods=["POST"])
@admin_required
def delete_question(qid):
    q = db.session.get(Question, qid)
    if q:
        db.session.delete(q); db.session.commit()
        flash("Question deleted.", "info")
    return redirect(url_for("admin"))

def seed_data():
    if Question.query.count():
        return
    samples = [
        ("Aptitude","A train travels 120 km in 2 hours. What is its speed?","40 km/h","50 km/h","60 km/h","80 km/h","C","Speed = distance / time."),
        ("Aptitude","What is 25% of 240?","40","50","60","70","C","0.25 × 240 = 60."),
        ("Reasoning","Find the next number: 2, 4, 8, 16, ?","20","24","30","32","D","Each term is multiplied by 2."),
        ("Reasoning","Which one is different?","Apple","Mango","Carrot","Banana","C","Carrot is a vegetable."),
        ("Verbal","Choose the synonym of 'Brief'.","Short","Wide","Late","Weak","A","Brief means short."),
        ("Verbal","Choose the correctly spelled word.","Accomodate","Acommodate","Accommodate","Acomodate","C","The correct spelling is accommodate."),
        ("Programming","What is the output of print(2 ** 3) in Python?","5","6","8","9","C","** is the exponentiation operator."),
        ("Programming","Which Python data type is immutable?","List","Dictionary","Set","Tuple","D","A tuple cannot be changed after creation.")
    ]
    for c,q,a,b,d,e,ans,ex in samples:
        db.session.add(Question(category=c, question=q, option_a=a, option_b=b, option_c=d, option_d=e, answer=ans, explanation=ex))
    db.session.commit()

with app.app_context():
    db.create_all()
    seed_data()
    admin_email = os.getenv("ADMIN_EMAIL", "admin@preppilot.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    if not User.query.filter_by(email=admin_email).first():
        db.session.add(User(name="PrepPilot Admin", email=admin_email, password_hash=generate_password_hash(admin_password), role="admin"))
        db.session.commit()

if __name__ == "__main__":
    app.run(debug=True)
