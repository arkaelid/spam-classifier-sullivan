# Projet de Spam détection
Ce projet est une appli de détection de spam pour classer les messages comme spam ou non-spam. Le projet inclut une application web FastAPI pour servir le modèle et un script pour générer un grand jeu de données de messages spam et non-spam.  

## Prérequis
Python 3.8+
pip

## Installation
Clonez le dépôt :  
```bash
  git clone https://github.com/arkaelid/spam-classifier-sullivan.git
  cd spam-classifier-sullivan
```

## Installez les paquets requis :  
```bash
  pip install -r requirements.txt
```


## Lancement de l'Application Web en local

```bash
 uvicorn main:app --reload    
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