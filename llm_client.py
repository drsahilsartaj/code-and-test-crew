"""
llm_client.py
Client pour communiquer avec Ollama
"""

import requests
import json

class OllamaClient:
    """Client pour utiliser Ollama en local"""
    
    def __init__(self, model="llama3.2", base_url="http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self.api_url = f"{base_url}/api/generate"
    
    def generate(self, prompt, temperature=0.7):
        """Génère une réponse avec Ollama"""
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "temperature": temperature
        }
        
        try:
            response = requests.post(self.api_url, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "")
        
        except requests.exceptions.ConnectionError:
            raise Exception(
                "❌ Impossible de se connecter à Ollama.\n"
                "💡 Assure-toi que 'ollama serve' tourne dans un autre terminal."
            )
        except requests.exceptions.Timeout:
            raise Exception("⏱️ Timeout - Le modèle met trop de temps à répondre.")
        except Exception as e:
            raise Exception(f"❌ Erreur Ollama : {str(e)}")
    
    def test_connection(self):
        """Teste si Ollama est accessible"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False