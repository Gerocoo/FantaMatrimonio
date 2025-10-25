import os
from flask import Flask, render_template, redirect, url_for, request, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from flask_dance.contrib.google import make_google_blueprint, google
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets
from PIL import Image, ImageDraw
default_dir = os.path.join('static')
default_path = os.path.join(default_dir, 'default.png')
os.makedirs(default_dir, exist_ok=True)
from werkzeug.utils import secure_filename
from itsdangerous import URLSafeTimedSerializer
from flask import current_app
from mailtrap import MailtrapClient, Mail, Address
import logging
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests


try:
    from PIL import Image, ImageDraw

    if not os.path.exists(default_path):
        img = Image.new('RGB', (200, 200), color='#E8B4D9')
        draw = ImageDraw.Draw(img)
        draw.ellipse([50, 30, 150, 130], fill='#B752B9')
        draw.ellipse([75, 100, 125, 170], fill='#B752B9')
        img.save(default_path)
        
except ImportError:
  
    
    print("Avatar default creato!")

app = Flask(__name__)
app.secret_key = "JDHFFLWEJFWEHFLJWEWEOIFHEHEWIOF"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///fantamatrimonio.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
app.config["SESSION_COOKIE_SECURE"] = False
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"



google_bp = make_google_blueprint(
    client_id="784920498349-fh705qbs12onumrks7pbgvn3rdj7ud39.apps.googleusercontent.com",
    client_secret="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",
    redirect_to="google_login", 
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
    is_verified = db.Column(db.Boolean, default=False)
    email_token = db.Column(db.String(128))
    owned_leagues = db.relationship('League', backref='owner', lazy=True, foreign_keys='League.owner_id')
    memberships = db.relationship('LeagueMember', backref='user', lazy=True)
    votes = db.relationship('FactorVote', backref='voter', lazy=True)
    reset_token = db.Column(db.String(100), unique=True)
    reset_token_expiry = db.Column(db.DateTime)

class ChatMessage(db.Model):
    """Modello per i messaggi della chat"""
    __tablename__ = 'chat_message'
    
    id = db.Column(db.Integer, primary_key=True)
    league_id = db.Column(db.Integer, db.ForeignKey('league.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships - NOTA: backref rinominati per evitare conflitti
    user = db.relationship('User', backref=db.backref('messages_sent', lazy='dynamic'))
    league = db.relationship('League', backref=db.backref('messages', lazy='dynamic'))
    attachments = db.relationship('ChatAttachment', backref='message', cascade='all, delete-orphan', lazy='dynamic')
    
    def __repr__(self):
        return f'<ChatMessage {self.id} by {self.user.username}>'


class ChatAttachment(db.Model):
    """Modello per gli allegati dei messaggi"""
    __tablename__ = 'chat_attachment'
    
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('chat_message.id'), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    original_name = db.Column(db.String(200), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ChatAttachment {self.id} - {self.original_name}>'

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
    password_hash = db.Column(db.String(128), nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)
    
# class LeagueChatMessage(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     league_id = db.Column(db.Integer, db.ForeignKey('league.id'), nullable=False)
#     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
#     message = db.Column(db.Text, nullable=False)
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)

#     user = db.relationship('User', backref='messages')
#     league = db.relationship('League', backref='chat_messages')

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


def init_database():

    with app.app_context():
        db.create_all()  
        
        
        try:
            with db.engine.connect() as conn:
                result = conn.execute(text("PRAGMA table_info(user)")).fetchall()
                columns = [row[1] for row in result]
                
                if 'reset_token' not in columns:
                    conn.execute(text("ALTER TABLE user ADD COLUMN reset_token VARCHAR(100)"))
                    print("✅ Colonna reset_token aggiunta")
                
                if 'reset_token_expiry' not in columns:
                    conn.execute(text("ALTER TABLE user ADD COLUMN reset_token_expiry DATETIME"))
                    print("✅ Colonna reset_token_expiry aggiunta")
                
                conn.commit()
        except Exception as e:
            print(f"Info database: {e}")


init_database()


def generate_league_code():
    """Genera un codice univoco per la lega"""
    import random
    import string
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        if not League.query.filter_by(code=code).first():
            return code
def get_serializer():
    return URLSafeTimedSerializer(app.secret_key)

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



reset_password_html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: 'Arial', sans-serif;
            background-color: #f9f9f9;
            margin: 0;
            padding: 0;
        }}
        .container {{
            max-width: 600px;
            margin: 40px auto;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        .header {{
            background: linear-gradient(135deg, #ff5ace 0%, #ffa3d7 100%);
            padding: 40px 20px;
            text-align: center;
        }}
        .header h1 {{
            color: white;
            margin: 0;
            font-family: 'Dancing Script', cursive;
            font-size: 2.5rem;
        }}
        .content {{
            padding: 40px 30px;
        }}
        .content h2 {{
            color: #ff5ace;
            margin-top: 0;
        }}
        .content p {{
            font-size: 16px;
            line-height: 1.6;
            color: #333;
        }}
        .button {{
            display: inline-block;
            background: #ff5ace;
            color: white;
            padding: 15px 40px;
            text-decoration: none;
            border-radius: 30px;
            font-weight: bold;
            font-size: 16px;
            margin: 20px 0;
        }}
        .button:hover {{
            background: #e143a3;
        }}
        .footer {{
            background: #f5f5f5;
            padding: 20px;
            text-align: center;
            font-size: 12px;
            color: #999;
        }}
        .warning {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>FantaMatrimonio</h1>
        </div>
        <div class="content">
            <h2>Ciao {username}!</h2>
            <p>Hai richiesto di reimpostare la tua password su <strong>FantaMatrimonio</strong>.</p>
            <p>Clicca sul pulsante qui sotto per reimpostare la password. Il link è valido per <strong>1 ora</strong>:</p>
            <div style="text-align: center;">
                <a href="{reset_url}" class="button">Reimposta Password</a>
            </div>
            <div class="warning">
                <p style="margin: 0;"><strong>⚠️ Importante:</strong> Se non hai richiesto questa reimpostazione, puoi ignorare tranquillamente questa email. La tua password rimarrà invariata.</p>
            </div>
            <p>Se il pulsante non funziona, copia e incolla questo link nel browser:</p>
            <p style="word-break: break-all; font-size: 14px; color: #666;">{reset_url}</p>
        </div>
        <div class="footer">
            <p><strong>Il Team di FantaMatrimonio</strong></p>
            <p><em>Il gioco di scommesse più divertente e goliardico!</em></p>
        </div>
    </div>
</body>
</html>
"""
def send_reset_password_email(user_email, username, reset_url):
    """Invia email di reset password tramite Mailtrap"""
    try:
        mail = Mail(
            sender=Address(email="noreply@therealfantamatrimonio.it", name="FantaMatrimonio"),
            to=[Address(email=user_email)],
            subject="Reimposta la tua password - FantaMatrimonio",
            html=reset_password_html_template.format(username=username, reset_url=reset_url),
            category="password_reset"
        )
        client = MailtrapClient(token="616b82792c3fd1696348a9d3f3ff382b")
        response = client.send(mail)
        return True
    except Exception as e:
        print(f"Errore invio email reset password: {e}")
        return False

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        
        # Verifica che username ed email corrispondano
        user = User.query.filter_by(username=username, email=email).first()
        
        if user:
            # Genera token univoco
            token = secrets.token_urlsafe(32)
            user.reset_token = token
            user.reset_token_expiry = datetime.now() + timedelta(hours=1)  # Valido 1 ora
            db.session.commit()
            
            # Invia email
            reset_url = url_for('reset_password', token=token, _external=True)
            
            if send_reset_password_email(user.email, user.username, reset_url):
                flash("Email di reimpostazione inviata! Controlla la tua casella di posta.", "success")
            else:
                flash("Errore nell'invio dell'email. Riprova più tardi.", "danger")
                return redirect(url_for('forgot_password'))
        else:
            # Per sicurezza, non specificare se username o email sono sbagliati
            flash("Se username ed email corrispondono, riceverai un'email di reimpostazione.", "info")
        
        return redirect(url_for('login'))
    
    return render_template("forgot_password.html")


# Route per reimpostare la password con il token
@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()
    
    # Verifica token valido e non scaduto
    if not user or not user.reset_token_expiry or user.reset_token_expiry < datetime.now():
        flash("Link di reimpostazione non valido o scaduto.", "danger")
        return redirect(url_for('forgot_password'))
    
    if request.method == "POST":
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")
        
        if new_password != confirm_password:
            flash("Le password non corrispondono.", "danger")
            return redirect(url_for('reset_password', token=token))
        
        if len(new_password) < 6:
            flash("La password deve essere di almeno 6 caratteri.", "warning")
            return redirect(url_for('reset_password', token=token))
        
        # Aggiorna password
        user.set_password(new_password)
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()
        
        flash("Password reimpostata con successo! Ora puoi effettuare il login.", "success")
        return redirect(url_for('login'))
    
    return render_template("reset_password.html", token=token)


@app.route("/")
def home():
    search_query = request.args.get('search', '').strip()
    
    if search_query:
        # Cerca per nome lega o username del proprietario
        leagues = League.query.join(User, League.owner_id == User.id).filter(
            db.or_(
                League.name.ilike(f'%{search_query}%'),
                User.username.ilike(f'%{search_query}%')
            ),
            League.is_active == True
        ).all()
    else:
        # Mostra tutte le leghe attive
        leagues = League.query.filter_by(is_active=True).all()
    
    return render_template("index.html", leagues=leagues, search_query=search_query)

@app.route("/rules")
def rules():
    return render_template("rules.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username, provider="local").first()
        
        if user and check_password_hash(user.password_hash, password):
            if not user.is_verified:
                flash("Devi prima confermare la tua email!", "warning")
                return redirect(url_for("login"))
            session['user_id'] = user.id
            session['username'] = user.username
            session['avatar'] = user.avatar
            flash("Login effettuato con successo!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Credenziali non valide", "danger")
    return render_template("login.html")



confirmation_html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: 'Arial', sans-serif;
            background-color: #f9f9f9;
            margin: 0;
            padding: 0;
        }}
        .container {{
            max-width: 600px;
            margin: 40px auto;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        .header {{
            background: linear-gradient(135deg, #ff5ace 0%, #ffa3d7 100%);
            padding: 40px 20px;
            text-align: center;
        }}
        .header h1 {{
            color: white;
            margin: 0;
            font-family: 'Dancing Script', cursive;
            font-size: 2.5rem;
        }}
        .content {{
            padding: 40px 30px;
        }}
        .content h2 {{
            color: #ff5ace;
            margin-top: 0;
        }}
        .content p {{
            font-size: 16px;
            line-height: 1.6;
            color: #333;
        }}
        .button {{
            display: inline-block;
            background: #ff5ace;
            color: white;
            padding: 15px 40px;
            text-decoration: none;
            border-radius: 30px;
            font-weight: bold;
            font-size: 16px;
            margin: 20px 0;
        }}
        .button:hover {{
            background: #e143a3;
        }}
        .footer {{
            background: #f5f5f5;
            padding: 20px;
            text-align: center;
            font-size: 12px;
            color: #999;
        }}
        .warning {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>FantaMatrimonio</h1>
        </div>
        <div class="content">
            <h2>Ciao {username}!</h2>
   <p>Clicca sul pulsante qui sotto per attivare il tuo account. Il link è valido per <strong>1 ora</strong>:</p>
            <div style="text-align: center;">
                <a href="{confirm_url}" class="button">Conferma</a>
            </div>
            <div class="warning">
                <p style="margin: 0;"><strong>⚠️ Importante:</strong> Se non hai richiesto questa registrazione, puoi ignorare questa email. </p>
            </div>
            <p>Se il pulsante non funziona, copia e incolla questo link nel browser:</p>
            <p style="word-break: break-all; font-size: 14px; color: #666;">{confirm_url}</p>
        </div>
        <div class="footer">
            <p><strong>Il Team di FantaMatrimonio</strong></p>
            <p><em>Il gioco di scommesse più divertente e goliardico!</em></p>
        </div>
    </div>
</body>
</html>
"""


@app.route("/register", methods=["GET", "POST"])
def register():
    try:
        if request.method == "POST":
            username = request.form.get("username")
            email = request.form.get("email")
            password = request.form.get("password")
            if User.query.filter_by(username=username).first():
                flash("Username già esistente", "danger")
                return render_template("register.html")
            elif User.query.filter_by(email=email).first():
                flash("Email già registrata", "danger")
                return render_template("register.html")
            hashed = generate_password_hash(password)
            token = get_serializer().dumps(email, salt="email-confirm")
            user = User(
                username=username,
                email=email,
                password_hash=hashed,
                provider="local",
                avatar="default.png",
                is_verified=False,
                email_token=token
            )
            
            link = url_for('confirm_email', token=token, _external=True)
            mail = Mail(
                sender=Address(email="noreply@therealfantamatrimonio.it", name="FantaMatrimonio"),
                to=[Address(email=email)],
                subject="Conferma la tua email per FantaMatrimonio!",
                html=confirmation_html_template.format(username=username, confirm_url=link),
                category="register"
            )
            client = MailtrapClient(token="616b82792c3fd1696348a9d3f3ff382b")
            response = client.send(mail)
            print(response)
            db.session.add(user)
            db.session.commit()
            flash("Registrazione effettuata! Controlla la tua mail per confermare l'account.", "info")
            return redirect(url_for("login"))
        return render_template("register.html")
    except Exception as e:
        print("ERRORE REGISTRAZIONE:", e)
        flash("Errore durante la registrazione: " + str(e), "danger")
        return render_template("register.html")
    


@app.route('/league/<league_code>/chat', methods=['GET'])
def get_chat_messages(league_code):
    """Recupera tutti i messaggi della chat di una lega"""
    if 'user_id' not in session:
        return jsonify({'error': 'Non autenticato'}), 401
    
    league = League.query.filter_by(code=league_code).first_or_404()
    messages = ChatMessage.query.filter_by(league_id=league.id)\
                                 .order_by(ChatMessage.created_at.asc())\
                                 .all()
    
    result = []
    for msg in messages:
        attachments_list = []
        for att in msg.attachments:
            attachments_list.append({
                'id': att.id,
                'name': att.original_name,
                'url': url_for('uploaded_file', filename=att.filename),
                'type': att.file_type,
                'size': att.file_size
            })
        
        result.append({
            'id': msg.id,
            'user': msg.user.username,
            'message': msg.message or '',
            'created_at': msg.created_at.isoformat(),
            'attachments': attachments_list
        })
    
    return jsonify(result)


@app.route('/league/<league_code>/chat', methods=['POST'])
def send_chat_message(league_code):
    """Invia un nuovo messaggio con eventuali allegati"""
    if 'user_id' not in session:
        return jsonify({'error': 'Non autenticato'}), 401
    
    league = League.query.filter_by(code=league_code).first_or_404()
    message_text = request.form.get('message', '').strip()
    
    # Validazione: almeno un messaggio o un file
    if not message_text and not request.files:
        return jsonify({'error': 'Messaggio o file richiesto'}), 400
    
    # Crea il messaggio
    new_message = ChatMessage(
        league_id=league.id,
        user_id=session['user_id'],
        message=message_text if message_text else None
    )
    db.session.add(new_message)
    db.session.flush()  # Ottieni l'ID prima del commit
    
    # Gestisci file allegati
    attachments_data = []
    for key in request.files:
        file = request.files[key]
        
        if file and file.filename:
            # Verifica estensione
            if not allowed_file(file.filename):
                db.session.rollback()
                return jsonify({'error': f'Tipo file non permesso: {file.filename}'}), 400
            
            # Genera nome file sicuro e unico
            original_filename = secure_filename(file.filename)
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
            ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
            unique_filename = f"{timestamp}_{session['user_id']}.{ext}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            
            try:
                # Salva file
                file.save(filepath)
                file_size = os.path.getsize(filepath)
                
                # Crea record attachment nel database
                attachment = ChatAttachment(
                    message_id=new_message.id,
                    filename=unique_filename,
                    original_name=original_filename,
                    file_type=get_file_type(original_filename),
                    file_size=file_size
                )
                db.session.add(attachment)
                
                attachments_data.append({
                    'name': original_filename,
                    'url': url_for('uploaded_file', filename=unique_filename),
                    'type': get_file_type(original_filename),
                    'size': file_size
                })
            
            except Exception as e:
                db.session.rollback()
                # Rimuovi file se salvato
                if os.path.exists(filepath):
                    os.remove(filepath)
                return jsonify({'error': f'Errore nel salvataggio: {str(e)}'}), 500
    
    try:
        db.session.commit()
        return jsonify({
            'status': 'ok',
            'message_id': new_message.id,
            'user': session.get('username'),
            'message': message_text,
            'created_at': new_message.created_at.isoformat(),
            'attachments': attachments_data
        })
    
    except Exception as e:
        db.session.rollback()
        # Rimuovi file caricati in caso di errore
        for att in attachments_data:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], att['name'])
            if os.path.exists(filepath):
                os.remove(filepath)
        return jsonify({'error': f'Errore nel database: {str(e)}'}), 500


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve i file caricati dagli utenti"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/league/<league_code>/chat/delete/<int:message_id>', methods=['DELETE'])
def delete_chat_message(league_code, message_id):
    """Elimina un messaggio (solo chi l'ha inviato o l'owner della lega)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Non autenticato'}), 401
    
    league = League.query.filter_by(code=league_code).first_or_404()
    message = ChatMessage.query.get_or_404(message_id)
    
    # Verifica permessi
    if message.user_id != session['user_id'] and league.owner_id != session['user_id']:
        return jsonify({'error': 'Non autorizzato'}), 403
    
    # Elimina file allegati
    for attachment in message.attachments:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], attachment.filename)
        if os.path.exists(filepath):
            os.remove(filepath)
    
    db.session.delete(message)
    db.session.commit()
    
    return jsonify({'status': 'ok', 'deleted_id': message_id})


@app.route("/league/<league_id>/delete", methods=["POST"])
def delete_league(league_id):
    if 'user_id' not in session:
        flash("Effettua prima il login", "warning")
        return redirect(url_for("login"))
    
    league = League.query.get_or_404(league_id)
    
    if league.owner_id != session['user_id']:
        flash("Solo il proprietario può eliminare la lega", "danger")
        return redirect(url_for("dashboard"))
    
    db.session.delete(league)
    db.session.commit()
    
    flash(f"Lega '{league.name}' eliminata con successo", "success")
    return redirect(url_for("dashboard"))

@app.route('/update_username', methods=['POST'])
def update_username():
    if 'user_id' not in session:
        flash("Effettua il login per continuare", "warning")
        return redirect(url_for('login'))
    new_username = request.form.get('username')
    if not new_username or len(new_username) > 120:
        flash("Nome utente non valido", "danger")
        return redirect(url_for('profilo'))
    existing = User.query.filter_by(username=new_username).first()
    if existing and existing.id != session['user_id']:
        flash("Nome utente già utilizzato", "danger")
        return redirect(url_for('profilo'))
    user = User.query.get(session['user_id'])
    user.username = new_username
    db.session.commit()
    session['username'] = new_username
    flash("Nome utente aggiornato con successo", "success")
    return redirect(url_for('profilo'))

@app.route('/change_password', methods=['POST'])
def change_password():
    if 'user_id' not in session:
        flash("Effettua il login per continuare", "warning")
        return redirect(url_for('login'))
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    user = User.query.get(session['user_id'])
    if not user or not check_password_hash(user.password_hash, current_password):
        flash("Password attuale errata", "danger")
        return redirect(url_for('profilo'))
    if new_password != confirm_password:
        flash("La nuova password e la conferma non corrispondono", "danger")
        return redirect(url_for('profilo'))
    user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    flash("Password aggiornata con successo", "success")
    return redirect(url_for('profilo'))


@app.route("/google_login")
def google_login():
    try:
        if not google.authorized:
            return redirect(url_for("google.login"))
        resp = google.get("/oauth2/v2/userinfo")
        if not resp.ok:
            flash("Errore durante l'autenticazione Google", "danger")
            return redirect(url_for("login"))
        user_info = resp.json()

        email = user_info.get("email")
        if not email:
            flash("Google non ha fornito la tua email.", "danger")
            return redirect(url_for("login"))

        avatar_url = user_info.get("picture", "default.png")
        username = email.split("@")[0]
        user = User.query.filter_by(email=email).first()
        if user:
            if user.provider != "google":
                flash("Questa email è già registrata con un account locale.", "danger")
                return redirect(url_for("login"))
        else:
            user = User(
                username=username,
                email=email,
                avatar=avatar_url,
                provider="google"
            )
            db.session.add(user)
            db.session.commit()

        session['user_id'] = user.id
        session['username'] = user.username
        session['avatar'] = user.avatar
        flash("Login con Google effettuato!", "success")
        return redirect(url_for("dashboard"))
    except Exception as e:
        return f"Errore interno Google login: {str(e)}", 500
@app.route("/google_login_token", methods=["POST"])
def google_login_token():
    """Gestisce il login tramite popup Google Sign-In"""
    try:
        token = request.json.get("token")
        
        # Verifica il token con Google
        idinfo = id_token.verify_oauth2_token(
            token, 
            google_requests.Request(), 
            "784920498349-fh705qbs12onumrks7pbgvn3rdj7ud39.apps.googleusercontent.com"
        )
        
        # Verifica che sia per la tua app
        if idinfo['aud'] != "784920498349-fh705qbs12onumrks7pbgvn3rdj7ud39.apps.googleusercontent.com":
            raise ValueError('Token non valido')
        
        email = idinfo.get('email')
        if not email:
            return jsonify({
                "success": False, 
                "message": "Email non fornita da Google"
            }), 400
        
        avatar_url = idinfo.get('picture', 'default.png')
        username = email.split("@")[0]
        
        # Cerca o crea l'utente
        user = User.query.filter_by(email=email).first()
        if user:
            if user.provider != "google":
                return jsonify({
                    "success": False, 
                    "message": "Questa email è già registrata con un account locale"
                }), 400
            # Aggiorna l'avatar se è cambiato
            if user.avatar != avatar_url:
                user.avatar = avatar_url
                db.session.commit()
        else:
            # Crea nuovo utente
            user = User(
                username=username,
                email=email,
                avatar=avatar_url,
                provider="google"
            )
            db.session.add(user)
            db.session.commit()
        
        # Imposta la sessione
        session['user_id'] = user.id
        session['username'] = user.username
        session['avatar'] = user.avatar
        
        return jsonify({
            "success": True,
            "message": "Login effettuato con successo"
        })
        
    except ValueError as e:
        print(f"Errore validazione token: {e}")
        return jsonify({
            "success": False,
            "message": f"Token non valido: {str(e)}"
        }), 401
    except Exception as e:
        print(f"Errore login Google: {e}")
        return jsonify({
            "success": False,
            "message": "Errore durante il login"
        }), 500

   
@app.route("/league/<league_id>/chat", methods=["GET", "POST"])
def league_chat(league_id):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    if request.method == "POST":
        data = request.get_json()
        msg_text = data.get("message")
        if not msg_text:
            return jsonify({"error": "Message empty"}), 400

        msg = LeagueChatMessage(
            league_id=league_id,
            user_id=session['user_id'],
            message=msg_text
        )
        db.session.add(msg)
        db.session.commit()
        return jsonify({"success": True, "message_id": msg.id})

    else:  
        messages = LeagueChatMessage.query.filter_by(league_id=league_id).order_by(LeagueChatMessage.created_at.desc()).limit(50).all()
        return jsonify([{
            "id": m.id,
            "user": m.user.username,
            "avatar": m.user.avatar,
            "message": m.message,
            "created_at": m.created_at.isoformat()
        } for m in reversed(messages)])

@app.route('/confirm/<token>')
def confirm_email(token):
    try:
        email = get_serializer().loads(token, salt="email-confirm", max_age=3600*48)
    except Exception:
        flash("Link non valido o scaduto. Prova a registrarti di nuovo.", "danger")
        return redirect(url_for('login'))

    user = User.query.filter_by(email=email).first()
    if user and not user.is_verified:
        user.is_verified = True
        user.email_token = None
        db.session.commit()
        flash("Email confermata! Ora puoi accedere.", "success")
        return redirect(url_for('login'))
    elif user and user.is_verified:
        flash("Email già confermata. Effettua il login.", "info")
        return redirect(url_for('login'))
    else:
        flash("Utente inesistente.", "danger")
        return redirect(url_for('register'))
    
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
        password = request.form.get("password")
        
        league = League(
            name=name,
            description=description,
            code=generate_league_code(),
            owner_id=session['user_id']
        )
        if password:
            league.set_password(password)
        db.session.add(league)
        db.session.commit()
        
        # Crea fattori di default
        setup_default_factors(league.id)
        
        flash(f"Lega '{name}' creata con successo! Codice: {league.code}", "success")
        return redirect(url_for("league_detail", league_id=league.id))
    
    return render_template("create_league.html")

@app.route("/league/<int:league_id>")
def league_detail(league_id):
    if 'user_id' not in session:
        flash("Effettua prima il login", "warning")
        return redirect(url_for("login"))
    
    league = db.session.get(League, league_id)
    if not league:
        flash("Lega non trovata", "danger")
        return redirect(url_for("dashboard"))
    
    # Recupera membri ordinati per punteggio
    members = LeagueMember.query.filter_by(league_id=league_id).order_by(LeagueMember.total_score.desc()).all()
    
    # Recupera i fattori della lega
    factors = Factor.query.filter_by(league_id=league_id).all()
    
    # Verifica se l'utente loggato è membro o proprietario
    is_member = LeagueMember.query.filter_by(league_id=league_id, user_id=session['user_id']).first() is not None
    is_owner = (league.owner_id == session['user_id'])
    
    return render_template(
        "league_detail.html", 
        league=league, 
        members=members, 
        factors=factors, 
        is_member=is_member, 
        is_owner=is_owner
    )

@app.route("/league/join", methods=["GET", "POST"])
def join_league():
    if 'user_id' not in session:
        flash("Effettua prima il login", "warning")
        return redirect(url_for("login"))
    
    if request.method == "POST":
        code = request.form.get("code", "").upper().strip()
        password = request.form.get("password", "")
        
        if not code:
            flash("Inserisci il codice della lega", "danger")
            return redirect(url_for("join_league"))
        
        league = League.query.filter_by(code=code).first()
        
        if not league:
            flash("Codice lega non valido", "danger")
            return redirect(url_for("join_league"))
        
        # Controlla se l'utente è già membro
        existing_member = LeagueMember.query.filter_by(
            league_id=league.id, 
            user_id=session['user_id']
        ).first()
        
        if existing_member:
            flash("Sei già membro di questa lega", "warning")
            return redirect(url_for("league_detail", league_id=league.id))
        
        # IMPORTANTE: Verifica password se la lega è protetta
        if league.password_hash:
            if not password:
                flash("Questa lega richiede una password", "danger")
                return redirect(url_for("join_league"))
            
            if not league.check_password(password):
                flash("Password errata. Contatta l'amministratore della lega.", "danger")
                return redirect(url_for("join_league"))
        
        # Aggiungi l'utente alla lega
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
    
    # GET - mostra tutte le leghe disponibili
    leagues = League.query.filter_by(is_active=True).all()
    return render_template("join_league.html", leagues=leagues)

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
        file.save(filepath)
        
        user = User.query.get(session['user_id'])
        old_avatar = user.avatar

        if old_avatar and old_avatar != 'default.png' and not old_avatar.startswith('http'):
            old_path = os.path.join('static', old_avatar)
            if os.path.exists(old_path):
                os.remove(old_path)
        
        user.avatar = f"uploads/avatars/{unique_filename}"
        db.session.commit()
        session['avatar'] = user.avatar
        
        flash("Avatar aggiornato con successo!", "success")
        return redirect(url_for("dashboard"))
    else:
        flash("Formato file non valido. Usa PNG, JPG, JPEG, GIF o WEBP", "danger")
        return redirect(url_for("dashboard"))
@app.route("/league/<int:league_id>/vote", methods=["GET", "POST"])
def vote(league_id):
    if 'user_id' not in session:
        flash("Effettua prima il login", "warning")
        return redirect(url_for("login"))
    
    league = db.session.get(League, league_id)
    if not league:
        flash("Lega non trovata", "danger")
        return redirect(url_for("dashboard"))
    
    members = LeagueMember.query.filter_by(league_id=league_id, is_competing=True).all()
    factors = Factor.query.filter_by(league_id=league_id).all()

    if request.method == "POST":
        try:
            for member in members:
                # Evita l'autovoto
                if member.user_id == session['user_id']:
                    continue
                
                for factor in factors:
                    score_key = f"score_{member.id}_{factor.id}"
                    score = request.form.get(score_key)
                    
                    if score:
                        existing_vote = FactorVote.query.filter_by(
                            factor_id=factor.id,
                            member_id=member.id,
                            voter_id=session['user_id']
                        ).first()
                        
                        if existing_vote:
                            existing_vote.score = float(score)
                        else:
                            new_vote = FactorVote(
                                factor_id=factor.id,
                                member_id=member.id,
                                voter_id=session['user_id'],
                                score=float(score)
                            )
                            db.session.add(new_vote)
            
            db.session.commit()
            calculate_member_scores(league_id)
            flash("Voti registrati con successo!", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Errore durante la registrazione dei voti: {str(e)}", "danger")
        
        return redirect(url_for("league_detail", league_id=league_id))

    # Escludi l'utente loggato dalla visualizzazione
    filtered_members = [m for m in members if m.user_id != session['user_id']]
    return render_template("vote.html", league=league, members=filtered_members, factors=factors)
    
        
@app.route("/privacy")
def privacy_policy():
    return render_template("privacy_policy.html")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
