"""
main.py
Fichier principal pour lancer le système multi-agents (3 agents)
"""

from llm_client import OllamaClient
from coder_agent import CoderAgent
from reviewer_agent import ReviewerAgent
from tester_agent_v2 import RealTesterAgent as TesterAgent
from orchestrator_3agents import ThreeAgentOrchestrator

def display_menu():
    """Affiche le menu des exemples"""
    
    examples = [
        "Écris une fonction qui retourne le factoriel d'un nombre",
        "Écris une fonction qui vérifie si une chaîne est un palindrome",
        "Écris une fonction qui retourne le nième nombre de Fibonacci",
        "Écris une fonction qui inverse une liste",
        "Écris une fonction qui trouve la valeur maximale dans une liste",
        "Écris une fonction qui compte les voyelles dans une chaîne",
        "Écris une fonction qui vérifie si un nombre est premier"
    ]
    
    print("\n" + "="*70)
    print("📚 EXEMPLES DE PROBLÈMES")
    print("="*70)
    
    for i, example in enumerate(examples, 1):
        print(f"{i}. {example}")
    
    print("="*70)
    
    return examples

def get_multiline_problem():
    """Permet à l'utilisateur de saisir un problème sur plusieurs lignes"""
    
    print("\n" + "="*70)
    print("📝 DÉCRIS TON PROBLÈME (plusieurs lignes possibles)")
    print("="*70)
    print("\n💡 Instructions :")
    print("  - Tape ton problème sur plusieurs lignes si nécessaire")
    print("  - Pour terminer : tape une ligne vide (appuie juste sur Entrée)")
    print("  - Sois le plus précis possible sur ce que tu veux")
    print("\n" + "─"*70)
    print("Commence à écrire :\n")
    
    lines = []
    while True:
        try:
            line = input()
            if line.strip() == "":
                if len(lines) > 0:
                    break
                else:
                    print("⚠️  Tu dois écrire au moins une ligne !")
                    continue
            lines.append(line)
        except EOFError:
            break
    
    problem = "\n".join(lines)
    
    print("\n" + "─"*70)
    print("✅ Problème enregistré !")
    print("─"*70)
    
    return problem

def save_code(code, filename):
    """Sauvegarde le code dans un fichier"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(code)
        print(f"✅ Code sauvegardé dans : {filename}")
        return True
    except Exception as e:
        print(f"❌ Erreur de sauvegarde : {e}")
        return False

def main():
    """Fonction principale"""
    
    print("\n" + "="*70)
    print("🤖 CODE GENERATION CREW - Système 3 Agents")
    print("="*70)
    print("👥 Agents : Coder → Reviewer → Tester")
    print("="*70)
    
    # 1. Configuration du client LLM
    print("\n⚙️ Configuration du système...")
    
    model = input("Quel modèle Ollama utiliser ? (défaut: gemma3:1b) : ").strip()
    if not model:
        model = "gemma3:1b"
    
    llm = OllamaClient(model=model)
    
    # Test de connexion
    print(f"🔌 Test de connexion à Ollama ({model})...")
    if not llm.test_connection():
        print("\n" + "="*70)
        print("❌ ERREUR : Impossible de se connecter à Ollama")
        print("="*70)
        print("\n💡 SOLUTION :")
        print("1. Ouvre un nouveau terminal")
        print("2. Lance : ollama serve")
        print("3. Laisse ce terminal ouvert")
        print("4. Reviens ici et relance ce programme")
        print("\n" + "="*70)
        return
    
    print("✅ Connexion réussie !\n")
    
    # 2. Création des 3 agents
    print("🔧 Création des agents...")
    coder = CoderAgent(llm)
    reviewer = ReviewerAgent(llm)
    tester = TesterAgent(llm)
    print("✅ 3 Agents créés : Coder, Reviewer, Tester\n")
    
    # 3. Création de l'orchestrateur
    print("🎭 Création de l'orchestrateur...")
    crew = ThreeAgentOrchestrator(coder, reviewer, tester, max_attempts=3)
    print("✅ Orchestrateur créé !\n")
    
    # 4. Menu des exemples
    examples = display_menu()
    
    # 5. Choix du problème
    choice = input("\nChoix (1-7 pour exemple, 'm' pour multi-lignes) : ").strip().lower()
    
    if choice == 'm':
        problem = get_multiline_problem()
    elif choice.isdigit() and 1 <= int(choice) <= len(examples):
        problem = examples[int(choice) - 1]
    else:
        problem = choice
    
    if not problem or problem.strip() == "":
        print("❌ Aucun problème fourni. Abandon.")
        return
    
    print("\n" + "="*70)
    print("📋 PROBLÈME À RÉSOUDRE :")
    print("="*70)
    print(problem)
    print("="*70)
    
    # 6. Lancement du système
    result = crew.run(problem)
    
    # 7. Affichage du résultat final
    print("\n" + "="*70)
    print("📊 RÉSULTAT FINAL")
    print("="*70)
    
    if result["success"]:
        print(f"✅ Statut : SUCCÈS")
        print(f"🔢 Tentatives : {result['attempts']}/{crew.max_attempts}")
        print("\n📝 CODE GÉNÉRÉ :")
        print("─"*70)
        print(result['code'])
        print("─"*70)
        
        # Option de sauvegarde
        save = input("\n💾 Sauvegarder le code ? (o/n) : ").strip().lower()
        if save == 'o':
            filename = input("Nom du fichier (ex: factorial.py) : ").strip()
            if not filename:
                filename = "generated_code.py"
            save_code(result['code'], filename)
    
    else:
        print(f"❌ Statut : ÉCHEC")
        print(f"🔢 Tentatives : {result['attempts']}/{crew.max_attempts}")
        
        if result.get('code'):
            print("\n📝 DERNIER CODE GÉNÉRÉ (non validé) :")
            print("─"*70)
            print(result['code'])
            print("─"*70)
        
        if result.get('last_feedback'):
            print("\n💬 DERNIER FEEDBACK :")
            print("─"*70)
            print(result['last_feedback'])
            print("─"*70)
    
    print("\n" + "="*70)
    print("👋 Merci d'avoir utilisé Code Generation Crew !")
    print("="*70 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Programme interrompu par l'utilisateur.")
    except Exception as e:
        print(f"\n\n❌ Erreur fatale : {e}")