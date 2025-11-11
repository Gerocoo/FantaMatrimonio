from app import app, db, LeagueMember, User

with app.app_context():
    # Trova membri senza utente
    all_members = LeagueMember.query.all()
    orphans = []
    
    for member in all_members:
        user = User.query.get(member.user_id)
        if not user:
            orphans.append(member)
            print(f"❌ Membro orfano trovato: ID {member.id}, user_id {member.user_id}")
    
    if orphans:
        print(f"\n🗑️ Trovati {len(orphans)} membri orfani")
        risposta = input("Vuoi eliminarli? (sì/no): ")
        
        if risposta.lower() in ['sì', 'si', 's', 'y', 'yes']:
            for orphan in orphans:
                db.session.delete(orphan)
            db.session.commit()
            print(f"✅ Eliminati {len(orphans)} membri orfani")
        else:
            print("❌ Operazione annullata")
    else:
        print("✅ Nessun membro orfano trovato!")
