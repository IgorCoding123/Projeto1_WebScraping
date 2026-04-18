import subprocess
import os

def run_script(path):
    # Obtém o caminho absoluto
    abs_path = os.path.abspath(path)
    abs_dir = os.path.dirname(abs_path)
    
    # Executa o script python no diretório dele (importante para caminhos relativos de dados)
    subprocess.call(["python", "main.py"], cwd=abs_dir)

def main_menu():
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print("==========================================")
        print("   SISTEMA DE AUTOMAÇÃO DE LEADS         ")
        print("==========================================")
        print("1. PROCURAR LEADS WHATSAPP (Maps)")
        print("2. PROCURAR LEADS INSTAGRAM (DuckDuckGo)")
        print("3. ENVIAR MENSAGENS WHATSAPP (Lista)")
        print("4. ENVIAR DMs INSTAGRAM (Lista)")
        print("5. [TESTE] ENVIAR WHATSAPP (Número Único)")
        print("6. [TESTE] ENVIAR INSTAGRAM (Perfil Único)")
        print("7. SAIR")
        print("==========================================")
        
        opcao = input("Escolha uma opção: ")
        
        if opcao == "1":
            run_script("procura-whatsapp/main.py")
        elif opcao == "2":
            run_script("procura-instagram/main.py")
        elif opcao == "3":
            run_script("envia-whatsapp/main.py")
        elif opcao == "4":
            run_script("envia-instagram/main.py")
        elif opcao == "5":
            # Chama o script de zap passando um argumento de teste
            abs_path = os.path.abspath("envia-whatsapp/main.py")
            subprocess.call(["python", "main.py", "--test"], cwd=os.path.dirname(abs_path))
        elif opcao == "6":
            # Chama o script de insta passando um argumento de teste
            abs_path = os.path.abspath("envia-instagram/main.py")
            subprocess.call(["python", "main.py", "--test"], cwd=os.path.dirname(abs_path))
        elif opcao == "7":
            print("Encerrando...")
            break
        else:
            input("Opção inválida! Pressione Enter para tentar novamente.")

if __name__ == "__main__":
    main_menu()
