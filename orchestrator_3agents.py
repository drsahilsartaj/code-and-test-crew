"""
orchestrator_3agents.py
Orchestrateur pour le système 3 agents : Coder → Reviewer → Tester
Selon Architecture Design Document
"""

class ThreeAgentOrchestrator:
    """Gère le workflow des 3 agents"""
    
    def __init__(self, coder, reviewer, tester, max_attempts=3):
        self.coder = coder
        self.reviewer = reviewer
        self.tester = tester
        self.max_attempts = max_attempts
        
        # État du système (AgentState)
        self.state = {
            "problem_description": None,
            "current_attempt": 0,
            "workflow_status": "not_started",
            "generated_code": None,
            "reviewer_status": None,
            "reviewer_feedback": None,
            "tester_status": None,
            "tester_results": None,
            "feedback_history": []
        }
    
    def run(self, problem):
        """Lance le système multi-agents avec workflow 3 agents"""
        
        print("\n" + "="*70)
        print("🚀 DÉMARRAGE - CODE GENERATION CREW (3 AGENTS)")
        print("="*70)
        print(f"📝 Problème : {problem[:100]}{'...' if len(problem) > 100 else ''}")
        print(f"🔄 Max tentatives : {self.max_attempts}")
        print(f"👥 Workflow : Coder → Reviewer → Tester")
        print("="*70 + "\n")
        
        # Initialiser l'état
        self.state["problem_description"] = problem
        self.state["workflow_status"] = "in_progress"
        
        current_attempt = 1
        feedback_for_coder = None
        
        while current_attempt <= self.max_attempts:
            print(f"\n{'='*70}")
            print(f"📍 TENTATIVE {current_attempt}/{self.max_attempts}")
            print(f"{'='*70}\n")
            
            self.state["current_attempt"] = current_attempt
            
            # ════════════════════════════════════════════════════════
            # PHASE 1 : CODER GÉNÈRE LE CODE
            # ════════════════════════════════════════════════════════
            print(f"{'─'*70}")
            print("🤖 PHASE 1/3 : Coder Agent")
            print(f"{'─'*70}")
            
            try:
                code = self.coder.work(
                    problem=problem,
                    feedback=feedback_for_coder,
                    attempt=current_attempt
                )
                self.state["generated_code"] = code
                
            except Exception as e:
                print(f"\n❌ Erreur Coder Agent : {e}")
                self.state["workflow_status"] = "failed"
                return {
                    "success": False,
                    "code": None,
                    "attempts": current_attempt,
                    "error": str(e)
                }
            
            # ════════════════════════════════════════════════════════
            # PHASE 2 : REVIEWER ANALYSE LE CODE
            # ════════════════════════════════════════════════════════
            print(f"\n{'─'*70}")
            print("🔍 PHASE 2/3 : Reviewer Agent")
            print(f"{'─'*70}")
            
            try:
                review_result = self.reviewer.work(code, problem, current_attempt)
                self.state["reviewer_status"] = "approved" if review_result["approved"] else "rejected"
                self.state["reviewer_feedback"] = review_result["feedback"]
                
            except Exception as e:
                print(f"\n❌ Erreur Reviewer Agent : {e}")
                self.state["workflow_status"] = "failed"
                return {
                    "success": False,
                    "code": code,
                    "attempts": current_attempt,
                    "error": str(e)
                }
            
            # Si le Reviewer REJETTE → retour au Coder
            if not review_result["approved"]:
                print(f"\n{'─'*70}")
                print("🔄 Code REJETÉ par Reviewer → Feedback au Coder")
                print(f"{'─'*70}")
                
                # Sauvegarder le feedback
                self.state["feedback_history"].append({
                    "attempt": current_attempt,
                    "source": "Reviewer",
                    "feedback": review_result["feedback"]
                })
                
                feedback_for_coder = f"""❌ FEEDBACK DU REVIEWER (Analyse Statique) :

{review_result['feedback']}

⚠️ IMPORTANT : Corrige ces problèmes identifiés par le Reviewer !
"""
                
                # Si c'est la dernière tentative
                if current_attempt == self.max_attempts:
                    print("\n" + "="*70)
                    print(f"⚠️ ÉCHEC : Max tentatives ({self.max_attempts}) atteint")
                    print("="*70 + "\n")
                    self.state["workflow_status"] = "failed"
                    return {
                        "success": False,
                        "code": code,
                        "attempts": current_attempt,
                        "last_feedback": feedback_for_coder
                    }
                
                current_attempt += 1
                continue  # Nouvelle tentative
            
            # ════════════════════════════════════════════════════════
            # PHASE 3 : TESTER EXÉCUTE LE CODE
            # ════════════════════════════════════════════════════════
            print(f"\n{'─'*70}")
            print("🧪 PHASE 3/3 : Tester Agent")
            print(f"{'─'*70}")
            
            try:
                test_result = self.tester.work(code, problem, current_attempt)
                self.state["tester_status"] = "pass" if test_result["pass"] else "fail"
                self.state["tester_results"] = test_result
                
            except Exception as e:
                print(f"\n❌ Erreur Tester Agent : {e}")
                self.state["workflow_status"] = "failed"
                return {
                    "success": False,
                    "code": code,
                    "attempts": current_attempt,
                    "error": str(e)
                }
            
            # ════════════════════════════════════════════════════════
            # VÉRIFICATION DU RÉSULTAT
            # ════════════════════════════════════════════════════════
            
            if test_result["pass"]:
                # ✅ SUCCÈS !
                print("\n" + "="*70)
                print(f"🎉 SUCCÈS ! Code validé à la tentative {current_attempt}/{self.max_attempts}")
                print("="*70)
                print("✅ Reviewer : APPROVED")
                print("✅ Tester : PASS")
                print("="*70 + "\n")
                
                self.state["workflow_status"] = "success"
                return {
                    "success": True,
                    "code": code,
                    "attempts": current_attempt,
                    "analysis": test_result["analysis"]
                }
            
            else:
                # ❌ Tests échoués
                print(f"\n{'─'*70}")
                print("❌ Tests ÉCHOUÉS → Feedback au Coder")
                print(f"{'─'*70}")
                
                # Sauvegarder le feedback
                self.state["feedback_history"].append({
                    "attempt": current_attempt,
                    "source": "Tester",
                    "feedback": test_result["feedback"]
                })
                
                feedback_for_coder = f"""✅ Code APPROUVÉ par Reviewer (analyse statique OK)
❌ Mais ÉCHEC lors des tests d'exécution

{test_result['feedback']}

⚠️ IMPORTANT : Le code passe la revue mais échoue à l'exécution !
Corrige les bugs détectés pendant les tests.
"""
                
                # Si c'est la dernière tentative
                if current_attempt == self.max_attempts:
                    print("\n" + "="*70)
                    print(f"⚠️ ÉCHEC : Max tentatives ({self.max_attempts}) atteint")
                    print("="*70 + "\n")
                    self.state["workflow_status"] = "failed"
                    return {
                        "success": False,
                        "code": code,
                        "attempts": current_attempt,
                        "last_feedback": feedback_for_coder
                    }
                
                current_attempt += 1
                continue  # Nouvelle tentative
        
        # Fin de boucle (normalement on ne devrait jamais arriver ici)
        self.state["workflow_status"] = "failed"
        return {
            "success": False,
            "code": self.state["generated_code"],
            "attempts": self.max_attempts
        }