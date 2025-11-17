"""
coder_agent.py
Agent qui écrit du code Python
"""

from agent_base import BaseAgent

class CoderAgent(BaseAgent):
    """Agent qui génère du code Python"""
    
    def __init__(self, llm_client):
        super().__init__("Coder", "Écrire du code Python")
        self.llm = llm_client
    
    def work(self, problem, feedback=None, attempt=1):
        """Génère du code basé sur le problème"""
        
        self.log(f"🤖 Tentative {attempt} : Analyse du problème...")
        
        # Construction du prompt
        prompt = self.create_prompt(problem, feedback)
        
        # Génération du code
        self.log("⚙️ Génération du code...")
        code = self.llm.generate(prompt, temperature=0.3)
        
        # Nettoyage du code (enlever les ```python)
        code = self.clean_code(code)
        
        self.log("✅ Code généré avec succès !", "SUCCESS")
        return code
    
    def create_prompt(self, problem, feedback):
        """Crée le prompt pour le LLM"""
        
        base_prompt = f"""Tu es un expert en programmation Python.

PROBLÈME : {problem}

INSTRUCTIONS :
- Écris UNIQUEMENT la fonction Python, rien d'autre
- Ajoute une docstring
- Gère les cas limites (edge cases)
- Gère les erreurs avec try/except si nécessaire
- Code propre et commenté

"""
        
        if feedback:
            base_prompt += f"""
❌ FEEDBACK DU TESTEUR :
{feedback}

⚠️ IMPORTANT : Corrige ces problèmes dans ta nouvelle version !

"""
        
        base_prompt += "\nÉcris maintenant la fonction Python :"
        
        return base_prompt
    
    def clean_code(self, code):
        """Nettoie le code généré (enlève les balises markdown)"""
        
        # Enlever les ```python et ```
        code = code.replace("```python", "").replace("```", "")
        
        # Enlever les espaces en début/fin
        code = code.strip()
        
        return code