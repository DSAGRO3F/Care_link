
# Architecture complète : app + Pro Santé Connect

```
┌─────────────────────────────────────────────────────────────────────┐
│                     APPLICATION (CareLink)                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────┐         ┌──────────────────────────────┐     │
│  │   Frontend       │         │      Backend FastAPI          │     │
│  │   (Dash)         │         │                               │     │
│  │                  │         │  ┌────────────────────────┐   │     │
│  │  - Bouton login  │────────>│  │  Les routes API        │   │     │
│  │  - Interface     │         │  │  /api/v1/auth/login    │   │     │
│  │    patients      │         │  │  /api/v1/auth/callback │   │     │
│  └──────────────────┘         │  │  /api/v1/patients      │   │     │
│                               │  └────────────────────────┘   │     │
│                               │                               │     │
│                               │  ┌────────────────────────┐   │     │
│                               │  │  PSC Client            │   │     │
│                               │  │  (Le code)            │   │     │
│                               │  │  - get_authorization   │   │     │
│                               │  │  - exchange_code       │   │     │
│                               │  │  - get_user_info       │   │     │
│                               │  └────────┬───────────────┘   │     │
│                               │           │                   │     │
│                               │           │ Appels HTTPS      │     │
│                               └───────────┼───────────────────┘     │
│                                           │                         │
└───────────────────────────────────────────┼─────────────────────────┘
                                            │
                                            │ HTTPS
                                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│              API PRO SANTÉ CONNECT (ANS - État)                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  - /auth (authorization endpoint)                                   │
│  - /token (token endpoint)                                          │
│  - /userinfo (userinfo endpoint)                                    │
│  - /certs (JWKS endpoint)                                           │
│                                                                       │
│  Propriété de l'ANS, Maintenu par l'ANS                       │
└─────────────────────────────────────────────────────────────────────┘
```


# Flux d'authentification complet (OAuth2/OpenID Connect)
```
Professionnel        App (Frontend)      App (Backend)         Pro Santé Connect
de santé                 Dash                    FastAPI                     ANS
    |                      |                         |                          |
    |─────────────────────>|                         |                          |
    | 1. Clic "Se          |                         |                          |
    |    connecter"        |                         |                          |
    |                      |                         |                          |
    |                      |─── GET /auth/login ────>|                          |
    |                      |                         |                          |
    |                      |                         |─── 2. Génère URL PSC ──>|
    |                      |                         |    avec client_id,       |
    |                      |                         |    redirect_uri, state   |
    |                      |                         |                          |
    |                      |<─── 302 Redirect ───────|                          |
    |                      |     vers PSC            |                          |
    |                      |                         |                          |
    |<─────────────────────|                         |                          |
    | 3. Redirection       |                         |                          |
    |    navigateur        |                         |                          |
    |                      |                         |                          |
    |─────────────────────────────────────────────────────────────────────────>|
    | 4. Page PSC: authentification e-CPS                                      |
    |    (scan QR code, code PIN)                                              |
    |                      |                         |                          |
    |<─────────────────────────────────────────────────────────────────────────|
    | 5. PSC redirige vers ton callback                                        |
    |    avec code d'autorisation                                              |
    |                      |                         |                          |
    |    GET /auth/callback?code=ABC123&state=xyz    |                          |
    |─────────────────────>|────────────────────────>|                          |
    |                      |                         |                          |
    |                      |                         |─── 6. Échange code ────>|
    |                      |                         |    POST /token           |
    |                      |                         |    {                     |
    |                      |                         |      code: "ABC123",     |
    |                      |                         |      client_id: "...",   |
    |                      |                         |      client_secret: "..." |
    |                      |                         |    }                     |
    |                      |                         |                          |
    |                      |                         |<─── access_token ────────|
    |                      |                         |     refresh_token        |
    |                      |                         |     id_token (JWT)       |
    |                      |                         |                          |
    |                      |                         |─── 7. Get user info ───>|
    |                      |                         |    GET /userinfo         |
    |                      |                         |    Authorization: Bearer |
    |                      |                         |                          |
    |                      |                         |<─── User data ───────────|
    |                      |                         |     {                    |
    |                      |                         |       sub: "123...",     |
    |                      |                         |       given_name: "...", |
    |                      |                         |       family_name: "...",|
    |                      |                         |       SubjectNameID: RPPS|
    |                      |                         |     }                    |
    |                      |                         |                          |
    |                      |                         | 8. Crée/update user en DB|
    |                      |                         | 9. Génère JWT interne    |
    |                      |                         |                          |
    |                      |<─── JWT + user info ────|                          |
    |<─────────────────────|                         |                          |
    | 10. Stocke JWT       |                         |                          |
    |     en localStorage  |                         |                          |
    |     ou cookie        |                         |                          |
    |                      |                         |                          |
    |─── Requêtes API ────>|─── avec JWT interne ───>|                          |
    | (toutes les autres)  |                         |                          |
```

