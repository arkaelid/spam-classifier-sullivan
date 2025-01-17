from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import RedirectResponse
import sqlite3
import csv
import hashlib
import secrets
from typing import Optional, List
from pydantic import BaseModel

# Créer l'instance FastAPI
app = FastAPI()

# Monter les fichiers statiques
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configurer les templates
templates = Jinja2Templates(directory="templates")

security = HTTPBasic()

# Créer la table users si elle n'existe pas
def init_db():
    con = sqlite3.connect("messages.db")
    cur = con.cursor()
    
    # Table users existante
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    # Nouvelle table pour les quotas
    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_quotas (
            username TEXT PRIMARY KEY,
            requests_count INTEGER DEFAULT 0,
            last_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (username) REFERENCES users(username)
        )
    ''')
    
    # Nouvelle table pour l'historique des SMS
    cur.execute('''
        CREATE TABLE IF NOT EXISTS sms_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            message TEXT NOT NULL,
            classification TEXT NOT NULL,
            suspicious_words TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (username) REFERENCES users(username)
        )
    ''')
    
    con.commit()
    con.close()

init_db()

# Fonction pour gérer les quotas
def check_quota(username: str, max_requests: int = 10) -> tuple[bool, int]:
    con = sqlite3.connect("messages.db")
    cur = con.cursor()
    
    # Vérifier si l'utilisateur a déjà une entrée dans user_quotas
    cur.execute('''
        INSERT OR IGNORE INTO user_quotas (username, requests_count)
        VALUES (?, 0)
    ''', (username,))
    
    # Réinitialiser le compteur si plus de 24h se sont écoulées
    cur.execute('''
        UPDATE user_quotas 
        SET requests_count = 0, last_reset = CURRENT_TIMESTAMP
        WHERE username = ? 
        AND (julianday(CURRENT_TIMESTAMP) - julianday(last_reset)) * 24 >= 24
    ''', (username,))
    
    # Obtenir le nombre actuel de requêtes
    cur.execute('SELECT requests_count FROM user_quotas WHERE username = ?', (username,))
    count = cur.fetchone()[0]
    
    if count >= max_requests:
        con.commit()
        con.close()
        return False, count
    
    # Incrémenter le compteur
    cur.execute('''
        UPDATE user_quotas 
        SET requests_count = requests_count + 1 
        WHERE username = ?
    ''', (username,))
    
    con.commit()
    con.close()
    return True, count + 1

# Fonction pour sauvegarder un SMS
def save_sms_history(username: str, message: str, classification: str, suspicious_words: list):
    con = sqlite3.connect("messages.db")
    cur = con.cursor()
    
    cur.execute('''
        INSERT INTO sms_history (username, message, classification, suspicious_words)
        VALUES (?, ?, ?, ?)
    ''', (username, message, classification, ",".join(suspicious_words) if suspicious_words else ""))
    
    con.commit()
    con.close()

# Fonction utilitaire pour vérifier si l'utilisateur est connecté
def is_user_logged_in(request: Request):
    return request.cookies.get("username") is not None

@app.on_event("startup")
async def startup_event():
    '''
    L'objectif est de créer une base de données avec les données présentes dans les fichiers csv
    Pour le traitement des messages spam.
    '''
    # Connexion à la base de données 
    con = sqlite3.connect("messages.db")
    cur = con.cursor()

    cur.execute(''' 
        CREATE TABLE IF NOT EXISTS messages 
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            content TEXT NOT NULL
        )
        ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS mots_spam
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL
        )
    ''')

    # Vider les tables avant d'insérer les nouvelles données
    cur.execute('DELETE FROM messages')
    cur.execute('DELETE FROM mots_spam')

    csv_file = "mots_uniques_spam.csv"
    with open(csv_file, encoding="utf-8") as f:
        csv_reader = csv.reader(f)  # Pas de délimiteur, chaque ligne contient un seul mot
        next(csv_reader)  # Ignorer l'en-tête
        for row in csv_reader:
            if len(row) == 1:  # Chaque ligne contient un mot
                mot = row[0] 
                cur.execute('''
                INSERT INTO mots_spam (word)
                VALUES (?)
                ''', (mot,))

    csv_file = "SMSSpamCollection.csv"
    with open(csv_file, encoding="utf-8") as f:
        csv_reader = csv.reader(f, delimiter=';')
        for row in csv_reader:
            if len(row) == 2:
                message_type, message_content = row
                cur.execute('''
                INSERT INTO messages (type, content)
                VALUES (?, ?)
                ''', (message_type, message_content))

    con.commit()
    con.close()
    print("Données insérées avec succès dans la base de données SQLite.")

@app.get("/")
async def root(request: Request):
    # Rediriger vers login si non connecté
    if not is_user_logged_in(request):
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "Détecteur de Spam",
            "heading": "Bienvenue dans l'application de détection de spam"
        }
    )

@app.post("/resultats")
async def resultats(request: Request, message: str = Form()):
    if not is_user_logged_in(request):
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    username = request.cookies.get("username")
    quota_ok, current_count = check_quota(username)
    
    if not quota_ok:
        return templates.TemplateResponse(
            "resultats.html",
            {
                "request": request,
                "title": "Limite atteinte",
                "error": "Vous avez atteint votre limite de 10 requêtes par jour.",
                "quota_count": current_count
            }
        )

    # Convertir le message en ensemble de mots
    input_words = set(message.lower().split())
    suspicious_words = []
    
    # 1. Vérifier les mots uniques de spam
    con = sqlite3.connect("messages.db")
    cur = con.cursor()
    
    cur.execute('SELECT word FROM mots_spam')
    spam_words_unique = set(row[0].lower() for row in cur.fetchall())
    
    # Si un mot est dans la liste des mots uniques de spam
    for word in input_words:
        if word in spam_words_unique:
            suspicious_words.append(word)
    
    if suspicious_words:
        result = "SPAM"
    else:
        # 2. Comparer avec la collection SMS
        cur.execute('''
            SELECT content, type FROM messages 
            WHERE type IN ('spam', 'ham')
        ''')
        sms_collection = cur.fetchall()
        
        max_spam_words = 0
        max_ham_words = 0
        spam_matching_words = set()
        ham_matching_words = set()
        
        for content, msg_type in sms_collection:
            msg_words = set(content.lower().split())
            common_words = input_words.intersection(msg_words)
            
            if msg_type.lower() == 'spam' and len(common_words) > max_spam_words:
                max_spam_words = len(common_words)
                spam_matching_words = common_words
            elif msg_type.lower() == 'ham' and len(common_words) > max_ham_words:
                max_ham_words = len(common_words)
                ham_matching_words = common_words
        
        # Décision basée sur la similarité
        if max_spam_words >= 5 and max_spam_words > max_ham_words:
            result = "SPAM"
            suspicious_words = list(spam_matching_words)
        else:
            result = "Message normal"
            suspicious_words = []
    
    con.close()
    
    # Sauvegarder l'historique
    save_sms_history(username, message, result, suspicious_words)
    
    return templates.TemplateResponse(
        "resultats.html",
        {
            "request": request,
            "title": "Résultat de l'analyse",
            "message": message,
            "result": result,
            "suspicious_words": suspicious_words,
            "quota_count": current_count
        }
    )

# Routes pour l'authentification
@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, username: str = Form(), password: str = Form()):
    # Hasher le mot de passe
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    
    # Vérifier les credentials
    con = sqlite3.connect("messages.db")
    cur = con.cursor()
    cur.execute("SELECT * FROM users WHERE username=? AND password=?", 
                (username, hashed_password))
    user = cur.fetchone()
    con.close()
    
    if user:
        response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        response.set_cookie(key="username", value=username)
        return response
    else:
        return templates.TemplateResponse(
            "login.html", 
            {"request": request, "error": "Nom d'utilisateur ou mot de passe incorrect"}
        )

@app.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def register(
    request: Request, 
    username: str = Form(), 
    password: str = Form(), 
    confirm_password: str = Form()
):
    if password != confirm_password:
        return templates.TemplateResponse(
            "register.html", 
            {"request": request, "error": "Les mots de passe ne correspondent pas"}
        )
    
    # Hasher le mot de passe
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    
    try:
        con = sqlite3.connect("messages.db")
        cur = con.cursor()
        cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", 
                   (username, hashed_password))
        con.commit()
        con.close()
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    except sqlite3.IntegrityError:
        return templates.TemplateResponse(
            "register.html", 
            {"request": request, "error": "Ce nom d'utilisateur existe déjà"}
        )

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("username")
    return response

# Nouvelle route pour voir l'historique
@app.get("/history")
async def history(request: Request):
    if not is_user_logged_in(request):
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    username = request.cookies.get("username")
    
    con = sqlite3.connect("messages.db")
    cur = con.cursor()
    
    cur.execute('''
        SELECT message, classification, suspicious_words, timestamp 
        FROM sms_history 
        WHERE username = ? 
        ORDER BY timestamp DESC
    ''', (username,))
    
    history = cur.fetchall()
    con.close()
    
    return templates.TemplateResponse(
        "history.html",
        {
            "request": request,
            "title": "Historique des analyses",
            "history": history
        }
    )

class SMSHistory(BaseModel):
    id: int
    message: str
    classification: str  # Maintenant uniquement "SPAM" ou "Message normal"
    suspicious_words: Optional[str]
    timestamp: str
    username: str

@app.get("/api/history/filter", response_model=List[SMSHistory])
async def filter_history(
    request: Request,
    classification: Optional[str] = None,  # Maintenant uniquement "SPAM" ou "Message normal"
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    if not is_user_logged_in(request):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Non authentifié"
        )
    
    username = request.cookies.get("username")
    
    query = '''
        SELECT id, message, classification, suspicious_words, timestamp, username
        FROM sms_history 
        WHERE username = ?
    '''
    params = [username]
    
    if classification:
        query += ' AND classification = ?'
        params.append(classification)
    
    if start_date:
        query += ' AND timestamp >= ?'
        params.append(start_date)
    
    if end_date:
        query += ' AND timestamp <= ?'
        params.append(end_date)
    
    query += ' ORDER BY timestamp DESC'
    
    con = sqlite3.connect("messages.db")
    cur = con.cursor()
    cur.execute(query, params)
    history = cur.fetchall()
    con.close()
    
    return [
        SMSHistory(
            id=row[0],
            message=row[1],
            classification=row[2],
            suspicious_words=row[3],
            timestamp=row[4],
            username=row[5]
        ) for row in history
    ]