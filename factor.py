# seed_factors.py
"""
Script per popolare il database con i fattori standard di FantaMatrimonio.
ATTENZIONE: Cancella TUTTI i fattori standard vecchi e li sostituisce con i nuovi!

Uso: python seed_factors.py
"""

try:
    from app import app, db, StandardFactor, LeagueFactor, League
except ImportError as e:
    print("--- ERRORE CRITICO ---")
    print(f"Impossibile importare da 'app.py': {e}")
    print("\nControlla quanto segue:")
    print("1. Questo script ('seed_factors.py') si trova nella STESSA cartella del tuo file 'app.py'.")
    print("2. Il tuo file 'app.py' contiene le definizioni di 'app', 'db', 'StandardFactor', 'LeagueFactor', 'League'.")
    print("3. Non ci sono errori di sintassi nel tuo file 'app.py'.")
    import sys
    sys.exit(1)


standard_factors_data = [
    # --- Categoria: Fisico ---
    {'name': 'Altezza', 'description': 'Da 150cm a 200cm+', 'category': 'Fisico', 'default_weight': 5},
    {'name': 'Fisicità attraente', 'description': 'Livello di attrazione fisica generale', 'category': 'Fisico', 'default_weight': 15},
    {'name': 'Dotazione', 'description': 'Attributi fisici maschili', 'category': 'Fisico', 'default_weight': 10},
    {'name': 'Seno', 'description': 'Attributi fisici femminili', 'category': 'Fisico', 'default_weight': 10},
    {'name': 'Forma fisica', 'description': 'Muscolatura e tono generale', 'category': 'Fisico', 'default_weight': 15},

    # --- Categoria: Economico ---
    {'name': 'Imprenditore/Lavoro autonomo', 'description': 'Possiede un\'azienda o lavora in proprio', 'category': 'Economico', 'default_weight': 25},
    {'name': 'Posto fisso statale', 'description': 'Impiego pubblico stabile', 'category': 'Economico', 'default_weight': 20},
    {'name': 'Lavoro privato stabile', 'description': 'Contratto indeterminato nel privato', 'category': 'Economico', 'default_weight': 15},
    {'name': 'Abile risparmiatore', 'description': 'Sa gestire bene le finanze personali', 'category': 'Economico', 'default_weight': 20},
    {'name': 'Taccagno', 'description': 'Eccessivamente parco con i soldi', 'category': 'Economico', 'default_weight': -15},
    {'name': 'Spendaccione', 'description': 'Spende in modo incontrollato', 'category': 'Economico', 'default_weight': -10},

    # --- Categoria: Sessuale ---
    {'name': 'Esperienza a letto', 'description': 'Pratico e consapevole sessualmente', 'category': 'Sessuale', 'default_weight': 20},
    {'name': 'Passionato/a', 'description': 'Molto focoso/a e intraprendente', 'category': 'Sessuale', 'default_weight': 25},
    {'name': 'Frigido/a', 'description': 'Poco interessato al sesso', 'category': 'Sessuale', 'default_weight': -25},
    {'name': 'Dipendenza da porno', 'description': 'Consuma molto contenuto pornografico', 'category': 'Sessuale', 'default_weight': -20},
    {'name': 'Esigenze particolari', 'description': 'Ha fetish o richieste specifiche', 'category': 'Sessuale', 'default_weight': 10},

    # --- Categoria: Carattere ---
    {'name': 'Fedele', 'description': 'Leale e affidabile sentimentalmente', 'category': 'Carattere', 'default_weight': 30},
    {'name': 'Donnaiolo/Vanitoso', 'description': 'Flirta e attira altre persone', 'category': 'Carattere', 'default_weight': -30},
    {'name': 'Geloso/a', 'description': 'Tende a essere possessivo/a', 'category': 'Carattere', 'default_weight': -15},
    {'name': 'Comunicativo/a', 'description': 'Sa parlare e affrontare i problemi', 'category': 'Carattere', 'default_weight': 25},
    {'name': 'Introverso/a chiuso', 'description': 'Difficile da avvicinare emotivamente', 'category': 'Carattere', 'default_weight': -10},
    {'name': 'Paziente e calmo/a', 'description': 'Non si arrabbia facilmente', 'category': 'Carattere', 'default_weight': 20},
    {'name': 'Temperamento difficile', 'description': 'Istintivo/a e di carattere complicato', 'category': 'Carattere', 'default_weight': -25},
    {'name': 'Responsabile', 'description': 'Affidabile e serio/a negli impegni', 'category': 'Carattere', 'default_weight': 25},
    {'name': 'Immaturo/a', 'description': 'Poco consapevole e non serio/a', 'category': 'Carattere', 'default_weight': -30},

    # --- Categoria: Intelletto ---
    {'name': 'Intelligente colto', 'description': 'Preparato e istruito', 'category': 'Intelletto', 'default_weight': 15},
    {'name': 'Semplice/Non istruito', 'description': 'Poco interesse per cultura/studi', 'category': 'Intelletto', 'default_weight': -10},
    {'name': 'Spiritoso/Divertente', 'description': 'Fa ridere e sa intrattenere', 'category': 'Intelletto', 'default_weight': 20},
    {'name': 'Noioso', 'description': 'Poco interessante come persona', 'category': 'Intelletto', 'default_weight': -20},

    # --- Categoria: Stile di vita ---
    {'name': 'Sportivo/a', 'description': 'Pratica sport regolarmente', 'category': 'Stile di vita', 'default_weight': 15},
    {'name': 'Sedentario/a', 'description': 'Non fa attività fisica', 'category': 'Stile di vita', 'default_weight': -10},
    {'name': 'Bevitore/Fumatore', 'description': 'Consuma alcol o fuma regolarmente', 'category': 'Stile di vita', 'default_weight': -15},
    {'name': 'Ama i viaggi', 'description': 'Appassionato di avventure', 'category': 'Stile di vita', 'default_weight': 15},
    {'name': 'Casalingo/a', 'description': 'Preferisce stare a casa', 'category': 'Stile di vita', 'default_weight': 0},

    # --- Categoria: Relazione ---
    {'name': 'Vuole figli', 'description': 'Desideroso di avere bambini', 'category': 'Relazione', 'default_weight': 20},
    {'name': 'NON vuole figli', 'description': 'Contrario a diventare genitore', 'category': 'Relazione', 'default_weight': -20},
    {'name': 'Disponibile al matrimonio', 'description': 'Aperto/a all\'idea di sposarsi', 'category': 'Relazione', 'default_weight': 25},
    {'name': 'Paura dell\'impegno', 'description': 'Riluttante a impegnarsi seriamente', 'category': 'Relazione', 'default_weight': -25},
    {'name': 'Materno/Paternale', 'description': 'Ha istinto genitoriale naturale', 'category': 'Relazione', 'default_weight': 15},

    # --- Categoria: Famiglia ---
    {'name': 'Legato/a alla famiglia', 'description': 'Frequenta e aiuta familiari', 'category': 'Famiglia', 'default_weight': 10},
    {'name': 'Indipendente da famiglia', 'description': 'Ha tagliato i cordoni ombelicali', 'category': 'Famiglia', 'default_weight': 10},
    {'name': 'Dipendente dalla mamma/papà', 'description': 'Ancora controllato dai genitori', 'category': 'Famiglia', 'default_weight': -20},
]