# Récapitulatif : Qui fait quoi ?

| Composant                  | Responsabilité                            | Qui le maintient |
|----------------------------|-------------------------------------------|------------------|
| API Pro Santé Connect      | Authentifier les pros de santé via e-CPS  | ANS (État)       |
| PSC Client (code CareLink) | Appeler l'API PSC (client HTTP)           | CareLink         |
| Les routes /auth/          | Gérer le flux OAuth2 dans CareLink        | CareLink         |
| Service d'authentification | Logique métier (créer user en DB, etc.)   | CareLink         |
| Les JWT internes           | Authentifier les requêtes API après login | CareLink         |


## Points clés à retenir

- On utilise l'API PSC → Il s'agit d'authentiifer le professionnnel de santé
- On code un CLIENT → ProSanteConnectClient qui fait des appels HTTPS vers PSC (est ce que ce professionnel de santé est connu ?)
- Si le professionnel de santé est connu:
  - OAuth2 = échange de code → PSC te donne un code, tu l'échanges contre un token
  - Deux systèmes de tokens :
    - Tokens PSC : pour communiquer avec PSC (courte durée)
    - Tokens JWT internes : pour authentifier les requêtes dans CareLink (durée à choisir/définir)


- **PSC identifie, CareLink autorise : PSC dit "c'est bien le Dr Dupont", CareLink décide "il peut voir quels patients"**


