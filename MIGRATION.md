# Migration de la base de données

## Problème
Si vous rencontrez des erreurs SQLite comme :
```
sqlite3.OperationalError: no such column: job_offer_id
```

C'est que votre base de données existante n'a pas la nouvelle structure.

## Solution

### Option 1: Migration automatique (recommandée)
La migration se fait automatiquement au démarrage de l'application. Si cela ne fonctionne pas, utilisez l'option 2.

### Option 2: Script de migration manuel
Exécutez le script de migration :

```bash
python migrate_db.py
```

### Option 3: Réinitialisation complète
Si vous voulez repartir de zéro :

1. Supprimez le fichier `cv_analyses.db`
2. Relancez l'application

⚠️ **Attention** : Cette option supprime toutes vos données existantes !

## Nouvelle structure

### Table `job_offers`
- `id` : Identifiant unique de l'offre
- `title` : Titre de l'offre d'emploi  
- `content` : Contenu de l'offre
- `created_date` : Date de création

### Table `analyses` (mise à jour)
- Nouvelles colonnes :
  - `job_offer_id` : Lien vers l'offre d'emploi

## Fonctionnalités ajoutées
- Regroupement des analyses par offre d'emploi
- Statistiques par offre
- Filtrage dans l'historique
- Page de gestion des offres
