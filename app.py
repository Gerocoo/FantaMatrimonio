from dotenv import load_dotenv
import os
from flask import Flask, render_template, redirect, url_for, request, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from sqlalchemy.ext.hybrid import hybrid_property
from flask_dance.contrib.google import make_google_blueprint, google
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, time, timedelta
import secrets
from flask import make_response, send_file
import random
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
from flask import send_from_directory
import time
from datetime import datetime
from pywebpush import webpush, WebPushException
import json
from py_vapid import Vapid
from pywebpush import webpush, WebPushException
import json
load_dotenv()


VAPID_FILE = 'vapid_private.pem'
VAPID_CLAIMS = {"sub": "mailto:admin@therealfantamatrimonio.it"}

if os.path.exists(VAPID_FILE):
    vapid_instance = Vapid.from_file(VAPID_FILE)
    print("Chiavi VAPID caricate da", VAPID_FILE)
else:
    vapid_instance = None
    print("File", VAPID_FILE, "non trovato!")

def send_push_notification(user_id, title, body, url, tag='default'):
    """Invia notifica push"""
    if not vapid_instance:
        print("VAPID non inizializzato")
        return
    
    subscriptions = PushSubscription.query.filter_by(
        user_id=user_id, 
        is_active=True
    ).all()
    
    if not subscriptions:
        print(f"Nessuna subscription per user {user_id}")
        return
    
    payload = json.dumps({
        'title': title,
        'body': body,
        'url': url,
        'tag': tag,
        'icon': '/static/images/icon-192.png',
        'badge': '/static/images/badge-72.png'
    })
    
    for sub in subscriptions:
        try:
            subscription_info = json.loads(sub.subscription_info)
            
            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=vapid_instance,
                vapid_claims=VAPID_CLAIMS
            )
            
            print(f"Notifica inviata a user {user_id}")
            
        except WebPushException as e:
            print(f"WebPush error: {e}")
            if e.response and e.response.status_code == 410:
                sub.is_active = False
                db.session.commit()
                
        except Exception as e:
            print(f"Errore: {e}")
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
app.secret_key = os.getenv('SECRET_KEY')
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///fantamatrimonio.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
app.config["SESSION_COOKIE_SECURE"] = False
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}


google_bp = make_google_blueprint(
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    redirect_to="google_login", 
    scope=["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"]
)
app.register_blueprint(google_bp, url_prefix="/login")

class Voting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    league_id = db.Column(db.Integer, db.ForeignKey('league.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    league = db.relationship('League', backref='votings')

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
    memberships = db.relationship('LeagueMember', back_populates='user', lazy=True)
    votes = db.relationship('FactorVote', backref='voter', lazy=True)
    reset_token = db.Column(db.String(100), unique=True)
    reset_token_expiry = db.Column(db.DateTime)
    
    #Questionario iniziale
    questionnaire_completed = db.Column(db.Boolean, default=False)
    marriage_score = db.Column(db.Integer, default=0)
    
    
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20), default="Altro")  # AGGIUNGI QUESTA RIGA
    employment_status = db.Column(db.String(100))
    longest_relationship = db.Column(db.Integer)  # In mesi
    num_relationships = db.Column(db.Integer)
    current_status = db.Column(db.String(50))
    has_cheated = db.Column(db.Boolean)
    would_cheat = db.Column(db.String(50))
    marriage_idea = db.Column(db.Text)
    wants_children = db.Column(db.Integer)
    living_together = db.Column(db.String(50))
    commitment_level = db.Column(db.Integer)
    
    
    def set_password(self, password):
        """Imposta la password con hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verifica se la password corrisponde"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'
@app.context_processor
def inject_cache_buster():
    return {'cache_bust': int(time.time())}

class ChatMessage(db.Model):
    """Modello per i messaggi della chat"""
    __tablename__ = 'chat_message'
    
    id = db.Column(db.Integer, primary_key=True)
    league_id = db.Column(db.Integer, db.ForeignKey('league.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    
    user = db.relationship('User', backref=db.backref('messages_sent', lazy='dynamic'))
    league = db.relationship('League', backref=db.backref('messages', lazy='dynamic'))

    
    def __repr__(self):
        return f'<ChatMessage {self.id} by {self.user.username}>'

class BlacklistedMember(db.Model):
    __tablename__ = 'blacklisted_members'
    id = db.Column(db.Integer, primary_key=True)
    league_id = db.Column(db.Integer, db.ForeignKey('league.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    removed_at = db.Column(db.DateTime, default=datetime.utcnow)

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
    age = db.Column(db.Integer)
    avatar = db.Column(db.String(255), default="default.png")
    is_competing = db.Column(db.Boolean, default=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    total_score = db.Column(db.Float, default=0.0)
    is_banned = db.Column(db.Boolean, default=False)
    user = db.relationship('User', back_populates='memberships')
    votes_received = db.relationship('FactorVote', backref='member', lazy=True)
    
    @property
    def name(self):
        """Restituisce il nome del membro"""
        return self.user.username if self.user else "Unknown"
    
    @property
    def base_score(self):
        """Restituisce il marriage_score dell'utente (base di partenza)"""
        return self.user.marriage_score if self.user else 0
    
    @property
    def votes_sum(self):
        """Somma tutti i voti ricevuti dai fattori"""
        return sum([v.score for v in self.votes_received]) if self.votes_received else 0
    
    @property
    def num_voters(self):
        """Conta quanti utenti hanno votato per questo membro"""
        if not self.votes_received:
            return 0
        unique_voters = set(v.voter_id for v in self.votes_received)
        return len(unique_voters)
    
    @property
    def calculated_total_score(self):
        """Calcola il punteggio totale: base_score + SOMMA dei voti ricevuti"""
        base = self.base_score
        if not self.votes_received:
            return base
        votes_sum = sum([v.score for v in self.votes_received])
        total = base + votes_sum
        return max(0, int(total))
    
    @property
    def user_color(self):
        """Restituisce il colore assegnato a questo utente per le chat"""
        colors = [
            '#FFD700',  
            '#C0C0C0',  
            '#CD7F32', 
            '#FF6B9D',  
            '#A569BD',  
            '#5DADE2',  
            '#52BE80',  
            '#F8B88B', 
        ]
        return colors[self.user_id % len(colors)]
    
    def get_voting_breakdown(self):
       
        breakdown = {}
        for vote in self.votes_received:
            if vote.factor_id not in breakdown:
                breakdown[vote.factor_id] = {
                    'factor_name': vote.factor.name if vote.factor else 'Unknown',
                    'votes': [],
                    'average': 0
                }
            breakdown[vote.factor_id]['votes'].append(vote.score)
        
        for factor_id, data in breakdown.items():
            if data['votes']:
                data['average'] = sum(data['votes']) / len(data['votes'])
        
        return breakdown