def seed():
    """
    Popola il database con i fattori standard NUOVI.
    ⚠️ CANCELLA TUTTI I FATTORI STANDARD VECCHI!
    """
    with app.app_context():
        try:
            print("\n" + "="*70)
            print("  SEEDING FATTORI STANDARD DI FANTAMATRIMONIO")
            print("  ⚠️ ATTENZIONE: VERRANNO CANCELLATI TUTTI I FATTORI VECCHI!")
            print("="*70)
            
            # ===== FASE 0: CANCELLAZIONE FATTORI VECCHI =====
            print("\n[FASE 0] Cancellazione fattori standard vecchi...")
            old_factors_count = StandardFactor.query.count()
            
            if old_factors_count > 0:
                # Cancella TUTTI i fattori standard
                num_deleted = db.session.query(StandardFactor).delete()
                db.session.commit()
                print(f"  ✗ Cancellati {num_deleted} fattori standard vecchi")
            else:
                print("  ℹ Nessun fattore vecchio da cancellare")
            
            # ===== FASE 1: CREAZIONE FATTORI NUOVI =====
            print("\n[FASE 1] Creazione fattori standard NUOVI...")
            created_count = 0
            
            for factor_data in standard_factors_data:
                factor = StandardFactor(**factor_data)
                db.session.add(factor)
                created_count += 1
                print(f"  ✓ CREATO: {factor_data['name']:<40} (peso: {factor_data['default_weight']:+3})")
            
            db.session.commit()
            print(f"\n  Risultato: {created_count} fattori creati")
            
            # ===== FASE 2: RICREAZIONE LINK LEAGUE_FACTOR =====
            print("\n[FASE 2] Ricreazione link league_factor...")
            all_leagues = League.query.all()
            
            if not all_leagues:
                print("  ⚠ ATTENZIONE: Non ci sono leghe nel database!")
                print("  I link league_factor verranno creati quando creerai le leghe.")
            else:
                # Cancella i vecchi link
                num_deleted = db.session.query(LeagueFactor).delete()
                db.session.commit()
                print(f"  ✗ Cancellati {num_deleted} vecchi link league_factor")
                
                # Ricrea i link
                all_factors = StandardFactor.query.all()
                links_created = 0
                
                for league in all_leagues:
                    for factor in all_factors:
                        new_link = LeagueFactor(
                            league_id=league.id,
                            standard_factor_id=factor.id,
                            is_active=False
                        )
                        db.session.add(new_link)
                        links_created += 1
                
                db.session.commit()
                print(f"  ✓ Creati {links_created} link league_factor")
                print(f"  ✓ Coinvolte {len(all_leagues)} lega/leghe")
            
            print("\n" + "="*70)
            print("  ✓ SEEDING COMPLETATO CON SUCCESSO!")
            print("="*70)
            print("\nSTATO ATTUALE:")
            print(f"  • Fattori standard nel DB: {StandardFactor.query.count()}")
            print(f"  • Link league_factor nel DB: {LeagueFactor.query.count()}")
            print("\nPROSSIMI STEP:")
            print("1. Avvia il server: python app.py")
            print("2. Accedi come admin di una lega")
            print("3. Vai in 'Fattori di Valutazione'")
            print("4. Attiva gli switch per i fattori che vuoi votare")
            print("5. Accedi come membro e vota!")
            print("="*70 + "\n")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n--- ERRORE DURANTE IL SEEDING ---")
            print(f"Errore: {str(e)}\n")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    seed()
