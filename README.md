# Projet de Spam détection
Ce projet est une appli de détection de spam pour classer les messages comme spam ou non-spam. Le projet inclut une application web FastAPI pour servir le modèle et un script pour générer un grand jeu de données de messages spam et non-spam.  


## Fonctionnalités

- 🔐 Système d'authentification (inscription/connexion)
- 📊 Quota de 10 requêtes par utilisateur par jour
- 📝 Analyse de SMS basée sur :
  - Une liste de mots uniques de spam
  - Une base de données de SMS classifiés (spam/ham)
- 📜 Historique des analyses par utilisateur
- 🔄 API REST pour accéder à l'historique
- 🎨 Interface utilisateur intuitive avec Bootstrap


## Prérequis
Python 3.8+
pip

## Installation
Clonez le dépôt :  
```bash
  git clone https://github.com/arkaelid/spam-classifier-sullivan.git
  cd spam-classifier-sullivan
```
##Créez un environnement virtuel (recommandé) 
```bash
python -m venv venv
source venv/bin/activate  # Sur Linux/Mac
venv\Scripts\activate     # Sur Windows
```

## Installez les paquets requis :  
```bash
  pip install -r requirements.txt
```

## Structure des fichiers

```
detecteur-spam-sms/
├── main.py                    # Application principale FastAPI
├── requirements.txt           # Dépendances Python
├── SMSSpamCollection.csv      # Base de données de SMS
├── mots_uniques_spam.csv     # Liste de mots spam
├── static/                    # Fichiers statiques
│   └── css/
│       └── bootstrap.css
└── templates/                 # Templates HTML
    ├── index.html
    ├── login.html
    ├── register.html
    ├── resultats.html
    └── history.html
```

## Configuration

L'application utilise SQLite comme base de données, qui sera créée automatiquement au premier lancement. Aucune configuration supplémentaire n'est nécessaire.


## Lancement de l'Application Web en local

```bash
 uvicorn main:app --reload    
```
Accédez à l'application dans votre navigateur :
```
http://localhost:8000
```

## Lancement sur la VM
### En local
```bash
  docker login grpccicdaacr.azurecr.io    
  docker build -t grpccicdaacr.azurecr.io/spam-classifier-sullivan . 
  docker tag spam-classifier-sullivan grpccicdaacr.azurecr.io/spam-classifier-sullivan
  docker run -p 5568:5568  grpccicdaacr.azurecr.io/spam-classifier-sullivan 
  docker push grpccicdaacr.azurecr.io/spam-classifier-sullivan    
```

### Sur putty
```bash
  docker pull grpccicdaacr.azurecr.io/spam-classifier-sullivan
  docker run -p 5568:5568 grpccicdaacr.azurecr.io/spam-classifier-sullivan

```
## Utilisation

1. **Inscription/Connexion**
   - Créez un compte via la page d'inscription
   - Connectez-vous avec vos identifiants

2. **Analyse de SMS**
   - Collez le SMS à analyser dans le champ de texte
   - Cliquez sur "Envoyer"
   - Le résultat indiquera si le message est un spam ou non

3. **Historique**
   - Consultez vos analyses précédentes via l'onglet "Historique"
   - Visualisez les mots suspects détectés

4. **API**
   - Accédez à l'historique via l'API REST
   - Documentation Swagger disponible sur `/docs`

## Points d'API

- `GET /api/history` : Récupérer tout l'historique
- `GET /api/history/{sms_id}` : Récupérer un SMS spécifique
- `GET /api/history/filter` : Filtrer l'historique
  - Paramètres : 
    - `classification` : "SPAM" ou "Message normal"
    - `start_date` : Date de début (YYYY-MM-DD)
    - `end_date` : Date de fin (YYYY-MM-DD)

## Algorithme de détection

Le système utilise une approche en deux étapes :
1. Vérifie si le message contient des mots de la liste `mots_uniques_spam.csv`
2. Compare le message avec la base de données `SMSSpamCollection.csv`
   - Un message est considéré comme spam s'il partage 5 mots ou plus avec des spams connus

## Sécurité

- Mots de passe hashés avec SHA-256
- Protection contre les injections SQL
- Système de quotas pour éviter l'abus
- Authentification requise pour toutes les fonctionnalités

## Limitations

- Maximum 10 requêtes par utilisateur par jour
- Taille maximale du message non spécifiée
- Base de données SQLite 

## Contact

Votre nom - votre.email@example.com

## Remerciements

- FastAPI pour le framework web
- Bootstrap pour le design
- La communauté Python pour les bibliothèques utilisées