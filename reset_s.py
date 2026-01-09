from app import app, db, PushSubscription

with app.app_context():
    
    deleted = PushSubscription.query.delete()
    db.session.commit()
    print(f"🗑️ Cancellate {deleted} subscription vecchie")
    print("✅ Database pulito! Ora ricarica il browser e registra la nuova subscription.")