class PushSubscription(db.Model):
    
    __tablename__ = 'push_subscription'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subscription_info = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    
    user = db.relationship('User', backref=db.backref('push_subscriptions', lazy=True))
    
    def __repr__(self):
        return f'<PushSubscription user_id={self.user_id}>'
    
class StandardFactor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=False)
    default_weight = db.Column(db.Float, nullable=False, default=0)


class LeagueFactor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    league_id = db.Column(db.Integer, db.ForeignKey('league.id'), nullable=False)
    standard_factor_id = db.Column(db.Integer, db.ForeignKey('standard_factor.id'), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=False)
    
    __table_args__ = (db.UniqueConstraint('league_id', 'standard_factor_id', name='_league_factor_uc'),)

    league = db.relationship('League', backref=db.backref('active_standard_factors', lazy=True))
    standard_factor = db.relationship('StandardFactor')

class Factor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    league_id = db.Column(db.Integer, db.ForeignKey('league.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    weight = db.Column(db.Float, default=1.0)
    is_default = db.Column(db.Boolean, default=False)
    abilitato = db.Column(db.Boolean, default=True)
    gender = db.Column(db.String(20), default="Entrambi")  
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

def setup_default_factors(league_id):
    """
    Crea i link tra una lega e i fattori standard di default.
    Tutti i fattori standard sono attivati per default quando si crea una lega.
    """
    try:
        all_standard_factors = StandardFactor.query.all()
        
        for factor in all_standard_factors:
         
            existing_link = LeagueFactor.query.filter_by(
                league_id=league_id,
                standard_factor_id=factor.id
            ).first()
            
            if not existing_link:
                
                new_link = LeagueFactor(
                    league_id=league_id,
                    standard_factor_id=factor.id,
                    is_active=True  
                )
                db.session.add(new_link)
        
        db.session.commit()
        print(f"✅ Fattori standard collegati alla lega {league_id}")
        
    except Exception as e:
        db.session.rollback()
        print(f"Errore in setup_default_factors: {str(e)}")
        import traceback
        traceback.print_exc()


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
        client = MailtrapClient(token=os.getenv('MAILTRAP_TOKEN'))
        response = client.send(mail)
        return True
    except Exception as e:
        print(f"Errore invio email reset password: {e}")
        return False



@app.route('/league/<int:league_id>/leave', methods=['POST'])
def leave_league(league_id):
    """Lascia una lega e notifica l'owner"""
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        league = League.query.get_or_404(league_id)
        member = LeagueMember.query.filter_by(
            league_id=league_id, 
            user_id=session['user_id']
        ).first_or_404()
        
        if league.owner_id == session['user_id']:
            return jsonify({'error': 'Non puoi uscire dalla lega di cui sei admin!'}), 403
        
        user = User.query.get(session['user_id'])
        db.session.delete(member)
        db.session.commit()
        
        try:
            send_push_notification(
                user_id=league.owner_id,
                title=f"👋 {league.name}",
                body=f"{user.username} ha lasciato la lega",
                url=f"/league/{league.id}",
                tag=f"leave-{league.id}-{user.id}"
            )
        except Exception as notif_error:
            print(f"⚠️ Notifica non inviata: {notif_error}")
        
        flash(f'Sei uscito dalla lega {league.name}!', 'success')
        return jsonify({'status': 'success'})
    
    except Exception as e:
        db.session.rollback()
        print(f"❌ Errore in leave_league: {e}")
        return jsonify({'error': str(e)}), 500



@app.route('/league/<int:league_id>/delete_members', methods=['POST'])
def delete_league_members(league_id):
    """Elimina membri dalla lega, li mette in blacklist e li notifica"""
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        league = League.query.get_or_404(league_id)
        
        if league.owner_id != session['user_id']:
            return jsonify({
                'status': 'error', 
                'message': 'Solo il creatore può eliminare i membri'
            }), 403
        
        member_ids = request.json.get('member_ids', [])
        
        if not member_ids:
            return jsonify({
                'status': 'error', 
                'message': 'Nessun membro selezionato'
            }), 400
        
        eliminated_users = []
        eliminated_usernames = []
        
        for member_id in member_ids:
            member = LeagueMember.query.filter_by(
                id=member_id, 
                league_id=league_id
            ).first()
            
            if member and member.user_id != league.owner_id:
                user = User.query.get(member.user_id)
                
                
                # ELIMINA TUTTI I VOTI ASSOCIATI AL MEMBRO
                
                try:
                    votes_received = FactorVote.query.filter_by(
                        member_id=member.id
                    ).all()
                    for vote in votes_received:
                        db.session.delete(vote)
                    
                    
                    votes_given = FactorVote.query.filter_by(
                        user_id=member.user_id,
                        league_id=league_id
                    ).all()
                    for vote in votes_given:
                        db.session.delete(vote)
                    
                    print(f"🗑️ Eliminati {len(votes_received)} voti ricevuti e {len(votes_given)} voti dati per member {member.id}")
                
                except Exception as vote_error:
                    print(f"⚠️ Errore eliminazione voti per member {member.id}: {vote_error}")
                
                
                blacklisted = BlacklistedMember(
                    league_id=league_id, 
                    user_id=member.user_id
                )
                db.session.add(blacklisted)
                
                
                db.session.delete(member)
                
                eliminated_users.append(member.user_id)
                eliminated_usernames.append(user.username if user else "Unknown")
            
            elif member and member.user_id == league.owner_id:
                db.session.rollback()
                return jsonify({
                    'status': 'error', 
                    'message': 'Non puoi eliminare il creatore della lega'
                }), 403
        
        
        db.session.commit()
        print(f"✅ {len(eliminated_users)} membri rimossi dalla lega {league.id}")
        

        try:
            calculate_member_scores(league_id)
            print(f"Punteggi ricalcolati per lega {league.id}")
        except Exception as calc_error:
            print(f"⚠️ Errore calcolo punteggi: {calc_error}")
        
       
        for user_id in eliminated_users:
            if user_id == session.get('user_id'):
                session['expelled_from'] = league.name
        
        
        for user_id in eliminated_users:
            try:
                send_push_notification(
                    user_id=user_id,
                    title=f"{league.name}",
                    body="Sei stato rimosso dalla lega dall'amministratore",
                    url="/dashboard",
                    tag=f"kick-{league.id}-{user_id}"
                )
            except Exception as notif_error:
                print(f"Notifica non inviata: {notif_error}")
        
        if eliminated_usernames:
            try:
                remaining_members = LeagueMember.query.filter_by(league_id=league_id).all()
                kicked_names = ", ".join(eliminated_usernames[:3])
                if len(eliminated_usernames) > 3:
                    kicked_names += f" e altri {len(eliminated_usernames) - 3}"
                
                for remaining_member in remaining_members:
                    if remaining_member.user_id != league.owner_id:
                        try:
                            send_push_notification(
                                user_id=remaining_member.user_id,
                                title=f"{league.name}",
                                body=f"{kicked_names} è stato rimosso dalla lega",
                                url=f"/league/{league.id}",
                                tag=f"member-removed-{league.id}"
                            )
                        except:
                            pass
            except:
                pass
        
        return jsonify({
            'status': 'success', 
            'message': f'{len(member_ids)} membro/i eliminato/i',
            'eliminated_users': eliminated_users
        }), 200
    
    except Exception as e:
        db.session.rollback()
        print(f"Errore critico in delete_league_members: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': f'Errore: {str(e)}'
        }), 500


@app.route('/test-push')
def test_push():
    """Route per testare le notifiche push"""
    if 'user_id' not in session:
        return "Devi essere loggato!", 401
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    return f"""
    <h1>✅ Notifica inviata a {user.username}!</h1>
    <p>Controlla il browser per vedere la notifica.</p>
    <br>
    <a href="/dashboard">Torna alla Dashboard</a>
    """

@app.route('/test-push-all')
def test_push_all():

    if 'user_id' not in session:
        return "Devi essere loggato", 401
    
    user_id = session['user_id']
    
    notifications = [
        {
            'title': '💬 Test Chat',
            'body': 'Mario: Ciao! Come va?',
            'url': '/dashboard',
            'tag': 'test-chat'
        },
        {
            'title': 'Test Join',
            'body': 'Luigi si è unito alla lega!',
            'url': '/dashboard',
            'tag': 'test-join'
        },
        {
            'title': '👋 Test Leave',
            'body': 'Peach ha lasciato la lega',
            'url': '/dashboard',
            'tag': 'test-leave'
        },
        {
            'title': '⛔ Test Kick',
            'body': 'Sei stato rimosso dalla lega dall\'amministratore',
            'url': '/dashboard',
            'tag': 'test-kick'
        }
    ]
    
    for notif in notifications:
        send_push_notification(
            user_id=user_id,
            title=notif['title'],
            body=notif['body'],
            url=notif['url'],
            tag=notif['tag']
        )
       
        import time
        time.sleep(0.5)
    
    return f"""
    <h1>✅ {len(notifications)} notifiche inviate!</h1>
    <p>Dovresti ricevere 4 notifiche diverse:</p>
    <ul>
        <li>💬 Chat</li>
        <li>🎉 Join</li>
        <li>👋 Leave</li>
        <li>⛔ Kick</li>
    </ul>
    <br>
    <a href="/dashboard">Torna alla Dashboard</a>
    """




from flask import request, jsonify
import json


@app.route('/api/push-subscription', methods=['POST'])
def save_push_subscription():
    """Salva la subscription push del browser nel database"""
    if 'user_id' not in session:
        return jsonify({'error': 'Non autenticato'}), 401
    
    try:
        subscription_info = request.json
        user_id = session['user_id']
        
        subscription_json = json.dumps(subscription_info)
        
        existing = PushSubscription.query.filter_by(
            user_id=user_id,
            subscription_info=subscription_json
        ).first()
        
        if not existing:
            
            new_sub = PushSubscription(
                user_id=user_id,
                subscription_info=subscription_json,
                is_active=True
            )
            db.session.add(new_sub)
            db.session.commit()
            print(f"Subscription salvata per user {user_id}")
        else:
            print(f"ℹSubscription già esistente per user {user_id}")
        
        return jsonify({'success': True, 'message': 'Subscription salvata'})
    
    except Exception as e:
        print(f"Errore salvataggio subscription: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/league/<int:league_id>/manage_factors', methods=['GET'])
def manage_factors(league_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    league = League.query.get_or_404(league_id)
    if league.owner_id != session['user_id']:
        flash('Solo il proprietario può gestire i fattori.', 'danger')
        return redirect(url_for('dashboard'))
    all_factors = StandardFactor.query.order_by(StandardFactor.category, StandardFactor.name).all()
    active_factor_links = LeagueFactor.query.filter_by(league_id=league_id, is_active=True).all()
    active_factor_ids = {link.standard_factor_id for link in active_factor_links}
    
    return render_template('manage_factors.html', 
                           league=league, 
                           all_factors=all_factors,
                           active_factor_ids=active_factor_ids)

@app.route('/api/league/<int:league_id>/voting', methods=['GET'])
def get_voting(league_id):
    voting = Voting.query.filter_by(league_id=league_id).order_by(Voting.created_at.desc()).first()
    
    if voting:
        now = datetime.utcnow()
        is_active = now >= voting.start_time and now <= voting.end_time
        
        return jsonify({
            'id': voting.id,
            'league_id': voting.league_id,
            'start_time': voting.start_time.isoformat(),
            'end_time': voting.end_time.isoformat(),
            'is_active': is_active
        })
    
    return jsonify({'is_active': False})

@app.route('/api/league/<int:league_id>/voting', methods=['POST'])
def create_voting(league_id):
    
    data = request.json
    start_time = datetime.fromisoformat(data.get('start_time', '').replace('Z', '+00:00'))
    end_time = datetime.fromisoformat(data.get('end_time', '').replace('Z', '+00:00'))
    
    if start_time >= end_time:
        return jsonify({'success': False, 'message': 'Data fine deve essere dopo data inizio'})
    
    voting = Voting(
        league_id=league_id,
        start_time=start_time,
        end_time=end_time
    )
    
    db.session.add(voting)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'start_time': start_time.isoformat(),
        'end_time': end_time.isoformat()
    })

@app.route('/league/<int:league_id>/toggle_factor/<int:factor_id>', methods=['POST'])
def toggle_factor(league_id, factor_id):
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Non autorizzato'}), 401
    
    try:
        league = League.query.get_or_404(league_id)
        if league.owner_id != session['user_id']:
            return jsonify({'status': 'error', 'message': 'Solo il proprietario può modificare.'}), 403

        
        link = LeagueFactor.query.filter_by(
            league_id=league_id, 
            standard_factor_id=factor_id
        ).first()

        if link:
            
            link.is_active = not link.is_active
            db.session.commit()
            message = f"Fattore {'attivato' if link.is_active else 'disattivato'}"
            is_active = link.is_active
        else:
            
            new_link = LeagueFactor(
                league_id=league_id, 
                standard_factor_id=factor_id, 
                is_active=True
            )
            db.session.add(new_link)
            db.session.commit()
            message = 'Fattore attivato'
            is_active = True
        
        return jsonify({
            'status': 'success', 
            'message': message, 
            'is_active': is_active
        })
    
    except Exception as e:
        db.session.rollback()
        print(f"ERRORE in toggle_factor: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error', 
            'message': f'Errore: {str(e)}'
        }), 500

