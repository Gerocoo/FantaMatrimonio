from app import app, db
from sqlalchemy import text

with app.app_context():
    try:
        # Prova ad aggiungere username
        db.session.execute(text('ALTER TABLE league_chat_message ADD COLUMN username VARCHAR(50)'))
        print("✅ Colonna username aggiunta")
    except:
        print("⚠️ Colonna username già esistente")
    
    try:
        # Prova ad aggiungere is_system
        db.session.execute(text('ALTER TABLE league_chat_message ADD COLUMN is_system BOOLEAN DEFAULT 0'))
        print("✅ Colonna is_system aggiunta")
    except:
        print("⚠️ Colonna is_system già esistente")
    
    db.session.commit()
    print("🎉 Fatto!")