from app import app, db, PushSubscription

with app.app_context():
    
    deleted = PushSubscription.query.delete()
    db.session.commit()
    