@app.route('/league/<int:league_id>/toggle_custom_factor/<int:factor_id>', methods=['POST'])
def toggle_custom_factor(league_id, factor_id):
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Non autorizzato'}), 401
    
    try:
        league = League.query.get_or_404(league_id)
        if league.owner_id != session['user_id']:
            return jsonify({'status': 'error', 'message': 'Solo il proprietario può modificare.'}), 403

        
        factor = Factor.query.filter_by(id=factor_id, league_id=league_id).first()
        
        if not factor:
            return jsonify({'status': 'error', 'message': 'Fattore non trovato'}), 404
        
        
        factor.abilitato = not factor.abilitato
        db.session.commit()
        
        message = f"Fattore {'abilitato' if factor.abilitato else 'disabilitato'}"
        
        return jsonify({
            'status': 'success', 
            'message': message, 
            'abilitato': factor.abilitato
        })
    
    except Exception as e:
        db.session.rollback()
        print(f"ERRORE in toggle_custom_factor: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error', 
            'message': f'Errore: {str(e)}'
        }), 500

from datetime import datetime, timedelta

@app.route('/api/voting-status', methods=['GET'])
def get_voting_status():
    
    voting_active = request.args.get('voting_active', 'false') == 'true'
    if voting_active:
        end_time = request.args.get('end_time')
        return jsonify({
            'active': True,
            'end_time': end_time
        })
    return jsonify({'active': False})

