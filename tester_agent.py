"""
tester_agent.py
Agent qui teste et analyse le code
"""

from agent_base import BaseAgent

class TesterAgent(BaseAgent):
    """Agent qui teste le code généré"""
    
    def __init__(self, llm_client):
        super().__init__("Tester", "Tester et analyser le code")
        self.llm = llm_client
    
    def work(self, code, problem, attempt):
        """Teste le code et retourne le résultat"""
        
        self.log(f"🧪 Test du code (Tentative {attempt})...")
        
        # Analyse du code
        analysis = self.analyze_code(code, problem)
        
        # Vérifier si ça passe
        is_passing = self.check_if_passing(analysis)
        
        if is_passing:
            self.log("✅ Tous les tests sont passés !", "SUCCESS")
            return {
                "pass": True,
                "feedback": None,
                "analysis": analysis
            }
        else:
            self.log("❌ Tests échoués - Envoi du feedback", "ERROR")
            return {
                "pass": False,
                "feedback": analysis,
                "analysis": analysis
            }
    
    def analyze_code(self, code, problem):
        """Analyse le code avec le LLM"""
        
        prompt = f"""Tu es un expert en tests et qualité de code Python.

CODE À ANALYSER :
```python
{code}
```

PROBLÈME À RÉSOUDRE : {problem}

ANALYSE À FAIRE :
1. ✅ Le code résout-il correctement le problème ?
2. 🐛 Y a-t-il des bugs évidents ?
3. ⚠️ Les cas limites sont-ils gérés ? (valeurs nulles, négatives, chaînes vides, etc.)
4. 🛡️ La gestion des erreurs est-elle présente ?
5. 📝 Le code est-il propre et lisible ?

FORMAT DE RÉPONSE OBLIGATOIRE :
STATUS: [écris exactement "PASS" si tout est bon, ou "FAIL" si problèmes]
PROBLÈMES: [liste détaillée des problèmes trouvés, ou "Aucun"]
SUGGESTIONS: [suggestions concrètes pour corriger]

Exemple de réponse :
STATUS: FAIL
PROBLÈMES: 
- Pas de gestion pour n < 0
- Pas de docstring
SUGGESTIONS:
- Ajoute une condition if n < 0: raise ValueError()
- Ajoute une docstring expliquant la fonction
"""
        
        self.log("🔍 Analyse en cours...")
        analysis = self.llm.generate(prompt, temperature=0.2)
        
        return analysis
    
    def check_if_passing(self, analysis):
        """Vérifie si l'analyse indique PASS ou FAIL"""
        
        # Cherche "STATUS: PASS" dans l'analyse
        analysis_upper = analysis.upper()
        
        if "STATUS: PASS" in analysis_upper or "STATUS:PASS" in analysis_upper:
            return True
        else:
            return False