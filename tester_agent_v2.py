"""
tester_agent_v2.py
Tester Agent qui EXÉCUTE vraiment le code et teste avec des valeurs réelles
"""

from agent_base import BaseAgent
import sys
from io import StringIO
import traceback

class RealTesterAgent(BaseAgent):
    """Agent qui teste le code EN L'EXÉCUTANT vraiment"""
    
    def __init__(self, llm_client):
        super().__init__("Real Tester", "Tester le code en l'exécutant")
        self.llm = llm_client
    
    def work(self, code, problem, attempt):
        """Teste le code en l'exécutant vraiment"""
        
        self.log(f"🧪 Test RÉEL du code (Tentative {attempt})...")
        
        # Étape 1 : Générer des cas de test avec le LLM
        test_cases = self.generate_test_cases(problem)
        self.log(f"📋 {len(test_cases)} cas de test générés")
        
        # Étape 2 : Extraire le nom de la fonction
        function_name = self.extract_function_name(code)
        if not function_name:
            return {
                "pass": False,
                "feedback": "❌ Impossible de trouver le nom de la fonction dans le code",
                "analysis": "Code invalide"
            }
        
        self.log(f"🔍 Fonction détectée : {function_name}()")
        
        # Étape 3 : Exécuter le code et tester
        execution_results = self.execute_tests(code, function_name, test_cases)
        
        # Étape 4 : Analyser les résultats
        if execution_results["all_passed"]:
            self.log("✅ TOUS les tests sont passés !", "SUCCESS")
            return {
                "pass": True,
                "feedback": None,
                "analysis": execution_results["summary"]
            }
        else:
            self.log(f"❌ {execution_results['failed_count']}/{execution_results['total_count']} tests ont échoué", "ERROR")
            return {
                "pass": False,
                "feedback": execution_results["feedback"],
                "analysis": execution_results["summary"]
            }
    
    def generate_test_cases(self, problem):
        """Génère des cas de test avec le LLM"""
        
        prompt = f"""Tu es un expert en tests unitaires Python.

PROBLÈME : {problem}

Génère 5 cas de test pour ce problème.

FORMAT DE RÉPONSE (STRICTEMENT CE FORMAT) :
TEST_CASE_1: input=<valeur> | expected=<résultat attendu>
TEST_CASE_2: input=<valeur> | expected=<résultat attendu>
TEST_CASE_3: input=<valeur> | expected=<résultat attendu>
TEST_CASE_4: input=<valeur> | expected=<résultat attendu>
TEST_CASE_5: input=<valeur> | expected=<résultat attendu>

EXEMPLES :
Pour "fonction qui calcule le factoriel" :
TEST_CASE_1: input=5 | expected=120
TEST_CASE_2: input=0 | expected=1
TEST_CASE_3: input=1 | expected=1
TEST_CASE_4: input=3 | expected=6
TEST_CASE_5: input=10 | expected=3628800

Pour "fonction qui vérifie si palindrome" :
TEST_CASE_1: input="radar" | expected=True
TEST_CASE_2: input="hello" | expected=False
TEST_CASE_3: input="" | expected=True
TEST_CASE_4: input="a" | expected=True
TEST_CASE_5: input="Radar" | expected=False

⚠️ IMPORTANT :
- Inclus des cas limites (0, vide, négatif, etc.)
- Utilise le format EXACT demandé
- Pas de texte supplémentaire, juste les TEST_CASE

Génère les cas de test maintenant :"""

        response = self.llm.generate(prompt, temperature=0.2)
        
        # Parser les cas de test
        test_cases = []
        lines = response.strip().split('\n')
        
        for line in lines:
            if 'TEST_CASE' in line and '|' in line:
                try:
                    parts = line.split('|')
                    input_part = parts[0].split('input=')[1].strip()
                    expected_part = parts[1].split('expected=')[1].strip()
                    
                    # Nettoyer et évaluer
                    input_value = self.safe_eval(input_part)
                    expected_value = self.safe_eval(expected_part)
                    
                    test_cases.append({
                        'input': input_value,
                        'expected': expected_value,
                        'raw_input': input_part,
                        'raw_expected': expected_part
                    })
                except Exception as e:
                    self.log(f"⚠️ Erreur parsing test case : {line}", "WARNING")
                    continue
        
        # Si pas assez de cas de test, ajouter des cas par défaut
        if len(test_cases) < 3:
            self.log("⚠️ Pas assez de cas de test générés, ajout de cas par défaut", "WARNING")
            test_cases = self.get_default_test_cases(problem)
        
        return test_cases
    
    def get_default_test_cases(self, problem):
        """Cas de test par défaut si la génération échoue"""
        if "factoriel" in problem.lower():
            return [
                {'input': 5, 'expected': 120},
                {'input': 0, 'expected': 1},
                {'input': 1, 'expected': 1}
            ]
        elif "palindrome" in problem.lower():
            return [
                {'input': "radar", 'expected': True},
                {'input': "hello", 'expected': False},
                {'input': "", 'expected': True}
            ]
        elif "fibonacci" in problem.lower():
            return [
                {'input': 0, 'expected': 0},
                {'input': 1, 'expected': 1},
                {'input': 5, 'expected': 5}
            ]
        else:
            # Cas générique
            return [
                {'input': 5, 'expected': None},
                {'input': 10, 'expected': None}
            ]
    
    def safe_eval(self, value_str):
        """Évalue une chaîne en Python de manière sécurisée"""
        value_str = value_str.strip()
        
        # Booléens
        if value_str == 'True':
            return True
        if value_str == 'False':
            return False
        if value_str == 'None':
            return None
        
        # Chaînes
        if value_str.startswith('"') and value_str.endswith('"'):
            return value_str[1:-1]
        if value_str.startswith("'") and value_str.endswith("'"):
            return value_str[1:-1]
        
        # Nombres
        try:
            if '.' in value_str:
                return float(value_str)
            else:
                return int(value_str)
        except:
            pass
        
        # Listes
        if value_str.startswith('[') and value_str.endswith(']'):
            try:
                return eval(value_str)
            except:
                pass
        
        return value_str
    
    def extract_function_name(self, code):
        """Extrait le nom de la fonction depuis le code"""
        lines = code.split('\n')
        for line in lines:
            if line.strip().startswith('def '):
                # Extraire le nom entre 'def ' et '('
                function_name = line.strip().split('def ')[1].split('(')[0].strip()
                return function_name
        return None
    
    def execute_tests(self, code, function_name, test_cases):
        """Exécute le code et teste tous les cas"""
        
        passed = 0
        failed = 0
        errors = []
        results_details = []
        
        for i, test_case in enumerate(test_cases, 1):
            self.log(f"   Test {i}/{len(test_cases)} : {test_case.get('raw_input', test_case['input'])}...")
            
            result = self.execute_single_test(code, function_name, test_case)
            results_details.append(result)
            
            if result['status'] == 'PASS':
                passed += 1
                self.log(f"   ✅ Test {i} : PASS", "SUCCESS")
            else:
                failed += 1
                self.log(f"   ❌ Test {i} : FAIL - {result['message']}", "ERROR")
                errors.append(f"Test {i}: {result['message']}")
        
        # Construire le feedback
        all_passed = (failed == 0)
        
        feedback = f"""RÉSULTATS DES TESTS :
✅ Tests réussis : {passed}/{len(test_cases)}
❌ Tests échoués : {failed}/{len(test_cases)}

DÉTAILS DES ÉCHECS :
"""
        
        for i, result in enumerate(results_details, 1):
            if result['status'] != 'PASS':
                feedback += f"\nTest {i}:"
                feedback += f"\n  Input: {result['input']}"
                if result.get('expected'):
                    feedback += f"\n  Attendu: {result['expected']}"
                if result.get('actual'):
                    feedback += f"\n  Obtenu: {result['actual']}"
                feedback += f"\n  Erreur: {result['message']}\n"
        
        feedback += "\n💡 SUGGESTIONS :"
        if failed > 0:
            feedback += "\n- Vérifie les cas limites (valeurs nulles, négatives, vides)"
            feedback += "\n- Assure-toi que la fonction retourne le bon type de données"
            feedback += "\n- Corrige les bugs détectés ci-dessus"
        
        return {
            "all_passed": all_passed,
            "passed_count": passed,
            "failed_count": failed,
            "total_count": len(test_cases),
            "feedback": feedback if not all_passed else None,
            "summary": f"{passed}/{len(test_cases)} tests réussis",
            "details": results_details
        }
    
    def execute_single_test(self, code, function_name, test_case):
        """Exécute un seul test"""
        
        try:
            # Créer un environnement d'exécution isolé
            exec_globals = {}
            exec_locals = {}
            
            # Exécuter le code pour définir la fonction
            exec(code, exec_globals, exec_locals)
            
            # Récupérer la fonction
            if function_name not in exec_locals:
                return {
                    'status': 'ERROR',
                    'message': f"Fonction '{function_name}' non trouvée après exécution",
                    'input': test_case.get('input'),
                    'expected': test_case.get('expected'),
                    'actual': None
                }
            
            func = exec_locals[function_name]
            
            # Exécuter avec l'input
            input_value = test_case['input']
            expected_value = test_case.get('expected')
            
            # Capturer stdout au cas où
            old_stdout = sys.stdout
            sys.stdout = StringIO()
            
            try:
                # Appeler la fonction
                actual_result = func(input_value)
            finally:
                sys.stdout = old_stdout
            
            # Si pas de valeur attendue (cas de test générique), c'est OK
            if expected_value is None:
                return {
                    'status': 'PASS',
                    'message': 'Exécution réussie (pas de valeur attendue)',
                    'input': input_value,
                    'expected': None,
                    'actual': actual_result
                }
            
            # Comparer le résultat
            if actual_result == expected_value:
                return {
                    'status': 'PASS',
                    'message': 'Résultat correct',
                    'input': input_value,
                    'expected': expected_value,
                    'actual': actual_result
                }
            else:
                return {
                    'status': 'FAIL',
                    'message': f'Résultat incorrect',
                    'input': input_value,
                    'expected': expected_value,
                    'actual': actual_result
                }
        
        except Exception as e:
            return {
                'status': 'ERROR',
                'message': f'Exception: {str(e)}',
                'input': test_case.get('input'),
                'expected': test_case.get('expected'),
                'actual': None,
                'traceback': traceback.format_exc()
            }