@app.route('/api/start-voting', methods=['POST'])
def start_voting():
    
    duration_minutes = request.json.get('duration', 5)  # default 5 minuti
    end_time = datetime.now() + timedelta(minutes=duration_minutes)
    session['voting_active'] = True
    session['voting_end_time'] = end_time.isoformat()
    
    return jsonify({
        'success': True,
        'end_time': end_time.isoformat()
    })

@app.route('/api/stop-voting', methods=['POST'])
def stop_voting():
    
    session['voting_active'] = False
    return jsonify({'success': True})

    
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
    
        username = request.form.get("username")
        email = request.form.get("email")
        user = User.query.filter_by(username=username, email=email).first()
        
        if user:
            token = secrets.token_urlsafe(32)
            user.reset_token = token
            user.reset_token_expiry = datetime.now() + timedelta(hours=1)  # Valido 1 ora
            db.session.commit()
            reset_url = url_for('reset_password', token=token, _external=True)
            if send_reset_password_email(user.email, user.username, reset_url):
                flash("Email di reimpostazione inviata! Controlla la tua casella di posta.", "success")
            else:
                flash("Errore nell'invio dell'email. Riprova più tardi.", "danger")
                return redirect(url_for('forgot_password'))
        else:
            flash("Se username ed email corrispondono, riceverai un'email di reimpostazione.", "info")
        
        return redirect(url_for('login'))
    
    return render_template("forgot_password.html")



@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()

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
        
        user.set_password(new_password)
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()
        
        flash("Password reimpostata con successo! Ora puoi effettuare il login.", "success")
        return redirect(url_for('login'))
    
    return render_template("reset_password.html", token=token)
@app.route('/.well-known/assetlinks.json')
def assetlinks():
    return send_from_directory('static/.well-known', 'assetlinks.json',
                             mimetype='application/json')
@app.route('/sw.js')
def service_worker():
    response = send_from_directory('static', 'sw.js', 
                                  mimetype='application/javascript')
    response.headers['Cache-Control'] = 'no-cache'
    return response

@app.route('/manifest.json')
def manifest():
    
    return send_from_directory('static', 'manifest.json', 
                             mimetype='application/manifest+json')

@app.route("/")
def home():
    print("=" * 50)
    print("DEBUGGING HOMEPAGE - INIZIO")
    print(f"Session keys: {list(session.keys())}")
    print(f"user_id: {session.get('user_id')}")
    print(f"avatar: {session.get('avatar')}")
    print("=" * 50)
    
    search_query = request.args.get('search', '').strip()
    
    if search_query:
        leagues = League.query.join(User, League.owner_id == User.id).filter(
            db.or_(
                League.name.ilike(f'%{search_query}%'),
                User.username.ilike(f'%{search_query}%')
            ),
            League.is_active == True
        ).all()
    else:
        leagues = League.query.filter_by(is_active=True).all()
    
    print(f"Leghe trovate: {len(leagues)}")
    
    print("=" * 50)
    print("DEBUGGING HOMEPAGE - FINE")
    print(f"Session keys prima del render: {list(session.keys())}")
    print("=" * 50)
    
    return render_template("index.html", leagues=leagues, search_query=search_query)

