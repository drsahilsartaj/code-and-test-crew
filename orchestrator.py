"""
orchestrator.py
Orchestrateur qui gère le flux entre les agents
"""

class CodeTestOrchestrator:
    """Gère le système multi-agents"""
    
    def __init__(self, coder, tester, max_attempts=6):
        self.coder = coder
        self.tester = tester
        self.max_attempts = max_attempts
    
    def run(self, problem):
        """Lance le système multi-agents"""
        
        print("\n" + "="*70)
        print("🚀 DÉMARRAGE DU SYSTÈME CODE & TEST CREW")
        print("="*70)
        print(f"📝 Problème : {problem}")
        print(f"🔄 Max tentatives : {self.max_attempts}")
        print("="*70 + "\n")
        
        current_attempt = 1
        code = None
        test_result = None
        
        while current_attempt <= self.max_attempts:
            print(f"\n{'─'*70}")
            print(f"📍 TENTATIVE {current_attempt}/{self.max_attempts}")
            print(f"{'─'*70}\n")
            
            # ÉTAPE 1 : Coder écrit le code
            try:
                code = self.coder.work(
                    problem=problem,
                    feedback=test_result["feedback"] if test_result else None,
                    attempt=current_attempt
                )
            except Exception as e:
                print(f"\n❌ Erreur Coder Agent : {e}")
                return {
                    "success": False,
                    "code": None,
                    "attempts": current_attempt,
                    "error": str(e)
                }
            
            # ÉTAPE 2 : Tester teste le code
            try:
                test_result = self.tester.work(code, problem, current_attempt)
            except Exception as e:
                print(f"\n❌ Erreur Tester Agent : {e}")
                return {
                    "success": False,
                    "code": code,
                    "attempts": current_attempt,
                    "error": str(e)
                }
            
            # ÉTAPE 3 : Vérifier le résultat
            if test_result["pass"]:
                print("\n" + "="*70)
                print(f"🎉 SUCCÈS ! Code validé à la tentative {current_attempt}/{self.max_attempts}")
                print("="*70 + "\n")
                
                return {
                    "success": True,
                    "code": code,
                    "attempts": current_attempt,
                    "analysis": test_result["analysis"]
                }
            
            elif current_attempt == self.max_attempts:
                print("\n" + "="*70)
                print(f"⚠️ ÉCHEC : Max tentatives ({self.max_attempts}) atteint")
                print("="*70 + "\n")
                
                return {
                    "success": False,
                    "code": code,
                    "attempts": current_attempt,
                    "last_feedback": test_result["feedback"]
                }
            
            else:
                print(f"\n🔄 Nouvelle tentative avec feedback...\n")
            
            current_attempt += 1
        
        return {
            "success": False,
            "code": code,
            "attempts": self.max_attempts
        }