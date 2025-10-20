import os
from app import app, db

# Elimina il database se esiste
db_path = 'fantamatrimonio.db'
if os.path.exists(db_path):
    os.remove(db_path)
    print(f"Database '{db_path}' eliminato")

# Ricrea tutte le tabelle
with app.app_context():
    db.create_all()
    print("Database ricreato con successo con tutte le colonne!")