# Le "code" PSC, c'est quoi ?
Non, ce n'est PAS un JWT. C'est juste un ticket temporaire.
🎫 Analogie : Le vestiaire de théâtre
Toi (navigateur)          Vestiaire (PSC)              Théâtre (CareLink)
      │                         │                            │
      │── "Je veux entrer" ────>│                            │
      │                         │                            │
      │   (Tu montres ta        │                            │
      │    carte d'identité)    │                            │
      │                         │                            │
      │<── Ticket n°4827 ───────│                            │
      │    (valable 30 sec)     │                            │
      │                         │                            │
      │                         │                            │
      │── "Voici mon ticket" ───────────────────────────────>│
      │                         │                            │
      │                         │<── "Ticket 4827 valide?" ──│
      │                         │                            │
      │                         │── "Oui, c'est M. Dupont" ─>│
      │                         │    Médecin, RPPS 123...    │
      │                         │                            │

Le code c'est juste le numéro du ticket (ex: abc123xyz). Il ne contient aucune information. Il sert uniquement à prouver que tu viens bien du vestiaire.

# "Échanger le code" - que se passe-t-il ?
Le mot "échange" ne veut PAS dire que CareLink envoie des infos à PSC.
🎟️ C'est un échange ticket → informations
CareLink (backend)                              PSC (serveur ANS)
      │                                               │
      │                                               │
      │── POST /token ───────────────────────────────>│
      │   {                                           │
      │     code: "abc123xyz",      ← Le ticket       │
      │     client_id: "carelink",  ← Qui je suis     │
      │     client_secret: "xxx"    ← Ma preuve       │
      │   }                                           │
      │                                               │
      │<── access_token + id_token ───────────────────│
      │                                               │
      │                                               │
      │── GET /userinfo ─────────────────────────────>│
      │   Authorization: Bearer <access_token>        │
      │                                               │
      │<── {                                          │
      │      "given_name": "Jean",                    │
      │      "family_name": "Dupont",                 │
      │      "SubjectNameID": "12345678901",  ← RPPS  │
      │      "profession": "Médecin",                 │
      │      ...                                      │
      │    }                                          │
      │                                               │

CareLink n'envoie RIEN sur l'utilisateur à PSC. CareLink dit juste "voici le ticket, donnez-moi les infos de la personne".

# Scénario A : Première connexion (Dr Dupont n'existe pas en base)
PSC renvoie : RPPS = 12345678901, Nom = Dupont, Prénom = Jean

CareLink cherche en base : SELECT * FROM users WHERE rpps = '12345678901'
→ Résultat : Aucun utilisateur trouvé

CareLink CRÉE l'utilisateur :
INSERT INTO users (rpps, first_name, last_name, email, ...)
VALUES ('12345678901', 'Jean', 'Dupont', ...)

# Scénario B : Connexion suivante (Dr Dupont existe déjà)
PSC renvoie : RPPS = 12345678901, Nom = Dupont, Prénom = Jean

CareLink cherche en base : SELECT * FROM users WHERE rpps = '12345678901'
→ Résultat : User id=42 trouvé !

CareLink MET À JOUR (optionnel) :
UPDATE users SET last_login = NOW() WHERE id = 42

(On peut aussi mettre à jour le nom/prénom si PSC a des infos plus récentes)

Le RPPS est la clé. C'est l'identifiant unique qui permet de retrouver l'utilisateur.

# Pourquoi CareLink génère son propre JWT ?
🏨 Analogie : L'hôtel et le badge
Étape 1 : Tu arrives à l'hôtel avec ton passeport (PSC)
          → L'hôtel vérifie ton identité UNE FOIS

Étape 2 : L'hôtel te donne un badge magnétique (JWT CareLink)
          → Ce badge ouvre ta chambre, la piscine, le spa...

Étape 3 : Pendant ton séjour, tu utilises le BADGE, pas le passeport
          → Tu ne remontres pas ton passeport à chaque porte !
- En pratique dans CareLink :
Requête 1 : GET /api/patients
            Authorization: Bearer <JWT_CARELINK>
            → CareLink vérifie le JWT (rapide, local)
            → Pas besoin d'appeler PSC !

Requête 2 : POST /api/patients/42/evaluation
            Authorization: Bearer <JWT_CARELINK>
            → Même chose, vérification locale

... 50 autres requêtes pendant la session ...
            → Toujours le JWT local, jamais PSC

# Pourquoi ne pas utiliser le token PSC directement ?
Pourquoi ne pas utiliser le token PSC directement ?

| Token PSC                       | JWT CareLink                                                     |
|---------------------------------|------------------------------------------------------------------|
| Courte durée (quelques minutes) | Durée configurable (30 min dans ton config)                      |
| Contient des infos génériques   | Contient des infos spécifiques CareLink (rôles, tenant_id, etc.) |
| Pour communiquer avec PSC       | Pour communiquer avec CareLink                                   |
| Géré par l'ANS                  | Géré par CareLink                                                |

# Résumé visuel complet
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   👨‍⚕️ Dr Dupont        🌐 Navigateur       🏥 CareLink       🏛️ PSC (ANS)   │
│        │                    │                   │                │          │
│        │─── Clic "PSC" ────>│                   │                │          │
│        │                    │── GET /login ────>│                │          │
│        │                    │<── Redirect PSC ──│                │          │
│        │                    │                   │                │          │
│        │<───────────────────│── Redirect ──────────────────────>│          │
│        │                    │                   │                │          │
│        │   [Page PSC : scan QR code e-CPS, PIN]                 │          │
│        │                    │                   │                │          │
│        │<── Redirect + code=abc123 ─────────────────────────────│          │
│        │                    │                   │                │          │
│        │                    │── GET /callback?code=abc123 ─────>│          │
│        │                    │                   │                │          │
│        │                    │                   │── POST /token ────────>│ │
│        │                    │                   │   (code=abc123)        │ │
│        │                    │                   │<── access_token ───────│ │
│        │                    │                   │                        │ │
│        │                    │                   │── GET /userinfo ──────>│ │
│        │                    │                   │<── {RPPS, nom...} ─────│ │
│        │                    │                   │                │          │
│        │                    │                   │ ┌────────────────────┐ │  │
│        │                    │                   │ │ SELECT user        │ │  │
│        │                    │                   │ │ WHERE rpps=123...  │ │  │
│        │                    │                   │ │                    │ │  │
│        │                    │                   │ │ Si pas trouvé:     │ │  │
│        │                    │                   │ │   INSERT user      │ │  │
│        │                    │                   │ │                    │ │  │
│        │                    │                   │ │ Générer JWT        │ │  │
│        │                    │                   │ │ CareLink           │ │  │
│        │                    │                   │ └────────────────────┘ │  │
│        │                    │                   │                │          │
│        │                    │<── JWT CareLink ──│                │          │
│        │<───────────────────│   (stocké local)  │                │          │
│        │                    │                   │                │          │
│   ─────┼────────────────────┼───────────────────┼────────────────┼──────────│
│   CONNEXION TERMINÉE - UTILISATION NORMALE                                  │
│   ─────┼────────────────────┼───────────────────┼────────────────┼──────────│
│        │                    │                   │                │          │
│        │── Voir patients ──>│── GET /patients ─>│                │          │
│        │                    │   + JWT CareLink  │                │          │
│        │                    │<── Liste patients │   (PSC n'est   │          │
│        │<───────────────────│                   │    plus appelé)│          │
│        │                    │                   │                │          │
└─────────────────────────────────────────────────────────────────────────────┘

# Récap
## ✅ Point 1 - Correct

L'utilisateur clique sur "Accès PSC pour authentification"

Oui, exactement.

## ⚠️ Point 2 - Précision sur l'authentification

PSC demande les informations. Est-ce qu'il doit les entrer ? QR Code ?

L'utilisateur a deux options pour s'authentifier sur PSC :

| Méthode              | Comment ça marche                                                                                                   |
|----------------------|---------------------------------------------------------------------------------------------------------------------|
| e-CPS (smartphone)   | L'écran PSC affiche un QR code → L'utilisateur le scanne avec l'app e-CPS → Il entre son code PIN sur son téléphone |
| Carte CPS (physique) | L'utilisateur insère sa carte dans un lecteur USB → Il entre son code PIN sur l'ordinateur                          |

┌─────────────────────────────────────────┐
│         Page PSC (navigateur)           │
│                                         │
│   ┌─────────────┐                       │
│   │ ▄▄▄▄▄▄▄▄▄▄ │   "Scannez ce QR code │
│   │ █ QR CODE █ │    avec votre app     │
│   │ ▀▀▀▀▀▀▀▀▀▀ │    e-CPS"             │
│   └─────────────┘                       │
│                                         │
│   ── ou ──                              │
│                                         │
│   [Utiliser ma carte CPS]               │
│                                         │
└─────────────────────────────────────────┘

         │
         │ QR scanné
         ▼

┌─────────────────────────────────────────┐
│      App e-CPS (smartphone)             │
│                                         │
│   Connexion demandée par CareLink       │
│                                         │
│   Entrez votre code PIN :               │
│   ┌───┬───┬───┬───┬───┬───┐            │
│   │ * │ * │ * │ * │ * │ * │            │
│   └───┴───┴───┴───┴───┴───┘            │
│                                         │
│        [Valider]                        │
│                                         │
└─────────────────────────────────────────┘

L'utilisateur n'entre jamais son RPPS ou son nom. C'est l'e-CPS (liée à son identité) + le PIN qui prouvent qui il est.

## ✅ Point 3 - Correct

Génération d'un code (pas un JWT)

Oui, c'est un code d'autorisation (authorization code). C'est juste une chaîne de caractères aléatoire, par exemple : a1b2c3d4e5f6. Il expire en 30 secondes environ.

## ⚠️ Point 4 - Précision sur la transmission

Ce code est transmis à CareLink

Oui, mais via une redirection du navigateur :
PSC redirige le navigateur vers :
https://carelink.fr/auth/callback?code=a1b2c3d4e5f6&state=xyz

Le navigateur appelle cette URL → CareLink reçoit le code

## ⚠️ Point 5 - Il manque une étape importante !

CareLink génère un JWT

Pas tout de suite ! Il y a une étape intermédiaire cruciale :
Étape 5a : CareLink envoie le code à PSC (serveur à serveur)
           → PSC répond avec un access_token

Étape 5b : CareLink utilise l'access_token pour demander les infos
           → PSC répond : nom, prénom, RPPS, profession...

Étape 5c : CareLink cherche/crée l'utilisateur en base avec le RPPS

Étape 5d : MAINTENANT CareLink génère son JWT

# Les étapes de l'authentification via PSC
1. Utilisateur clique "Se connecter avec PSC"
                    │
                    ▼
2. Redirection vers PSC → Authentification (QR code e-CPS + PIN)
                    │
                    ▼
3. PSC génère un CODE temporaire (pas JWT, juste un ticket)
                    │
                    ▼
4. Redirection vers CareLink avec le code dans l'URL
                    │
                    ▼
5a. CareLink envoie le code à PSC (backend → backend)
                    │
                    ▼
5b. PSC renvoie les infos : RPPS, nom, prénom, profession...
                    │
                    ▼
5c. CareLink cherche l'utilisateur par RPPS (ou le crée)
                    │
                    ▼
5d. CareLink génère un JWT interne
                    │
                    ▼
6. L'utilisateur utilise ce JWT pour toutes ses requêtes
   (PSC n'est plus jamais contacté pendant la session)

# 🔐 Comment les données sont transmises de façon sécurisée ?
Deux mécanismes de protection :
1. HTTPS (chiffrement du transport)
Toutes les communications sont chiffrées. Même si quelqu'un intercepte les données, il ne voit que du charabia.
2. Le secret client (authentification de CareLink)
Quand CareLink envoie le code à PSC, il envoie aussi une preuve de son identité :
3. CareLink → PSC :

POST /token
{
  "code": "a1b2c3d4e5f6",           ← Le ticket
  "client_id": "carelink-xyz",      ← "Je suis CareLink"
  "client_secret": "********"       ← "Voici ma preuve secrète"
}

Le client_secret est une clé secrète connue uniquement de CareLink et de PSC (fournie lors de l'inscription Datapass). Sans cette clé, impossible d'échanger le code.

# 🛡️ Protection contre un faux professionnel de santé
Excellente question ! Voici pourquoi un imposteur ne peut pas usurper l'identité d'un vrai professionnel :
Scénario : "Je veux me faire passer pour le Dr Dupont"
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  🦹 Imposteur : "Je vais accéder aux données patients !"        │
│                                                                 │
│  Étape 1 : Il clique sur "Se connecter avec PSC"                │
│            → OK, n'importe qui peut cliquer                     │
│                                                                 │
│  Étape 2 : PSC affiche un QR code                               │
│            → OK, n'importe qui peut voir le QR code             │
│                                                                 │
│  Étape 3 : Il doit scanner avec l'app e-CPS                     │
│            → 🚫 BLOQUÉ !                                        │
│                                                                 │
│            Pourquoi ?                                           │
│            • Il n'a pas l'app e-CPS du Dr Dupont                │
│            • Il ne connaît pas le code PIN du Dr Dupont         │
│            • L'app e-CPS est liée à UN téléphone précis         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

# **Comment l'e-CPS est-elle activée à l'origine ?**
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  Pour activer son e-CPS, le Dr Dupont a dû :                    │
│                                                                 │
│  1. Recevoir sa carte CPS physique par courrier                 │
│     (envoyée à son adresse professionnelle vérifiée)            │
│                                                                 │
│  2. Utiliser cette carte + un lecteur pour activer l'app        │
│     (preuve qu'il possède la carte)                             │
│                                                                 │
│  3. Définir un code PIN personnel                               │
│     (qu'il est le seul à connaître)                             │
│                                                                 │
│  4. L'app est liée à SON téléphone                              │
│     (impossible de la transférer)                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

# En résumé : la chaîne de confiance
L'État (Ordre des médecins, ARS...)
         │
         │ Vérifie le diplôme et l'identité
         ▼
Inscription au RPPS (numéro unique)
         │
         │ Envoie la carte CPS à l'adresse pro
         ▼
Carte CPS physique (puce sécurisée)
         │
         │ Nécessaire pour activer l'e-CPS
         ▼
App e-CPS (sur téléphone personnel)
         │
         │ Protégée par code PIN
         ▼
Authentification PSC
         │
         │ Preuve d'identité transmise
         ▼
Accès CareLink

Un imposteur devrait donc :

Obtenir frauduleusement un diplôme de médecin
S'inscrire au RPPS avec de faux documents
Recevoir une carte CPS à une fausse adresse
Activer une e-CPS

C'est le même niveau de difficulté que de se faire passer pour un médecin dans un hôpital physique. PSC transpose cette sécurité dans le monde numérique.

# Flux: exemple création utlisateur
Prenons l'exemple concret de Marie Dupont, infirmière que l'on vient de recruter comme coordinatrice.
Création de Marie Dupont (Infirmière + Coordinatrice)
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                        COUCHE API                               │
├─────────────────────────────────────────────────────────────────┤
│  app/api/v1/user/                                               │
│  ├── routes.py      ← Point d'entrée : POST /api/v1/users       │
│  ├── schemas.py     ← Validation des données entrantes          │
│  └── services.py    ← Logique métier (création user)            │
│                                                                 │
│  app/api/v1/auth/                                               │
│  └── services.py    ← (Plus tard) Authentification PSC          │
└─────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                        COUCHE MODÈLES                           │
├─────────────────────────────────────────────────────────────────┤
│  app/models/user/                                               │
│  ├── user.py        ← Table "users" (Marie)                     │
│  ├── profession.py  ← Table "professions" (Infirmier)           │
│  ├── role.py        ← Table "roles" (COORDINATEUR)              │
│  └── user_associations.py ← Table "user_roles" (Marie ↔ Coord)  │
└─────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                        COUCHE DATABASE                          │
├─────────────────────────────────────────────────────────────────┤
│  app/database/                                                  │
│  ├── session.py     ← Connexion PostgreSQL                      │
│  └── base_class.py  ← Classe de base SQLAlchemy                 │
└─────────────────────────────────────────────────────────────────┘

# Explication imagée de chaque module: routes.py, schema.py et services.py
## routes.py
```
app/api/v1/user/routes.py → 🚪 L'accueil / Le standard téléphonique
```
-> "Bonjour, je voudrais créer un compte pour Marie Dupont"

C'est le point d'entrée. Comme une réceptionniste :

Elle reçoit les demandes (requêtes HTTP)
Elle vérifie que vous avez le droit de faire cette demande (authentification)
Elle transmet au bon service (appelle services.py)
Elle renvoie la réponse au demandeur

@router.post("/users")  # "Si quelqu'un demande à créer un user..."
async def create_user(user_data: UserCreate):  # "...prends ses infos..."
    return user_service.create(user_data)  # "...et passe-les au service RH"


---
## schema.py
```
**`app/api/v1/user/schemas.py`** → 📋 **Le formulaire d'inscription**
```
┌─────────────────────────────────────┐
│  FORMULAIRE NOUVEAU COLLABORATEUR   │
├─────────────────────────────────────┤
│  Nom*: [Dupont_________]            │
│  Prénom*: [Marie__________]         │
│  Email*: [marie.dupont@ssiad.fr]    │
│  RPPS: [12345678901____]            │
│  Profession*: [Infirmier ▼]         │
│                                     │
│  * Champs obligatoires              │
└─────────────────────────────────────┘
C'est le contrat de données. Comme un formulaire papier :

Il définit quels champs sont obligatoires
Il vérifie le format (email valide ? RPPS = 11 chiffres ?)
Il rejette les formulaires mal remplis AVANT de déranger le service RH

class UserCreate(BaseModel):
    email: EmailStr           # ✅ Doit être un email valide
    first_name: str           # ✅ Obligatoire
    rpps: str | None = None   # ⚪ Optionnel
    profession_id: int        # ✅ Obligatoire


---

## services.py
```
**app/api/v1/user/services.py`** → 👔 **Le service des Ressources Humaines**
```
"OK, j'ai le formulaire de Marie. Je vais :
 1. Vérifier qu'elle n'existe pas déjà
 2. Créer son dossier
 3. Lui attribuer son badge (rôle)
 4. L'inscrire dans l'annuaire"

C'est la logique métier. Comme un gestionnaire RH :

Il applique les règles (pas de doublon d'email, RPPS valide...)
Il orchestre les opérations (créer user, assigner rôle...)
Il interagit avec la base de données
Il ne parle jamais directement au public (c'est routes.py qui fait ça)

## Autres modules intervenant
class UserService:
    def create_user(self, data: UserCreate) -> User:
        # Vérifier que l'email n'existe pas
        if self.db.query(User).filter(User.email == data.email).first():
            raise ValueError("Email déjà utilisé")
        
        # Créer l'utilisateur
        user = User(**data.dict())
        self.db.add(user)
        self.db.commit()
        return user
```

---

### **`app/models/user/user.py`** → 🗂️ **Le dossier personnel de Marie**
```
┌─────────────────────────────────────┐
│  DOSSIER EMPLOYÉ #42                │
├─────────────────────────────────────┤
│  Nom: Dupont                        │
│  Prénom: Marie                      │
│  Email: marie.dupont@ssiad.fr       │
│  RPPS: 12345678901                  │
│  Profession: → [voir classeur 60]   │
│  Rôles: → [voir classeur COORD]     │
│  Actif: ✅ Oui                      │
└─────────────────────────────────────┘
```

C'est la **structure du dossier**. Comme un modèle de fiche employé :
- Il **définit** quelles informations on stocke
- Il **définit** les liens vers d'autres dossiers (profession, rôles)
- Il **correspond** exactement à une table SQL

---

### **`app/models/user/profession.py`** → 📚 **Le référentiel des diplômes**
```
┌─────────────────────────────────────┐
│  RÉFÉRENTIEL DES PROFESSIONS        │
├─────────────────────────────────────┤
│  Code 10: Médecin (RPPS: oui)       │
│  Code 60: Infirmier (RPPS: oui) ◄── Marie
│  Code 93: Aide-soignant (RPPS: non) │
│  ...                                │
└─────────────────────────────────────┘
```

C'est le **catalogue officiel** des diplômes d'État. Immuable.

---

### **`app/models/user/role.py`** → 🎫 **Les badges d'accès**
```
┌─────────────────────────────────────┐
│  BADGE: COORDINATEUR                │
├─────────────────────────────────────┤
│  Accès:                             │
│  ✅ Voir les patients               │
│  ✅ Créer des patients              │
│  ✅ Planifier les soins             │
│  ✅ Accorder des accès              │
│  ❌ Administration système          │
└─────────────────────────────────────┘
```

C'est le **système de badges**. Un utilisateur peut avoir plusieurs badges.

---

### **`app/models/user/user_associations.py`** → 📎 **Le registre des attributions**
```
┌─────────────────────────────────────┐
│  REGISTRE DES BADGES ATTRIBUÉS      │
├─────────────────────────────────────┤
│  Marie (42) ←→ COORDINATEUR         │
│  Marie (42) ←→ INFIRMIERE           │
│  Jean (43) ←→ ADMIN                 │
│  ...                                │
└─────────────────────────────────────┘
```

C'est la **table de liaison** qui connecte users et roles (many-to-many).

---

## 🔄 Le trio routes.py / services.py / schemas.py

### Analogie : **Un restaurant** 🍽️
```
CLIENT                 SERVEUR              CUISINE              RECETTE
(Navigateur)          (routes.py)         (services.py)        (schemas.py)
    │                      │                    │                    │
    │  "Je veux une        │                    │                    │
    │   pizza margherita"  │                    │                    │
    │─────────────────────►│                    │                    │
    │                      │                    │                    │
    │                      │  Vérifie la        │                    │
    │                      │  commande avec ────┼───────────────────►│
    │                      │  la carte          │                    │
    │                      │◄───────────────────┼────────────────────│
    │                      │  "OK, pizza        │                    │
    │                      │   existe"          │                    │
    │                      │                    │                    │
    │                      │  "Chef, une        │                    │
    │                      │   margherita !" ───┼───────────────────►│
    │                      │                    │                    │
    │                      │                    │  Prépare la pizza  │
    │                      │                    │  (logique métier)  │
    │                      │                    │                    │
    │                      │◄───────────────────┼────────────────────│
    │                      │  🍕 Pizza prête    │                    │
    │                      │                    │                    │
    │◄─────────────────────│                    │                    │
    │  🍕 Votre pizza      │                    │                    │
    │                      │                    │                    │


## 🔄 Exemple complet : Rattacher une entité à un GCSMS

Même pattern que pour création utilisateur :
```
┌─────────────────────────────────────────────────────────────────┐
│  POST /api/v1/organizations/gcsms/5/entities                    │
│  Body: { "entity_id": 12 }                                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  routes.py                                                      │
│  ─────────                                                      │
│  "OK, l'admin veut rattacher l'entité 12 au GCSMS 5"            │
│  → Vérifie que c'est bien un admin                              │
│  → Passe au service                                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  schemas.py                                                     │
│  ──────────                                                     │
│  class EntityAttachRequest(BaseModel):                          │
│      entity_id: int        # Obligatoire                        │
│      start_date: date      # Optionnel, défaut = aujourd'hui    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  services.py                                                    │
│  ───────────                                                    │
│  def attach_entity_to_gcsms(gcsms_id, entity_id):               │
│      1. Vérifier que le GCSMS existe                            │
│      2. Vérifier que l'entité existe                            │
│      3. Vérifier que l'entité n'est pas déjà rattachée          │
│      4. Vérifier que l'entité est dans le même département      │
│      5. Créer le rattachement                                   │
│      6. Logger l'opération (audit)                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## ✅ En résumé

Le trio fonctionne ainsi :
```
routes.py    →  "QUI peut faire QUOI et QUAND"  (API + permissions)
schemas.py   →  "QUEL FORMAT pour les données"  (validation entrée/sortie)
services.py  →  "COMMENT on le fait"            (logique + règles + base)

























