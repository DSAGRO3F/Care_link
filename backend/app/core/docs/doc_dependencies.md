
## 📊 Flux d'une requête avec dépendances
- Le module dependencies.py contient des fonctions réutilisables qui sont automatiquement appelées par FastAPI avant l'exécution des routes API.
### Les 3 dépendances principales pour ton projet
- get_db() - Fournir une session de base de données
- get_current_user() - Extraire l'utilisateur authentifié
- require_role() - Vérifier les rôles utilisateur

### Schéma simplifié de fonctionnement des dépendances.

```
Client                    FastAPI                    Dependencies              Routes
  |                         |                            |                        |
  |-- GET /patients ------->|                            |                        |
  |    Header: Bearer xxx   |                            |                        |
  |                         |                            |                        |
  |                         |-- 1. get_db() ------------>|                        |
  |                         |<-- Session DB -------------|                        |
  |                         |                            |                        |
  |                         |-- 2. get_current_user() -->|                        |
  |                         |    (token + db)            |                        |
  |                         |                            |-- Verify JWT           |
  |                         |                            |-- Query User in DB     |
  |                         |<-- User object ------------|                        |
  |                         |                            |                        |
  |                         |-- 3. Call route ---------->|----------------------->|
  |                         |    (user, db)              |                   get_patients()
  |                         |<-- Response ---------------|<-----------------------|
  |                         |                            |                        |
  |                         |-- 4. Close DB ------------->|                        |
  |<-- Response ------------|                            |                        |
```