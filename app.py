import os
from flask import Flask, render_template, redirect, url_for, request, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_dance.contrib.google import make_google_blueprint, google
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import secrets
from PIL import Image, ImageDraw
default_dir = os.path.join('static')
default_path = os.path.join(default_dir, 'default.png')
os.makedirs(default_dir, exist_ok=True)
from werkzeug.utils import secure_filename

try:
    from PIL import Image, ImageDraw

    if not os.path.exists(default_path):
        img = Image.new('RGB', (200, 200), color='#E8B4D9')
        draw = ImageDraw.Draw(img)
        draw.ellipse([50, 30, 150, 130], fill='#B752B9')
        draw.ellipse([75, 100, 125, 170], fill='#B752B9')
        img.save(default_path)
        print("Avatar default creato!")
except ImportError:
  
    print("Pillow non installato: salto creazione avatar predefinito. Installa con 'pip install pillow' per abilitarlo.")
print("Avatar default creato!")

app = Flask(__name__)
app.secret_key = "JDHFFLWEJFWEHFLJWEWEOIFHEHEWIOF"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///fantamatrimonio.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

google_bp = make_google_blueprint(
    client_id="TUO_CLIENT_ID",
    client_secret="TUO_CLIENT_SECRET",
    redirect_url="https://therealfantamatrimonio.it/login/google/authorized",
    scope=["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"]
)
app.register_blueprint(google_bp, url_prefix="/login")

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(255))
    avatar = db.Column(db.String(255), default="default.png")
    provider = db.Column(db.String(16), default="local")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    owned_leagues = db.relationship('League', backref='owner', lazy=True, foreign_keys='League.owner_id')
    memberships = db.relationship('LeagueMember', backref='user', lazy=True)
    votes = db.relationship('FactorVote', backref='voter', lazy=True)

