"""
Script de migration de la base de données
Ajoute les nouvelles colonnes et tables nécessaires pour le système d'offres d'emploi
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = "cv_analyses.db"

def migrate_database():
    """Migre la base de données vers la nouvelle structure"""
    print("🔄 Début de la migration de la base de données...")
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        # Vérifier si la table job_offers existe
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='job_offers'")
        job_offers_exists = c.fetchone() is not None
        
        if not job_offers_exists:
            print("📋 Création de la table job_offers...")
            c.execute('''
                CREATE TABLE job_offers (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    content TEXT,
                    created_date TEXT
                )
            ''')
            print("✅ Table job_offers créée")
        
        # Vérifier si la colonne job_offer_id existe dans analyses
        c.execute("PRAGMA table_info(analyses)")
        columns = [column[1] for column in c.fetchall()]
        
        if 'job_offer_id' not in columns:
            print("🔗 Ajout de la colonne job_offer_id à la table analyses...")
            c.execute('ALTER TABLE analyses ADD COLUMN job_offer_id TEXT')
            print("✅ Colonne job_offer_id ajoutée")
            
            # Créer une offre d'emploi par défaut pour les analyses existantes
            default_job_id = "default_legacy"
            c.execute('''
                INSERT OR IGNORE INTO job_offers (id, title, content, created_date)
                VALUES (?, ?, ?, ?)
            ''', (
                default_job_id,
                "Offre héritée (analyses antérieures)",
                "Analyses réalisées avant l'implémentation du système d'offres d'emploi",
                datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            ))
            
            # Mettre à jour toutes les analyses existantes avec l'ID par défaut
            c.execute('UPDATE analyses SET job_offer_id = ? WHERE job_offer_id IS NULL', (default_job_id,))
            print("🔄 Analyses existantes migrées vers l'offre par défaut")
        
        conn.commit()
        print("✅ Migration terminée avec succès !")
        
    except Exception as e:
        print(f"❌ Erreur lors de la migration : {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def check_database_structure():
    """Vérifie la structure actuelle de la base de données"""
    if not os.path.exists(DB_PATH):
        print("ℹ️ Aucune base de données existante trouvée")
        return
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    print("📊 Structure actuelle de la base de données :")
    
    # Lister les tables
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = c.fetchall()
    print(f"Tables : {[table[0] for table in tables]}")
    
    # Structure de la table analyses
    if any(table[0] == 'analyses' for table in tables):
        c.execute("PRAGMA table_info(analyses)")
        analyses_columns = c.fetchall()
        print(f"Colonnes de 'analyses' : {[col[1] for col in analyses_columns]}")
    
    # Structure de la table job_offers
    if any(table[0] == 'job_offers' for table in tables):
        c.execute("PRAGMA table_info(job_offers)")
        job_offers_columns = c.fetchall()
        print(f"Colonnes de 'job_offers' : {[col[1] for col in job_offers_columns]}")
    
    conn.close()

if __name__ == "__main__":
    print("🚀 Script de migration de la base de données CV_IA")
    print("=" * 50)
    
    check_database_structure()
    print()
    migrate_database()
    print()
    check_database_structure()