@app.route('/questionnaire', methods=['GET', 'POST'])
def questionnaire():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    
    if user.questionnaire_completed:
        return redirect(url_for('dashboard'))
    
    if request.method == "POST":
        try:
            
            gender = request.form.get('gender', 'Altro')
            age = request.form.get('age', 18)
            employment_status = request.form.get('employment_status', '')
            longest_relationship = request.form.get('longest_relationship', 0)
            num_relationships = request.form.get('num_relationships', 0)
            current_status = request.form.get('current_status', '')
            has_cheated = request.form.get('has_cheated') == 'yes'
            would_cheat = request.form.get('would_cheat', '')
            marriage_idea = request.form.get('marriage_idea', '')
            wants_children = request.form.get('wants_children', 0)
            living_together = request.form.get('living_together', '')
            commitment_level = request.form.get('commitment_level', 5)
            
            age = int(age) if age else 18
            longest_relationship = int(longest_relationship) if longest_relationship else 0
            num_relationships = int(num_relationships) if num_relationships else 0
            wants_children = int(wants_children) if wants_children else 0
            commitment_level = int(commitment_level) if commitment_level else 5
            
            
            score = 0
            
           
            if gender == 'Maschio':
                score += 5
            elif gender == 'Femmina':
                score += 5
            
            
            if 25 <= age <= 35:
                score += 30
            elif 22 <= age < 25 or 35 < age <= 40:
                score += 20
            else:
                score += 10
            
            
            if employment_status in ['Impiegato', 'Libero professionista', 'Imprenditore']:
                score += 25
            elif employment_status in ['Studente', 'Disoccupato']:
                score += 5
            
            
            score += min(longest_relationship * 2, 50)
            
            
            if 2 <= num_relationships <= 5:
                score += 20
            elif num_relationships == 1:
                score += 10
            else:
                score += 5
            
            
            if current_status == 'Fidanzato/a':
                score += 40
            elif current_status == 'Convivente':
                score += 50
            elif current_status == 'Single':
                score += 10
            elif current_status == 'Sposato/a':
                score += 100
            
           
            if has_cheated:
                score -= 30
            else:
                score += 20
            
            
            if would_cheat == 'Mai':
                score += 30
            elif would_cheat == 'Forse':
                score -= 10
            elif would_cheat == 'Dipende':
                score -= 20
            
            
            if wants_children == 0:
                score -= 20
            elif wants_children == 1:
                score += 10
            elif wants_children == 2:
                score += 30
            elif wants_children >= 3:
                score += 50
            
            if living_together == 'Sì':
                score += 40
            elif living_together == 'Non ancora':
                score += 20
            else:
                score -= 10
            
            score += commitment_level * 5
            user.gender = gender
            user.age = age
            user.employment_status = employment_status
            user.longest_relationship = longest_relationship
            user.num_relationships = num_relationships
            user.current_status = current_status
            user.has_cheated = has_cheated
            user.would_cheat = would_cheat
            user.marriage_idea = marriage_idea
            user.wants_children = wants_children
            user.living_together = living_together
            user.commitment_level = commitment_level
            user.marriage_score = max(0, score)
            user.questionnaire_completed = True
            db.session.commit()
            flash(f"Grazie per aver completato il questionario! Il tuo punteggio di propensione al matrimonio è: {score}", "success")
            return redirect(url_for('dashboard'))
        
        except Exception as e:
            db.session.rollback()
            flash(f"Errore: {str(e)}", "danger")
            return redirect(url_for('questionnaire'))
    
    return render_template('questionnaire.html')



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
            client = MailtrapClient(token=os.getenv('MAILTRAP_TOKEN'))
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
    