class League(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    code = db.Column(db.String(8), unique=True, nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    members = db.relationship('LeagueMember', backref='league', lazy=True, cascade='all, delete-orphan')
    factors = db.relationship('Factor', backref='league', lazy=True, cascade='all, delete-orphan')

class LeagueMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    league_id = db.Column(db.Integer, db.ForeignKey('league.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    age = db.Column(db.Integer)
    avatar = db.Column(db.String(255), default="default.png")
    is_competing = db.Column(db.Boolean, default=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    total_score = db.Column(db.Float, default=0.0)
    votes_received = db.relationship('FactorVote', backref='member', lazy=True)

class Factor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    league_id = db.Column(db.Integer, db.ForeignKey('league.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    weight = db.Column(db.Float, default=1.0)
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    votes = db.relationship('FactorVote', backref='factor', lazy=True, cascade='all, delete-orphan')

class FactorVote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    factor_id = db.Column(db.Integer, db.ForeignKey('factor.id'), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('league_member.id'), nullable=False)
    voter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    score = db.Column(db.Float, nullable=False)
    voted_at = db.Column(db.DateTime, default=datetime.utcnow)

class PendingVote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    league_id = db.Column(db.Integer, db.ForeignKey('league.id'), nullable=False)
    voter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    factor_id = db.Column(db.Integer, db.ForeignKey('factor.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def generate_league_code():
    """Genera un codice univoco per la lega"""
    import random
    import string
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        if not League.query.filter_by(code=code).first():
            return code

def setup_default_factors(league_id):
    """Crea i fattori di default per una nuova lega"""
    default_factors = [
        {"name": "Relazione stabile", "description": "Ha una relazione seria", "weight": 1.5},
        {"name": "Età", "description": "Età del partecipante", "weight": 1.0},
        {"name": "Stabilità economica", "description": "Situazione economica", "weight": 1.2},
        {"name": "Desiderio matrimonio", "description": "Quanto desidera sposarsi", "weight": 1.3},
        {"name": "Pressione familiare", "description": "Pressione della famiglia", "weight": 0.8},
    ]
    
    for factor_data in default_factors:
        factor = Factor(
            league_id=league_id,
            name=factor_data["name"],
            description=factor_data["description"],
            weight=factor_data["weight"],
            is_default=True
        )
        db.session.add(factor)
    db.session.commit()

def calculate_member_scores(league_id):
    """Calcola i punteggi totali per tutti i membri di una lega"""
    members = LeagueMember.query.filter_by(league_id=league_id, is_competing=True).all()
    
    for member in members:
        total = 0
        votes = FactorVote.query.filter_by(member_id=member.id).all()
        
        for vote in votes:
            factor = Factor.query.get(vote.factor_id)
            if factor:
                total += vote.score * factor.weight
        
        member.total_score = total
    
    db.session.commit()

# ============================================
# ROUTES - Autenticazione
# ============================================

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username, provider="local").first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['avatar'] = user.avatar
            flash("Login effettuato con successo!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Credenziali non valide", "danger")
    
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        
        if User.query.filter_by(username=username).first():
            flash("Username già esistente", "danger")
        elif User.query.filter_by(email=email).first():
            flash("Email già registrata", "danger")
        else:
            hashed = generate_password_hash(password)
            user = User(
                username=username,
                email=email,
                password_hash=hashed,
                provider="local",
                avatar="default.png"
            )
            db.session.add(user)
            db.session.commit()
            flash("Registrazione completata! Effettua il login.", "success")
            return redirect(url_for("login"))
    
    return render_template("register.html")

@app.route("/google_login")
@app.route("/google_login")
def google_login():
    if not google.authorized:
        return redirect(url_for("google.login"))

    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        flash("Errore durante l'autenticazione Google", "danger")
        return redirect(url_for("login"))

    user_info = resp.json()

    # Alcune email potrebbero non essere presenti
    email = user_info.get("email")
    if not email:
        flash("Google non ha fornito la tua email.", "danger")
        return redirect(url_for("login"))

    avatar_url = user_info.get("picture", "default.png")
    username = email.split("@")[0]

    # Controlla se l'utente esiste con questa email
    user = User.query.filter_by(email=email).first()

    if user:
        # L'utente esiste, controlla il provider
        if user.provider != "google":
            flash("Questa email è già registrata con un account locale.", "danger")
            return redirect(url_for("login"))
    else:
        # L'utente non esiste, crealo
        user = User(
            username=username,
            email=email,
            avatar=avatar_url,
            provider="google"
        )
        db.session.add(user)
        db.session.commit()

    # Login: aggiorna sessione
    session['user_id'] = user.id
    session['username'] = user.username
    session['avatar'] = user.avatar
    flash("Login con Google effettuato!", "success")
    return redirect(url_for("dashboard"))

@app.route("/logout")
def logout():
    session.clear()
    flash("Logout effettuato", "info")
    return redirect(url_for("home"))

# ============================================
# ROUTES - Dashboard e Profilo
# ============================================

@app.route("/dashboard")
def dashboard():
    if 'user_id' not in session:
        flash("Effettua prima il login", "warning")
        return redirect(url_for("login"))
    
    user = User.query.get(session['user_id'])
    owned_leagues = League.query.filter_by(owner_id=user.id).all()
    
    # Leghe a cui l'utente partecipa
    memberships = LeagueMember.query.filter_by(user_id=user.id).all()
    joined_leagues = [m.league for m in memberships]
    
    return render_template("dashboard.html", 
                         user=user, 
                         owned_leagues=owned_leagues,
                         joined_leagues=joined_leagues)

@app.route("/profilo", methods=["GET", "POST"])
def profilo():
    if 'user_id' not in session:
        flash("Effettua prima il login", "warning")
        return redirect(url_for("login"))
    
    user = User.query.get(session['user_id'])
    
    # Gestione upload avatar
    if request.method == "POST":
        if 'avatar' not in request.files:
            flash("Nessun file selezionato", "danger")
            return redirect(url_for("profilo"))

        file = request.files['avatar']
        if file.filename == '':
            flash("Nessun file selezionato", "danger")
            return redirect(url_for("profilo"))

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            ext = filename.rsplit('.', 1)[1].lower()
            unique_filename = f"user_{session['user_id']}_{secrets.token_hex(8)}.{ext}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(filepath)

            # Elimina vecchio avatar se personalizzato
            if user.avatar and user.avatar != "default.png" and not user.avatar.startswith("http"):
                old_path = os.path.join("static", user.avatar)
                if os.path.exists(old_path):
                    os.remove(old_path)

            user.avatar = f"uploads/avatars/{unique_filename}"
            db.session.commit()
            session["avatar"] = user.avatar
            flash("Avatar aggiornato con successo!", "success")
            return redirect(url_for("profilo"))
        else:
            flash("Formato file non valido (usa PNG, JPG, JPEG, GIF o WEBP)", "danger")
            return redirect(url_for("profilo"))
    
    return render_template("profilo.html", user=user)



# ============================================
# ROUTES - Leghe
# ============================================

@app.route("/league/create", methods=["GET", "POST"])
def create_league():
    if 'user_id' not in session:
        flash("Effettua prima il login", "warning")
        return redirect(url_for("login"))
    
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        
        league = League(
            name=name,
            description=description,
            code=generate_league_code(),
            owner_id=session['user_id']
        )
        db.session.add(league)
        db.session.commit()
        
        # Crea fattori di default
        setup_default_factors(league.id)
        
        flash(f"Lega '{name}' creata con successo! Codice: {league.code}", "success")
        return redirect(url_for("league_detail", league_id=league.id))
    
    return render_template("create_league.html")

@app.route("/league/join", methods=["GET", "POST"])
def join_league():
    if 'user_id' not in session:
        flash("Effettua prima il login", "warning")
        return redirect(url_for("login"))
    
    if request.method == "POST":
        code = request.form.get("code").upper()
        league = League.query.filter_by(code=code).first()
        
        if not league:
            flash("Codice lega non valido", "danger")
        elif LeagueMember.query.filter_by(league_id=league.id, user_id=session['user_id']).first():
            flash("Sei già membro di questa lega", "warning")
        else:
            user = User.query.get(session['user_id'])
            member = LeagueMember(
                league_id=league.id,
                user_id=user.id,
                name=user.username,
                avatar=user.avatar
            )
            db.session.add(member)
            db.session.commit()
            flash(f"Sei entrato nella lega '{league.name}'!", "success")
            return redirect(url_for("league_detail", league_id=league.id))
    
    return render_template("join_league.html")

@app.route("/league/<int:league_id>")
def league_detail(league_id):
    if 'user_id' not in session:
        flash("Effettua prima il login", "warning")
        return redirect(url_for("login"))
    
    league = League.query.get_or_404(league_id)
    members = LeagueMember.query.filter_by(league_id=league_id).order_by(LeagueMember.total_score.desc()).all()
    factors = Factor.query.filter_by(league_id=league_id).all()
    
    is_owner = league.owner_id == session['user_id']
    is_member = LeagueMember.query.filter_by(league_id=league_id, user_id=session['user_id']).first() is not None
    
    return render_template("league_detail.html",
                         league=league,
                         members=members,
                         factors=factors,
                         is_owner=is_owner,
                         is_member=is_member)

@app.route("/league/<int:league_id>/vote", methods=["GET", "POST"])
def vote(league_id):
    if 'user_id' not in session:
        flash("Effettua prima il login", "warning")
        return redirect(url_for("login"))
    
    league = League.query.get_or_404(league_id)
    members = LeagueMember.query.filter_by(league_id=league_id, is_competing=True).all()
    factors = Factor.query.filter_by(league_id=league_id).all()
    
    if request.method == "POST":
        for member in members:
            for factor in factors:
                score_key = f"score_{member.id}_{factor.id}"
                score = request.form.get(score_key)
                
                if score:
                    # Elimina voto precedente se esiste
                    old_vote = FactorVote.query.filter_by(
                        factor_id=factor.id,
                        member_id=member.id,
                        voter_id=session['user_id']
                    ).first()
                    
                    if old_vote:
                        db.session.delete(old_vote)
                    
                    # Crea nuovo voto
                    vote = FactorVote(
                        factor_id=factor.id,
                        member_id=member.id,
                        voter_id=session['user_id'],
                        score=float(score)
                    )
                    db.session.add(vote)
        
        db.session.commit()
        calculate_member_scores(league_id)
        flash("Voti registrati con successo!", "success")
        return redirect(url_for("league_detail", league_id=league_id))
    
    return render_template("vote.html", league=league, members=members, factors=factors)

# ============================================
# ROUTES - Amministrazione Lega
# ============================================

@app.route("/league/<int:league_id>/add_member", methods=["POST"])
def add_member(league_id):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    league = League.query.get_or_404(league_id)
    if league.owner_id != session['user_id']:
        return jsonify({"error": "Only owner can add members"}), 403
    
    name = request.form.get("name")
    age = request.form.get("age")
    
    member = LeagueMember(
        league_id=league_id,
        user_id=session['user_id'],
        name=name,
        age=int(age) if age else None
    )
    db.session.add(member)
    db.session.commit()
    
    flash(f"Membro '{name}' aggiunto alla lega", "success")
    return redirect(url_for("league_detail", league_id=league_id))

@app.route("/league/<int:league_id>/add_factor", methods=["POST"])
def add_factor(league_id):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    league = League.query.get_or_404(league_id)
    if league.owner_id != session['user_id']:
        return jsonify({"error": "Only owner can add factors"}), 403
    
    name = request.form.get("name")
    description = request.form.get("description")
    weight = request.form.get("weight", 1.0)
    
    factor = Factor(
        league_id=league_id,
        name=name,
        description=description,
        weight=float(weight)
    )
    db.session.add(factor)
    db.session.commit()
    
    flash(f"Fattore '{name}' aggiunto", "success")
    return redirect(url_for("league_detail", league_id=league_id))

    
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads', 'avatars')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max

# Crea cartella upload se non esiste
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/upload_avatar", methods=["POST"])
def upload_avatar():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    if 'avatar' not in request.files:
        flash("Nessun file selezionato", "danger")
        return redirect(url_for("dashboard"))
    
    file = request.files['avatar']
    
    if file.filename == '':
        flash("Nessun file selezionato", "danger")
        return redirect(url_for("dashboard"))
    
    if file and allowed_file(file.filename):
        
        filename = secure_filename(file.filename)
        ext = filename.rsplit('.', 1)[1].lower()
        unique_filename = f"user_{session['user_id']}_{secrets.token_hex(8)}.{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        # Salva file
        file.save(filepath)
        
        # Aggiorna database
        user = User.query.get(session['user_id'])
        old_avatar = user.avatar
        
        # Elimina vecchio avatar se non è default
        if old_avatar and old_avatar != 'default.png' and not old_avatar.startswith('http'):
            old_path = os.path.join('static', old_avatar)
            if os.path.exists(old_path):
                os.remove(old_path)
        
        user.avatar = f"uploads/avatars/{unique_filename}"
        db.session.commit()
        
        # Aggiorna sessione
        session['avatar'] = user.avatar
        
        flash("Avatar aggiornato con successo!", "success")
        return redirect(url_for("dashboard"))
    else:
        flash("Formato file non valido. Usa PNG, JPG, JPEG, GIF o WEBP", "danger")
        return redirect(url_for("dashboard"))
@app.route("/privacy")
def privacy_policy():
    return render_template("privacy_policy.html")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
