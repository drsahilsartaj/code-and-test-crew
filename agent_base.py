"""
agent_base.py
Classe de base pour tous les agents
"""

import time
from datetime import datetime

class BaseAgent:
    """Classe de base pour créer des agents"""
    
    def __init__(self, name, role):
        self.name = name
        self.role = role
        self.history = []
    
    def log(self, message, level="INFO"):
        """Enregistre et affiche les actions de l'agent"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = {
            "agent": self.name,
            "message": message,
            "level": level,
            "timestamp": timestamp
        }
        self.history.append(entry)
        
        # Affichage avec couleurs
        color = {
            "INFO": "\033[94m",    # Bleu
            "SUCCESS": "\033[92m", # Vert
            "ERROR": "\033[91m",   # Rouge
            "WARNING": "\033[93m"  # Jaune
        }.get(level, "\033[0m")
        
        reset = "\033[0m"
        print(f"{color}[{timestamp}] [{self.name}] {message}{reset}")
    
    def work(self, *args, **kwargs):
        """Méthode abstraite - à implémenter dans les sous-classes"""
        raise NotImplementedError(f"{self.name} doit implémenter la méthode work()")