@app.route('/league/<int:league_id>/blacklist', methods=['GET', 'POST'])
def manage_blacklist(league_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    league = League.query.get_or_404(league_id)
    
    if league.owner_id != session['user_id']:
        flash('Solo il creatore può gestire la blacklist', 'warning')
        return redirect(url_for('league_detail', league_id=league_id))
    
    if request.method == 'POST':
        user_id = request.form.get('user_id', type=int)
        action = request.form.get('action')
        
        blacklisted = BlacklistedMember.query.filter_by(
            league_id=league_id,
            user_id=user_id
        ).first()
        
        if action == 'unban' and blacklisted:
            user = User.query.get(user_id)
            db.session.delete(blacklisted)
            db.session.commit()
            flash(f'Utente {user.username} sbannato con successo! Può rientrare nella lega.', 'success')
            
           
            return redirect(url_for('league_detail', league_id=league_id))
        
        return redirect(url_for('manage_blacklist', league_id=league_id))
    
    blacklisted_users = db.session.query(BlacklistedMember, User).join(
        User, BlacklistedMember.user_id == User.id
    ).filter(BlacklistedMember.league_id == league_id).all()
    
    return render_template('blacklist.html', 
                         league=league, 
                         blacklisted_users=blacklisted_users)


@app.route('/league/<league_code>/chat', methods=['GET'])
def get_chat_messages(league_code):
    """Recupera tutti i messaggi della chat di una lega (versione semplificata senza allegati)."""
    if 'user_id' not in session:
        return jsonify({'error': 'Non autenticato'}), 401
    
    user_id = session['user_id']
    league = League.query.filter_by(code=league_code).first_or_404()
    is_member = LeagueMember.query.filter_by(league_id=league.id, user_id=user_id).first()
    if not is_member:
        return jsonify({'error': 'Non sei membro di questa lega'}), 403
    
    
    messages = ChatMessage.query.options(
        db.joinedload(ChatMessage.user)
    ).filter(
        ChatMessage.league_id == league.id
    ).order_by(
        ChatMessage.created_at.asc()
    ).all()
    result = [
        {
            'id': msg.id,
            'user': msg.user.username,
            'message': msg.message or '',
            'created_at': msg.created_at.isoformat()
          
        } for msg in messages
    ]
    
    return jsonify(result)


@app.route('/league/<league_code>/chat', methods=['POST'])
def send_chat_message(league_code):
    """Invia un nuovo messaggio con eventuali allegati e notifiche push"""
    if 'user_id' not in session:
        return jsonify({'error': 'Non autenticato'}), 401
    
    league = League.query.filter_by(code=league_code).first_or_404()
    is_blacklisted = BlacklistedMember.query.filter_by(
        league_id=league.id,
        user_id=session['user_id']
    ).first()
    
    if is_blacklisted:
        return jsonify({'error': 'Sei stato espulso da questa lega e non puoi chattare'}), 403
    
    is_member = LeagueMember.query.filter_by(
        league_id=league.id,
        user_id=session['user_id']
    ).first()
    
    if not is_member:
        return jsonify({'error': 'Non sei membro di questa lega'}), 403
    
    message_text = request.form.get('message', '').strip()
    
    
    if not message_text and not request.files:
        return jsonify({'error': 'Messaggio o file richiesto'}), 400
    
   
    new_message = ChatMessage(
        league_id=league.id,
        user_id=session['user_id'],
        message=message_text if message_text else None
    )
    db.session.add(new_message)
    db.session.flush()  
    
    
    attachments_data = []
    for key in request.files:
        file = request.files[key]
        
        if file and file.filename:
            
            if not allowed_file(file.filename):
                db.session.rollback()
                return jsonify({'error': f'Tipo file non permesso: {file.filename}'}), 400

            original_filename = secure_filename(file.filename)
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
            ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
            unique_filename = f"{timestamp}_{session['user_id']}.{ext}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            
            try:
                
                file.save(filepath)
                file_size = os.path.getsize(filepath)
                
                
                attachments_data.append({
                    'name': unique_filename,
                    'original_name': original_filename,
                    'size': file_size
                })
            
            except Exception as e:
                db.session.rollback()
                
                if os.path.exists(filepath):
                    os.remove(filepath)
                return jsonify({'error': f'Errore nel salvataggio: {str(e)}'}), 500
    
    try:
        db.session.commit()
        sender = User.query.get(session['user_id'])
        all_members = LeagueMember.query.filter_by(league_id=league.id).all()
        
       
        if message_text:
            notification_body = f"{sender.username}: {message_text[:50]}"
            if len(message_text) > 50:
                notification_body += "..."
        elif attachments_data:
            file_count = len(attachments_data)
            notification_body = f"{sender.username} ha inviato {file_count} file"
        else:
            notification_body = f"{sender.username} ha inviato un messaggio"
        
       
        for member in all_members:
            if member.user_id != session['user_id']:
                try:
                    send_push_notification(
                        user_id=member.user_id,
                        title=f"💬 {league.name}",
                        body=notification_body,
                        url=f"/league/{league.id}",
                        tag=f"chat-{league.id}-{new_message.id}"
                    )
                except Exception as e:
                    print(f"Errore invio notifica a user {member.user_id}: {e}")
        
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
    
    
    if message.user_id != session['user_id'] and league.owner_id != session['user_id']:
        return jsonify({'error': 'Non autorizzato'}), 403
    
    
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
        CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
        token = request.json.get("token")
        idinfo = id_token.verify_oauth2_token(
            token, 
            google_requests.Request(), 
            CLIENT_ID 
        )
        
        if idinfo['aud'] != CLIENT_ID:
            raise ValueError('Token non valido')
        
        email = idinfo.get('email')
        if not email:
            return jsonify({
                "success": False, 
                "message": "Email non fornita da Google"
            }), 400
        
        avatar_url = idinfo.get('picture', 'default.png')
        username = email.split("@")[0]
        
        
        user = User.query.filter_by(email=email).first()
        if user:
            if user.provider != "google":
                return jsonify({
                    "success": False, 
                    "message": "Questa email è già registrata con un account locale"
                }), 400
            
            if user.avatar != avatar_url:
                user.avatar = avatar_url
                db.session.commit()
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

        msg = ChatMessage(
            league_id=league_id,
            user_id=session['user_id'],
            message=msg_text
        )
        db.session.add(msg)
        db.session.commit()
        return jsonify({"success": True, "message_id": msg.id})

    else:  
        messages = ChatMessage.query.filter_by(league_id=league_id).order_by(ChatMessage.created_at.desc()).limit(50).all()
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

@app.route("/dashboard")
def dashboard():
    if 'user_id' not in session:
        flash("Effettua prima il login", "warning")
        return redirect(url_for("login"))
    
    user = User.query.get(session['user_id'])
    if not user.questionnaire_completed:
        return redirect(url_for("questionnaire"))

    if 'expelled_from' in session:
        league_name = session.pop('expelled_from')
        flash(f"Sei stato espulso dalla lega '{league_name}' dall'amministratore", "danger")
    
    owned_leagues = League.query.filter_by(owner_id=user.id).all()
    memberships = LeagueMember.query.filter_by(user_id=user.id).all()
    joined_leagues = [m.league for m in memberships]
    
    return render_template("dashboard.html", 
                         user=user, 
                         owned_leagues=owned_leagues,
                         joined_leagues=joined_leagues,
                         marriage_score=user.marriage_score)

@app.route("/profilo", methods=["GET", "POST"])
def profilo():
    if 'user_id' not in session:
        flash("Effettua prima il login", "warning")
        return redirect(url_for("login"))
    
    user = User.query.get(session['user_id'])
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

            if user.avatar and user.avatar != "default.png" and not user.avatar.startswith("http"):
                old_path = os.path.join("static", user.avatar)
                if os.path.exists(old_path):
                    os.remove(old_path)


            user.avatar = f"uploads/avatars/{unique_filename}"
            user.updated_at = datetime.utcnow()
            
            db.session.commit()
            session["avatar"] = user.avatar
            session["avatar_updated"] = int(time.time())  # ← AGGIUNGI QUESTO
            
            flash("Avatar aggiornato con successo!", "success")
            return redirect(url_for("profilo"))
        else:
            flash("Formato file non valido (usa PNG, JPG, JPEG, GIF o WEBP)", "danger")
            return redirect(url_for("profilo"))
    
    return render_template("profilo.html", user=user)


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
        
        
        creator_member = LeagueMember(
            league_id=league.id,
            user_id=session['user_id'],
            avatar=session.get('avatar', 'default.png')
        )
        db.session.add(creator_member)
        
        
        setup_default_factors(league.id)
        db.session.commit()
        
        flash(f"Lega '{name}' creata con successo! Codice: {league.code}", "success")
        return redirect(url_for("league_detail", league_id=league.id))
    
    return render_template("create_league.html")


@app.route("/league/<int:league_id>", methods=['GET'])
def league_detail(league_id):
    if 'user_id' not in session:
        flash("Effettua prima il login", "warning")
        return redirect(url_for("login"))
    
    league = db.session.get(League, league_id)
    if not league:
        flash("Lega non trovata", "danger")
        return redirect(url_for("dashboard"))
    
    
    is_blacklisted = BlacklistedMember.query.filter_by(
        league_id=league_id,
        user_id=session['user_id']
    ).first()
    
    if is_blacklisted:
        flash(f"Sei stato espulso dalla lega '{league.name}' dall'amministratore", "danger")
        return redirect(url_for("dashboard"))
    
    
    is_member = LeagueMember.query.filter_by(
        league_id=league_id, 
        user_id=session['user_id']
    ).first()
    
    is_owner = (league.owner_id == session['user_id'])
    
   
    if not is_member and not is_owner:
        flash("Non sei membro di questa lega", "warning")
        return redirect(url_for("dashboard"))
    
    
    members = LeagueMember.query.filter_by(league_id=league_id).all()
    members_sorted = sorted(
        members,
        key=lambda m: m.calculated_total_score,
        reverse=True
    )
    
    
    custom_factors = Factor.query.filter_by(league_id=league_id).all()
    active_links = LeagueFactor.query.filter_by(league_id=league_id, is_active=True).all()
    active_standard_factor_ids = {link.standard_factor_id for link in active_links}
    
    all_standard_factors_for_owner = []
    active_standard_factors_for_member = []
    
    if is_owner:
        
        all_standard_factors_for_owner = StandardFactor.query.order_by(StandardFactor.category, StandardFactor.name).all()
    else:
        
        if active_standard_factor_ids:
            active_standard_factors_for_member = StandardFactor.query.filter(StandardFactor.id.in_(active_standard_factor_ids)).all()
    voting = Voting.query.filter_by(league_id=league_id).order_by(Voting.created_at.desc()).first()
    
    return render_template(
        "league_detail.html", 
        league=league, 
        members=members_sorted,
        custom_factors=custom_factors,
        is_member=is_member is not None, 
        is_owner=is_owner,
        all_standard_factors=all_standard_factors_for_owner,
        active_standard_factor_ids=active_standard_factor_ids,
        active_standard_factors=active_standard_factors_for_member,
        voting=voting,
    )

@app.route('/league/<int:league_id>/stats')
def league_stats(league_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    league = League.query.get_or_404(league_id)
    members = LeagueMember.query.filter_by(league_id=league_id).all()
    members_sorted = sorted(
        members,
        key=lambda m: m.calculated_total_score,
        reverse=True
    )
    scores = [m.calculated_total_score for m in members_sorted]
    stats = {
        'totale_voti': len(members),
        'membro_piu_votato': members_sorted[0].name if members_sorted else "Nessuno",
        'membro_meno_votato': members_sorted[-1].name if members_sorted else "Nessuno",
        'voto_medio': round(sum(scores) / len(scores), 2) if scores else 0,
        'disparita': round(max(scores) - min(scores), 2) if scores else 0,
    }
    
    
    funny_phrases = []
    
    if members_sorted:
        primo = members_sorted[0]
        ultimo = members_sorted[-1]
        primo_user = User.query.get(primo.user_id)
        ultimo_user = User.query.get(ultimo.user_id)
        
        gender_primo = primo_user.gender if primo_user else "Altro"
        gender_ultimo = ultimo_user.gender if ultimo_user else "Altro"
        
        
        if gender_primo == "Femmina":
            funny_phrases.extend([
                f"👑 {primo.name} ha la corona! La signora perfetta! 💍",
                f"💄 {primo.name} sarà la prima all'altare... prepara l'abito! 👰",
            ])
        elif gender_primo == "Maschio":
            funny_phrases.extend([
                f"🤵 {primo.name} è il prescelto! Prepara lo smoking! 💍",
                f"💪 {primo.name} ha i coglioni quadrati...e le tasche vuote",
            ])
        else:
            funny_phrases.extend([
                f"👑 {primo.name} vincitore o perdente?",
                f"⛓️‍💥 {primo.name} presto in galera",
            ])
        
        
        if gender_ultimo == "Femmina":
            funny_phrases.extend([
                f" {ultimo.name} a gambe aperte,sempre!"
                f" {ultimo.name} prenota un viaggetto a Lourdes,fidati!",
            ])
        elif gender_ultimo == "Maschio":
            funny_phrases.extend([
                f" {ultimo.name} spargerà seme per il mondo...",
                f" {ultimo.name} ce l'hai piccolo, confessa!",
            ])
        else:
            funny_phrases.extend([
                f" {ultimo.name} usa il preservativo, sempre!",
                f" {ultimo.name}, eh marpione!",
            ])
    
    if not funny_phrases:
        funny_phrases = [
            f" Disparità di {stats['disparita']}",
            f" Voto medio {stats['voto_medio']}",
        ]
    
    funny_phrase = random.choice(funny_phrases)
    
   
    pronostici_list = []
    
    if len(members_sorted) >= 2:
        primo = members_sorted[0]
        primo_user = User.query.get(primo.user_id)
        gender_primo = primo_user.gender if primo_user else "Altro"
        
        total_score = sum(scores)
        percentuale = round((primo.calculated_total_score / total_score * 100), 1) if total_score > 0 else 0
        
        
        if gender_primo == "Femmina":
            pronostici_list = [
                f" {primo.name} ha il {percentuale}% di diventare la signora X! ",
                f" Entro 2 anni {primo.name} sarà all'altare! ",
                f" {primo.name} finalmente, ha smesso di fare la troi@!! ",
                f" Proponi a {primo.name}... fidati! ",
                f" {primo.name} è la regina! Prepara lo champagne! ",
            ]
        
        
        elif gender_primo == "Maschio":
            pronostici_list = [
                f""
                f" {primo.name} ha il {percentuale}% di diventare uno sposo!",
                f" Entro 2 anni {primo.name} correrà all'altare!",
                f" {primo.name} ha soldi, classe, stile! Le donne lo adorano!",
                f" Qualche donna lo prenderà al volo!",
                f" Il portafoglio di {primo.name} è un magnete!",
            ]
        
       
        else:
            pronostici_list = [
                f"{primo.name} ha il {percentuale}% di vincere!",
                f"{primo.name} troverà l'amore perfetto!",
                f"Il matrimonio è vicino per {primo.name}!",
            ]

        pronostico = random.choice(pronostici_list)
    else:
        pronostico = "Non ci sono abbastanza dati per il pronostico!"
    
   
    member_names = [m.name for m in members_sorted]
    total_scores = scores
    
    return render_template('league_stats.html', 
                         league=league, 
                         stats=stats,
                         funny_phrase=funny_phrase,
                         pronostico=pronostico,
                         members=members_sorted,
                         member_names=member_names,
                         total_scores=total_scores)


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
        
       
        blacklisted = BlacklistedMember.query.filter_by(
            league_id=league.id,
            user_id=session['user_id']
        ).first()
        
        if blacklisted:
            flash("Sei stato rimosso da questa lega e non puoi rientrare", "danger")
            return redirect(url_for("dashboard"))
        
        existing_member = LeagueMember.query.filter_by(
            league_id=league.id, 
            user_id=session['user_id']
        ).first()
        
        if existing_member:
            flash("Sei già membro di questa lega", "warning")
            return redirect(url_for("league_detail", league_id=league.id))
        
        if league.password_hash:
            if not password:
                flash("Questa lega richiede una password", "danger")
                return redirect(url_for("join_league"))
            
            if not league.check_password(password):
                flash("Password errata. Contatta l'amministratore della lega.", "danger")
                return redirect(url_for("join_league"))
        
        user = User.query.get(session['user_id'])
        member = LeagueMember(
            league_id=league.id,
            user_id=user.id,
            avatar=user.avatar
        )
        db.session.add(member)
        db.session.commit()
        existing_members = LeagueMember.query.filter_by(league_id=league.id).all()

        for existing_member in existing_members:
            if existing_member.user_id != user.id:
                try:
                    send_push_notification(
                        user_id=existing_member.user_id,
                        title=f"🎉 {league.name}",
                        body=f"{user.username} si è unito alla lega!",
                        url=f"/league/{league.id}",
                        tag=f"join-{league.id}-{user.id}"
                    )
                except Exception as e:
                    print(f"Errore invio notifica a user {existing_member.user_id}: {e}")
        if league.owner_id != user.id:
            try:
                send_push_notification(
                    user_id=league.owner_id,
                    title=f"👑 {league.name}",
                    body=f"Nuovo membro: {user.username} è entrato nella tua lega!",
                    url=f"/league/{league.id}",
                    tag=f"join-owner-{league.id}-{user.id}"
                )
            except Exception as e:
                print(f"Errore invio notifica all'owner {league.owner_id}: {e}")
        
        flash(f"Sei entrato nella lega '{league.name}'!", "success")
        return redirect(url_for("league_detail", league_id=league.id))
    
    
    leagues = League.query.filter_by(is_active=True).all()
    return render_template("join_league.html", leagues=leagues)

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
        return jsonify({"error": "Solo gli admin possono aggiungere i fattori!"}), 403
    name = request.form.get("name")
    description = request.form.get("description")
    weight = request.form.get("weight", 1.0)
    gender = request.form.get("gender", "Entrambi")  
    
    factor = Factor(
        league_id=league_id,
        name=name,
        description=description,
        weight=float(weight),
        gender=gender 
    )
    db.session.add(factor)
    db.session.commit()
    flash(f"Fattore '{name}' aggiunto (visibile a: {gender})", "success")
    return redirect(url_for("league_detail", league_id=league_id))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads', 'avatars')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  
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
    
    
    is_blacklisted = BlacklistedMember.query.filter_by(
        league_id=league_id,
        user_id=session['user_id']
    ).first()
    
    if is_blacklisted:
        flash(f"Sei stato espulso dalla lega '{league.name}' e non puoi più votare", "danger")
        return redirect(url_for("dashboard"))
    

    is_member = LeagueMember.query.filter_by(
        league_id=league_id, 
        user_id=session['user_id']
    ).first()
    
    if not is_member:
        flash("Non sei membro di questa lega", "warning")
        return redirect(url_for("dashboard"))
    
    members = LeagueMember.query.filter_by(league_id=league_id, is_competing=True).all()
    
  
    user_gender = User.query.get(session['user_id']).gender
    factors = Factor.query.filter_by(league_id=league_id).filter(
        db.or_(
            Factor.gender == "Entrambi",
            Factor.gender == user_gender
        )
    ).all()

    active_links = LeagueFactor.query.filter_by(league_id=league_id, is_active=True).all()
    active_standard_factor_ids = {link.standard_factor_id for link in active_links}
    active_standard_factors = StandardFactor.query.filter(StandardFactor.id.in_(active_standard_factor_ids)).all() if active_standard_factor_ids else []

    if request.method == "POST":
        try:
            for member in members:
                if member.user_id == session['user_id']:
                    continue               
                user_voted = User.query.get(member.user_id)
                base_score = user_voted.marriage_score if user_voted else 0
                member_total_score = base_score
                for factor in factors:
                    score_key = f"score_{member.id}_{factor.id}"
                    score = request.form.get(score_key)
                    
                    if score:
                        score_value = float(score)
                        existing_vote = FactorVote.query.filter_by(
                            factor_id=factor.id,
                            member_id=member.id,
                            voter_id=session['user_id']
                        ).first()
                        
                        if not existing_vote:
                            member_total_score += score_value
                            new_vote = FactorVote(
                                factor_id=factor.id,
                                member_id=member.id,
                                voter_id=session['user_id'],
                                score=score_value
                            )
                            db.session.add(new_vote)
                member_total_score = max(0, member_total_score)
                member.total_score = int(member_total_score)
            
            db.session.commit()
            calculate_member_scores(league_id)
            flash("Voti registrati con successo! Base: marriage_score + bonus/malus dai fattori", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Errore durante la registrazione dei voti: {str(e)}", "danger")
        
        return redirect(url_for("league_detail", league_id=league_id))
    
    existing_votes = FactorVote.query.filter_by(voter_id=session['user_id']).all()
    voted_pairs = set((vote.member_id, vote.factor_id) for vote in existing_votes)
    filtered_members = [m for m in members if m.user_id != session['user_id']]
    member_scores = {}
    for member in filtered_members:
        user = User.query.get(member.user_id)
        member_scores[member.id] = user.marriage_score if user else 0
    
    return render_template("vote.html", 
                         league=league, 
                         members=filtered_members, 
                         factors=factors,
                         active_standard_factors=active_standard_factors,
                         voted_pairs=voted_pairs,
                         member_scores=member_scores)



@app.route("/privacy")
def privacy_policy():
    return render_template("privacy_policy.html")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
