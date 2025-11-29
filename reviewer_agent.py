"""
reviewer_agent.py
Agent Reviewer - Analyse statique du code (selon Architecture Document)
"""

from agent_base import BaseAgent

class ReviewerAgent(BaseAgent):
    """Agent qui fait l'analyse statique du code"""
    
    def __init__(self, llm_client):
        super().__init__("Reviewer", "Analyser le code (analyse statique)")
        self.llm = llm_client
    
    def work(self, code, problem, attempt):
        """Analyse le code de manière statique"""
        
        self.log(f"🔍 Analyse statique du code (Tentative {attempt})...")
        
        # Analyse du code
        analysis = self.analyze_code(code, problem)
        
        # Vérifier si c'est APPROVED ou REJECTED
        is_approved = self.check_if_approved(analysis)
        
        if is_approved:
            self.log("✅ Code APPROUVÉ par le Reviewer", "SUCCESS")
            return {
                "approved": True,
                "feedback": None,
                "analysis": analysis
            }
        else:
            self.log("❌ Code REJETÉ - Feedback envoyé au Coder", "ERROR")
            return {
                "approved": False,
                "feedback": analysis,
                "analysis": analysis
            }
    
    def analyze_code(self, code, problem):
        """Analyse le code avec le LLM"""
        
        prompt = f"""Tu es un expert en revue de code Python (Reviewer Agent).

CODE À ANALYSER :
```python
{code}
```

PROBLÈME À RÉSOUDRE : 
{problem}

TON RÔLE - ANALYSE STATIQUE (sans exécuter le code) :

✅ Vérifie ces points :
1. **Logique** : Le code résout-il logiquement le problème ?
2. **Syntaxe** : Y a-t-il des erreurs de syntaxe évidentes ?
3. **Edge Cases** : Les cas limites sont-ils gérés ?
   - Valeurs nulles (None, 0, "")
   - Valeurs négatives
   - Types de données incorrects
4. **Gestion d'erreurs** : Y a-t-il des try/except si nécessaire ?
5. **Best Practices** : 
   - Docstring présente ?
   - Noms de variables clairs ?
   - Code PEP 8 compliant ?
6. **Sécurité** : Pas de code dangereux ?

FORMAT DE RÉPONSE OBLIGATOIRE :

STATUS: [écris EXACTEMENT "APPROVED" si tout est bon, ou "REJECTED" si problèmes]

PROBLÈMES TROUVÉS: 
[Si REJECTED : liste détaillée et numérotée des problèmes]
[Si APPROVED : écris "Aucun"]

SUGGESTIONS CONCRÈTES:
[Si REJECTED : suggestions précises pour corriger chaque problème]
[Si APPROVED : écris "Code prêt pour les tests"]

---

Exemple 1 - Code avec problèmes :
STATUS: REJECTED
PROBLÈMES TROUVÉS:
1. Pas de gestion pour n < 0 (cas négatif)
2. Pas de docstring
3. Pas de gestion TypeError si n n'est pas un int
SUGGESTIONS CONCRÈTES:
1. Ajoute : if n < 0: raise ValueError("n doit être positif")
2. Ajoute une docstring expliquant la fonction
3. Ajoute : if not isinstance(n, int): raise TypeError()

Exemple 2 - Code bon :
STATUS: APPROVED
PROBLÈMES TROUVÉS: Aucun
SUGGESTIONS CONCRÈTES: Code prêt pour les tests

---

Analyse maintenant le code ci-dessus :"""
        
        self.log("🔍 Analyse en cours...")
        analysis = self.llm.generate(prompt, temperature=0.2)
        
        return analysis
    
    def check_if_approved(self, analysis):
        """Vérifie si l'analyse indique APPROVED ou REJECTED"""
        
        analysis_upper = analysis.upper()
        
        # Cherche "STATUS: APPROVED"
        if "STATUS: APPROVED" in analysis_upper or "STATUS:APPROVED" in analysis_upper:
            return True
        else:
            return False