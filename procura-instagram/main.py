import asyncio
import os
import pandas as pd
import urllib.parse
from playwright.async_api import async_playwright

# Configurações
CSV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dados-instagram", "dados-insta.csv"))

async def scrape_instagram_leads(search_query, max_results=20):
    async with async_playwright() as p:
        # Usar um contexto persistente para manter login se necessário
        user_data_dir = os.path.join(os.path.dirname(__file__), "user_data")
        context = await p.chromium.launch_persistent_context(user_data_dir, headless=False)
        page = await context.new_page()
        
        print(f"Buscando no DuckDuckGo: {search_query}")
        # Usando a versão HTML do DuckDuckGo que é mais estável para raspagem
        search_url = f"https://html.duckduckgo.com/html/?q={search_query.replace(' ', '+')}+site%3Ainstagram.com"
        await page.goto(search_url)
        
        await page.wait_for_timeout(2000)
        
        # Coletar links do Instagram
        # Na versão HTML, os links reais costumam estar em a.result__url
        results = await page.query_selector_all('a')
        insta_urls = []
        
        for res in results:
            href = await res.get_attribute("href")
            if href:
                # O DuckDuckGo às vezes coloca o link real dentro de um parâmetro 'uddg'
                if "uddg=" in href:
                    parsed = urllib.parse.urlparse(href)
                    href = urllib.parse.parse_qs(parsed.query).get('uddg', [href])[0]
                
                if "instagram.com/" in href and not any(x in href for x in ["/p/", "/reels/", "/explore/", "duckduckgo", "/reel/"]):
                    # Limpa a URL para pegar apenas o perfil base
                    clean_url = href.split('?')[0].split('#')[0].rstrip('/')
                    if clean_url not in insta_urls and len(clean_url.split('/')) == 4: # https://www.instagram.com/user
                        insta_urls.append(clean_url)

        print(f"DEBUG: Encontrados {len(insta_urls)} perfis potenciais.")

        
        count = 0
        for url in insta_urls:
            if count >= max_results:
                break
            
            try:
                # Extrai o username para usar como nome, sem precisar carregar o perfil
                name = url.split("/")[-1].strip('/')
                if not name or name == "instagram": continue

                new_lead = {
                    "nome": name,
                    "instagram": url,
                    "já_foi_abordado": "Não"
                }
                
                if save_to_csv(new_lead):
                    print(f"✨ [IG LEAD!] {name} | 📸 {url}")
                    count += 1

            except Exception as e:
                print(f"Erro ao processar {url}: {e}")
                continue
                
        await context.close()
        return count


def save_to_csv(new_lead):
    # Salva um único lead por vez para garantir registro imediato
    df_new = pd.DataFrame([new_lead])
    
    file_exists = os.path.exists(CSV_PATH)
    
    try:
        if file_exists:
            df_old = pd.read_csv(CSV_PATH, encoding='utf-8-sig')
            if new_lead['instagram'] in df_old['instagram'].values:
                return False
            df_new.to_csv(CSV_PATH, mode='a', index=False, header=False, encoding='utf-8-sig')
        else:
            df_new.to_csv(CSV_PATH, index=False, encoding='utf-8-sig')
        return True
    except Exception as e:
        print(f"❌ Erro ao salvar lead no Instagram: {e}")
        return False

def menu():
    from search_config import SEARCH_TERMS, BRAZIL_LOCATIONS
    import random
    import shutil

    # Pergunta sobre o login antes de começar as buscas
    user_data_dir = os.path.join(os.path.dirname(__file__), "user_data")
    if os.path.exists(user_data_dir):
        print("\n--- Gerenciamento de Conta Instagram ---")
        print("Já existe uma conta logada neste computador.")
        escolha_login = input("Deseja (1) Continuar com a conta atual ou (2) Logar em outra conta? ")
        
        if escolha_login == "2":
            print("Limpando dados da conta anterior... Você precisará logar novamente na próxima janela.")
            try:
                # Remove a pasta de dados para forçar novo login
                shutil.rmtree(user_data_dir)
            except Exception as e:
                print(f"Aviso: Não foi possível limpar todos os arquivos (podem estar em uso). Erro: {e}")

    while True:
        print("\n" + "="*40)
        print("   📸 BUSCADOR DE CLIENTES (INSTAGRAM)")
        print("="*40)
        print("1. Iniciar busca AUTOMÁTICA por todo o Brasil")
        print("2. Iniciar busca MANUAL (Termo específico)")
        print("3. Voltar ao Menu Principal")
        opcao = input("\nEscolha uma opção: ")
        
        if opcao == "1":
            try:
                meta_leads = int(input("\n🎯 Quantos novos perfis deseja encontrar? (ex: 20): "))
            except:
                meta_leads = 5
            
            print(f"\n🚀 Iniciando varredura estratégica no Instagram...")
            total_encontrados = 0
            
            while total_encontrados < meta_leads:
                termo = random.choice(SEARCH_TERMS)
                cidade = random.choice(BRAZIL_LOCATIONS)
                query = f"{termo} em {cidade}"
                
                falta = meta_leads - total_encontrados
                print(f"\n🔎 Analisando {termo} em {cidade}... (Faltam {falta} leads)")
                
                encontrados_rodada = asyncio.run(scrape_instagram_leads(query, falta))
                total_encontrados += encontrados_rodada
                
                # Pausa de segurança removida conforme solicitação do usuário
            
            print(f"\n✅ SUCESSO! Você tem {total_encontrados} novos leads do Instagram.")
            input("\nPressione Enter para voltar ao menu...")
            return

        elif opcao == "2":
            termo = input("\nO que deseja buscar no Instagram? ")
            try:
                max_r = int(input("Quantos leads deseja extrair? "))
            except:
                max_r = 10
            
            print(f"\n🔎 Iniciando busca por: {termo}...")
            asyncio.run(scrape_instagram_leads(termo, max_r))
            print("\n✅ Busca finalizada!")
            input("\nPressione Enter para voltar ao menu...")
            return
        elif opcao == "3":
            return
        else:
            print("Opção inválida.")

if __name__ == "__main__":
    menu()
