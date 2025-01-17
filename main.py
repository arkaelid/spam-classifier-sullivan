from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import sqlite3
import csv

# Créer l'instance FastAPI
app = FastAPI()

# Monter les fichiers statiques
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configurer les templates
templates = Jinja2Templates(directory="templates")

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

    csv_file = "mots_uniques_spam.csv"
    with open(csv_file, encoding="utf-8") as f:
        csv_reader = csv.reader(f)  # Pas de délimiteur, chaque ligne contient un seul mot
        next(csv_reader) # Pour les 
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
    # Connexion à la base de données
    con = sqlite3.connect("messages.db")
    cur = con.cursor()
    
    # Récupérer les mots uniques de spam
    cur.execute('SELECT word FROM mots_spam')
    spam_words_unique = set(row[0].lower() for row in cur.fetchall())
    
    # Convertir le message d'entrée en ensemble de mots
    input_words = set(message.lower().split())
    
    # Variables pour stocker les mots suspects
    suspicious_words = []
    
    # Vérifier les mots uniques de spam
    for word in input_words:
        if word in spam_words_unique:
            suspicious_words.append(word)
    
    if suspicious_words:
        result = "SPAM"
    else:
        # Récupérer tous les messages spam et ham de la base
        cur.execute('SELECT content, type FROM messages')
        all_messages = cur.fetchall()
        
        max_spam_words = 0
        max_ham_words = 0
        spam_matching_words = set()
        ham_matching_words = set()
        
        # Comparer avec chaque message
        for msg_content, msg_type in all_messages:
            msg_words = set(msg_content.lower().split())
            common_words = input_words.intersection(msg_words)
            
            if msg_type.lower() == 'spam' and len(common_words) > max_spam_words:
                max_spam_words = len(common_words)
                spam_matching_words = common_words
            elif msg_type.lower() == 'ham' and len(common_words) > max_ham_words:
                max_ham_words = len(common_words)
                ham_matching_words = common_words
        
        # Déterminer le résultat
        if max_spam_words >= 5 and max_spam_words > max_ham_words:
            result = "SPAM"
            suspicious_words = list(spam_matching_words)
        elif max_ham_words >= 5:
            result = "HAMEÇONNAGE"
            suspicious_words = list(ham_matching_words)
        else:
            result = "Message normal"
            suspicious_words = []
    
    con.close()
    
    return templates.TemplateResponse(
        "resultats.html",
        {
            "request": request,
            "title": "Résultat de l'analyse",
            "message": message,
            "result": result,
            "suspicious_words": suspicious_words
        }
    )