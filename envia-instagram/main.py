import asyncio
import os
import pandas as pd
import random
import shutil
from playwright.async_api import async_playwright

import sys
import re

CSV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dados-instagram", "dados-insta.csv"))

# Configurações de Contas
INSTAGRAM_ACCOUNTS = [
    {"user": "dentalpage.software", "pass": "56263877@"},
    {"user": "dentalpage.software2", "pass": "56263877@"},
    {"user": "dentalpage.software3", "pass": "56263877@"},
    {"user": "dentalpage.software4", "pass": "56263877@"},
    {"user": "dentalpage_empresa", "pass": "56263877"},
    {"user": "dentalpage_empresa2", "pass": "56263877"},
    {"user": "dentalpage_empresa3", "pass": "56263877"},
    {"user": "dentalpage_empresa4", "pass": "56263877"},
]

# Variações de mensagens para o Instagram
MENSAGENS_BASE = [
    "Olá {nome}, vi seu perfil e achei seu trabalho fantástico! Percebi que vocês não têm website oficial. Gostariam de conhecer alguns modelos que criamos?",
    "Oi {nome}! Tudo bem? Vi seu Instagram e notei a falta de um site na bio. Posso te mostrar como um site profissional pode elevar sua clínica?",
    "Olá {nome}, adorei o conteúdo do seu perfil! Notei que vocês ainda não possuem um site. Quer ver alguns exemplos de sites para dentistas?",
    "Tudo bem {nome}? Trabalho com criação de sites e vi que sua clínica não tem um oficial. Posso te enviar uns modelos para você dar uma olhada?",
    "Oi {nome}, sou fã do seu trabalho! Percebi que vocês não têm site. Gostaria de ver como um site moderno pode atrair mais pacientes para vocês?"
]

async def check_login_status(page):
    """Verifica se está logado ou se precisa de login."""
    try:
        # Testa se estamos em uma página que indica login
        await page.goto("https://www.instagram.com/", wait_until="domcontentloaded")
        await page.wait_for_timeout(4000)
        
        # Se a URL contém 'login', não está logado
        if "accounts/login" in page.url:
            return False

        # Procura por múltiplos indicadores de estar logado (ícones da barra lateral ou superior)
        selectors = [
            'svg[aria-label*="Notificações"]', 
            'svg[aria-label*="Explorar"]', 
            'svg[aria-label*="Página inicial"]',
            'svg[aria-label*="Messages"]',
            'svg[aria-label*="Direct"]',
            'a[href="/direct/inbox/"]',
            'img[alt*="Foto do perfil"]',
            'svg[aria-label*="Pesquisa"]'
        ]
        
        for selector in selectors:
            try:
                el = await page.query_selector(selector)
                if el and await el.is_visible():
                    return True
            except:
                continue
        return False
    except:
        return False

async def login_instagram(page, username, password):
    """Realiza o processo de login automático."""
    try:
        print(f"🔐 Tentando login automático para {username}...")
        # Adiciona um tempo de carga maior e tenta carregar a página
        await page.goto("https://www.instagram.com/accounts/login/", wait_until="load", timeout=60000)
        await page.wait_for_timeout(6000) # Espera carregar scripts
        
        # 1. Tenta remover banners de Cookies que costumam travar a página
        print("🍪 Verificando banners de cookies...")
        try:
            # Seletores amplos para botões de aceitação
            btn_cookies = page.locator('button:has-text("Permitir todos os cookies"), button:has-text("Aceitar"), button:has-text("Permitir"), button:has-text("Allow all cookies"), button:has-text("Accept")').first
            if await btn_cookies.count() > 0:
                await btn_cookies.click(timeout=3000)
                print("✅ Banner de cookies fechado.")
                await page.wait_for_timeout(2000)
        except: 
            pass

        # 2. Preencher Usuário (tenta diversos caminhos)
        print(f"⏳ Preenchendo usuário...")
        preencheu_user = False
        selectors_user = [
            'input[name="username"]',
            'input[aria-label*="usuário"]',
            'input[placeholder*="usuário"]',
            'input[type="text"]',
            'input[type="tel"]'
        ]
        
        for sel in selectors_user:
            try:
                el = page.locator(sel).first
                if await el.count() > 0:
                    # Usa force=True para preencher mesmo se o Playwright achar que está "escondido" por algum label
                    await el.fill(username, timeout=4000, force=True)
                    preencheu_user = True
                    break
            except:
                continue
        
        if not preencheu_user:
            # Última tentativa via label humano
            try:
                await page.get_by_label("Número de celular, nome de usuário ou email").fill(username, timeout=4000, force=True)
                preencheu_user = True
            except: pass

        if not preencheu_user:
            print(f"❌ Não consegui localizar o campo de usuário para {username}.")
            return False

        # 3. Preencher Senha
        print(f"⏳ Preenchendo senha...")
        preencheu_pass = False
        selectors_pass = [
            'input[name="password"]', 
            'input[type="password"]',
            'input[aria-label*="Senha"]'
        ]
        
        for sel in selectors_pass:
            try:
                el = page.locator(sel).first
                if await el.count() > 0:
                    await el.fill(password, timeout=4000, force=True)
                    preencheu_pass = True
                    break
            except:
                continue

        if not preencheu_pass:
             # Tenta via label se falhou nos seletores técnicos
             try:
                 await page.get_by_label("Senha").fill(password, timeout=4000, force=True)
                 preencheu_pass = True
             except: pass

        if not preencheu_pass:
            print(f"❌ Não consegui localizar o campo de senha para {username}.")
            return False
        
        # 4. Clicar em Entrar
        print(f"🖱️  Clicando em Entrar...")
        try:
            await page.click('button[type="submit"]', timeout=5000)
        except:
            try:
                await page.locator('button:has-text("Entrar"), button:has-text("Log In")').first.click(timeout=5000)
            except:
                await page.keyboard.press("Enter") # Último recurso
        
        # 5. Aguardar confirmação de login
        print("⏳ Aguardando confirmação (60s)...")
        try:
            # Espera por ícones de feed ou mensagens que indicam sucesso
            await page.wait_for_selector('svg[aria-label*="Notificações"], svg[aria-label*="Explorar"], a[href="/direct/inbox/"]', timeout=60000)
            print(f"✅ Login confirmado para {username}!")
            
            # Tenta pular popups chatos de salvar informações
            await page.wait_for_timeout(3000)
            for _ in range(3):
                popups = await page.query_selector_all('button:has-text("Agora não"), button:has-text("Not Now"), button:has-text("Depois"), button:has-text("Salvar informações"), button:has-text("Save Info")')
                for btn in popups:
                    if await btn.is_visible():
                        await btn.click()
                        await page.wait_for_timeout(2000)
            return True
        except:
            print(f"⚠️  Posso estar logado, mas não detectei os ícones principais para {username}.")
            # Verifica se pelo menos a URL mudou do /login/
            if "login" not in page.url:
                print("✅ URL mudou, considerando como logado!")
                return True
            return False
    except Exception as e:
        print(f"❌ Erro crítico no login para {username}: {e}")
        return False

async def send_single_test(insta_url, nome="Amigo"):
    import shutil
    user_data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "procura-instagram", "user_data"))
    
    print("\n--- Gerenciamento de Conta Instagram (Teste) ---")
    print("1. Usar conta atual (Verificar login)")
    print("2. Trocar de conta (Limpar e novo login)")
    escolha_inicial = input("Escolha uma opção: ")

    async with async_playwright() as p:
        print("\n🚀 Iniciando navegador para verificar sessão...")
        context = await p.chromium.launch_persistent_context(user_data_dir, headless=False)
        page = await context.new_page()
        await page.goto("https://www.instagram.com")
        await page.wait_for_timeout(4000)

        # Testa se está logado
        is_logged = await page.query_selector('svg[aria-label="New post"], svg[aria-label="Nova publicação"]')
        
        # Opção 1: Usar Atual
        if escolha_inicial == "1":
            if is_logged:
                print("\n✅ STATUS: Você está logado!")
                cont = input("Deseja continuar com esta conta? (S/N): ").lower()
                if cont != 's':
                    print("Operação cancelada.")
                    await context.close()
                    return
            else:
                print("\n⚠️  STATUS: Você NÃO está logado.")
                print("Por favor, faça o login agora para o robô continuar.")
                # Espera por qualquer sinal de que o login foi concluído
                # Pode ser o ícone de 'Novo Post', 'Explorar' ou 'Página Inicial'
                print("⏳ Detectando entrada na conta...")
                try:
                    await page.wait_for_selector('svg[aria-label*="post"], svg[aria-label*="publicação"], a[href="/explore/"], svg[aria-label*="Home"]', timeout=300000)
                    print("✅ Login detectado!")
                    await page.wait_for_timeout(3000)
                    
                    # Tenta fechar popups chatos de 'Salvar Informações' ou 'Notificações'
                    for _ in range(2):
                        not_now = await page.query_selector('button:has-text("Agora não"), button:has-text("Not Now"), button:has-text("Depois")')
                        if not_now:
                            await not_now.click()
                            await page.wait_for_timeout(1500)
                except:
                    print("❌ Tempo esgotado ou falha no login.")
                    await context.close()
                    return

        # Opção 2: Testar e oferecer troca
        elif escolha_inicial == "2":
            if is_logged:
                print("\n✅ STATUS: Você está logado!")
                trocar = input("Deseja realmente trocar de conta? (Isso limpará a sessão atual) (S/N): ").lower()
                if trocar == 's':
                    print("Limpando dados e reiniciando...")
                    await context.close()
                    try:
                        shutil.rmtree(user_data_dir)
                    except:
                        print("Aviso: Feche outras janelas do navegador se a limpeza falhar.")
                    
                    # Reinicia para novo login
                    context = await p.chromium.launch_persistent_context(user_data_dir, headless=False)
                    page = await context.new_page()
                    await page.goto("https://www.instagram.com")
                    print("Aguardando novo login...")
                    try:
                        await page.wait_for_selector('svg[aria-label="New post"], svg[aria-label="Nova publicação"]', timeout=300000)
                        print("✅ Novo login detectado!")
                    except:
                        print("❌ Falha no login.")
                        await context.close()
                        return
                else:
                    print("Mantendo conta atual...")
            else:
                print("\n⚠️  Você não está logado. Por favor, entre na conta desejada.")
                print("⏳ Detectando entrada na conta...")
                try:
                    await page.wait_for_selector('svg[aria-label*="post"], svg[aria-label*="publicação"], a[href="/explore/"], svg[aria-label*="Home"]', timeout=300000)
                    print("✅ Login detectado!")
                    await page.wait_for_timeout(3000)
                    
                    # Tenta fechar popups de login
                    for _ in range(2):
                        not_now = await page.query_selector('button:has-text("Agora não"), button:has-text("Not Now"), button:has-text("Depois")')
                        if not_now:
                            await not_now.click()
                            await page.wait_for_timeout(1500)
                except:
                    print("❌ Falha.")
                    await context.close()
                    return

        # Parte Comum: Enviar Mensagem
        msg = random.choice(MENSAGENS_BASE).replace("{nome}", nome)
        print(f"🚀 Indo para o perfil: {insta_url}")
        await page.goto(insta_url)
        await page.wait_for_timeout(5000)
        
        try:
            # 1. Tenta Seguir o perfil primeiro (necessário para liberar DM em muitos casos)
            print("👤 Verificando botão de Seguir...")
            follow_btn = page.locator('button, div[role="button"]').filter(has_text=re.compile(r"^Seguir$|^Follow$", re.IGNORECASE)).first
            
            if await follow_btn.count() > 0 and await follow_btn.is_visible():
                print("➕ Clicando em Seguir...")
                await follow_btn.click()
                await page.wait_for_timeout(3000) # Espera o sistema processar o follow
            else:
                print("ℹ️  Já seguindo ou botão Seguir não disponível.")

            # 2. Agora procura o botão de mensagem
            print("🔍 Procurando botão de mensagem...")
            msg_btn = page.locator('div[role="button"], button').filter(has_text=re.compile(r"Enviar mensagem|Message", re.IGNORECASE)).first
            
            if await msg_btn.count() > 0:
                print("✅ Botão encontrado! Clicando...")
                await msg_btn.click()
                
                print("⏳ Abrindo chat...")
                await page.wait_for_timeout(7000)
                
                # Digita a mensagem
                chat_box = await page.query_selector('div[role="textbox"][contenteditable="true"]')
                if chat_box:
                    await chat_box.fill(msg)
                    await page.wait_for_timeout(2000)
                    
                    # Tenta clicar no botão de enviar (setinha azul/roxa)
                    # O botão muitas vezes só aparece DEPOIS que você digita
                    print("📤 Procurando botão de enviar...")
                    send_btn = page.locator('div[role="button"]:has(svg[aria-label="Enviar"]), div[role="button"]:has(svg[aria-label="Send"]), div[role="button"]:has(svg[aria-label="Direct"])').first
                    
                    if await send_btn.count() > 0:
                        await send_btn.click()
                        print("✅ Botão de enviar clicado!")
                    else:
                        # Fallback: Tenta pressionar Enter se o botão não for achado
                        await page.keyboard.press("Enter")
                        print("⌨️  Botão não achado, enviado via Enter.")
                    
                    await page.wait_for_timeout(3000)
                    print("✅ Teste de DM finalizado!")
                else:
                    print("❌ Não encontrei a caixa de chat.")
            else:
                print("❌ Não encontrei o botão de mensagem.")
                print("Dica: Verifique se o perfil não é privado ou se você está realmente logado.")
        except Exception as e:
            print(f"❌ Erro no teste de Insta: {e}")
        
        await context.close()

async def send_instagram_dms(message_template=None, limit=50):
    if not os.path.exists(CSV_PATH):
        print("Planilha dados-insta.csv não encontrada.")
        return

    print(f"\n🚀 Iniciando campanha multi-conta. Objetivo: {limit} leads por conta.")
    
    # Prepara o diretório de sessões (uma pasta por conta para não deslogar toda hora)
    sessions_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "instagram_sessions"))
    os.makedirs(sessions_dir, exist_ok=True)

    async with async_playwright() as p:
        for account in INSTAGRAM_ACCOUNTS:
            username = account["user"]
            password = account["pass"]
            
            print("\n" + "="*60)
            print(f"👤 CONTA ATUAL: {username}")
            print("="*60)
            
            # Recarrega o CSV a cada conta para pegar o estado mais atual de 'já_foi_abordado'
            df = pd.read_csv(CSV_PATH)
            leads_pendentes = df[df["já_foi_abordado"] == "Não"]
            
            if leads_pendentes.empty:
                print("🏁 Todos os leads da planilha já foram abordados!")
                break
                
            # Seleciona os próximos leads para esta conta específica
            num_envios = min(len(leads_pendentes), limit)
            leads_da_rodada = leads_pendentes.head(num_envios)
            print(f"🎯 Preparado para enviar para {num_envios} novos leads com esta conta.")
            
            # Lança navegador persistente para esta conta
            user_data_dir = os.path.join(sessions_dir, f"session_{username}")
            context = await p.chromium.launch_persistent_context(user_data_dir, headless=False)
            page = await context.new_page()
            
            # Tenta verificar se já está logado ou faz o login
            is_logged = await check_login_status(page)
            if not is_logged:
                print(f"⚠️  Sessão expirada ou não encontrada para {username}.")
                logged_now = await login_instagram(page, username, password)
                if not logged_now:
                    print(f"⏭️  Pulando conta {username} por falha no login.")
                    await context.close()
                    continue
            else:
                print(f"✅ Sessão ativa para {username}!")

            # Loop de envio para os leads selecionados para esta conta
            logs_sucesso = 0
            for index, row in leads_da_rodada.iterrows():
                nome = str(row["nome"]) if pd.notna(row["nome"]) and str(row["nome"]).strip() != "" else "Amigo"
                url = row["instagram"]
                msg = message_template.replace("{nome}", nome) if message_template else random.choice(MENSAGENS_BASE).replace("{nome}", nome)
                
                print(f"\n📡 Lead [{logs_sucesso+1}/{num_envios}]: {nome} -> {url}")
                
                try:
                    await page.goto(url)
                    await page.wait_for_timeout(5000)
                    
                    # 1. Tenta Seguir primeiro (estratégia para evitar bloqueio e liberar DM)
                    print("➕ Verificando botão de seguir...")
                    follow_btn = page.locator('button, div[role="button"]').filter(has_text=re.compile(r"^Seguir$|^Follow$", re.IGNORECASE)).first
                    if await follow_btn.count() > 0 and await follow_btn.is_visible():
                        await follow_btn.click()
                        await page.wait_for_timeout(3000)

                    # 2. Localiza botão de DM
                    print("🔍 Procurando botão de mensagem...")
                    # Tenta múltiplos seletores por ordem de prioridade
                    msg_btn = None
                    btn_selectors = [
                        'div[role="button"]:has-text("Mensagem")',
                        'div[role="button"]:has-text("Message")',
                        'button:has-text("Enviar mensagem")',
                        'button:has-text("Message")',
                        'div[role="button"]:has(svg[aria-label="Mensagem"])',
                        'div[role="button"]:has(svg[aria-label="Message"])'
                    ]
                    
                    for sel in btn_selectors:
                        try:
                            el = page.locator(sel).first
                            if await el.count() > 0 and await el.is_visible():
                                msg_btn = el
                                break
                        except:
                            continue
                    
                    if not msg_btn:
                        print(f"❌ Botão de mensagem não encontrado para {nome}.")
                        df.at[index, "já_foi_abordado"] = "Sim"
                        df.to_csv(CSV_PATH, index=False, encoding='utf-8-sig')
                        continue
                    
                    await msg_btn.click()
                    print(f"⏳ Abrindo chat...")
                    await page.wait_for_timeout(7000)
                    
                    # Tenta fechar popups chatos que aparecem ao abrir chat
                    for _ in range(2):
                        not_now = await page.query_selector('button:has-text("Agora não"), button:has-text("Not Now"), button:has-text("Depois")')
                        if not_now:
                            await not_now.click()
                            await page.wait_for_timeout(1000)
                    
                    # 3. Digita e Envia
                    chat_box = await page.query_selector('div[role="textbox"][contenteditable="true"]')
                    if chat_box:
                        await chat_box.fill(msg)
                        await page.wait_for_timeout(2000)
                        
                        send_btn = page.locator('div[role="button"]:has(svg[aria-label="Enviar"]), div[role="button"]:has(svg[aria-label="Send"]), div[role="button"]:has(svg[aria-label="Direct"])').first
                        if await send_btn.count() > 0:
                            await send_btn.click()
                            print(f"✅ Mensagem enviada para {nome}!")
                        else:
                            await page.keyboard.press("Enter")
                            print(f"✅ Enviada via Enter para {nome}!")
                        
                        logs_sucesso += 1
                        df.at[index, "já_foi_abordado"] = "Sim"
                        df.to_csv(CSV_PATH, index=False, encoding='utf-8-sig') # Salva imediato para segurança
                    else:
                        print(f"❌ Não foi possível encontrar a caixa de texto para {nome}.")
                        df.at[index, "já_foi_abordado"] = "Sim"
                        df.to_csv(CSV_PATH, index=False, encoding='utf-8-sig')

                    # Delay entre mensagens (segurança anti-spam)
                    pause = 5
                    print(f"⏳ Aguardando {pause}s antes do próximo...")
                    await asyncio.sleep(pause)
                    
                except Exception as e:
                    print(f"⚠️ Ocorreu um erro no lead {nome}: {e}")
                    df.at[index, "já_foi_abordado"] = "Sim"
                    df.to_csv(CSV_PATH, index=False, encoding='utf-8-sig')
                    await asyncio.sleep(5)
            
            print(f"🏁 Conta {username} finalizada. Total enviado: {logs_sucesso}")
            await context.close()
            
            # Pausa maior entre a troca de contas
            if account != INSTAGRAM_ACCOUNTS[-1]:
                wait_between = 20
                print(f"\n😴 Pausa de {wait_between}s para respiro entre contas...")
                await asyncio.sleep(wait_between)

    print("\n" + "#"*40)
    print("✨ OPERAÇÃO MULTI-CONTA CONCLUÍDA! ✨")
    print("#"*40)


def menu():
    while True:
        print("\n" + "="*40)
        print("   📦 ENVIO EM MASSA - INSTAGRAM")
        print("="*40)
        print("1. Iniciar envios (Mensagens randômicas)")
        print("2. Personalizar mensagem única")
        print("3. Voltar ao menu principal")
        opcao = input("\nEscolha uma opção: ")
        
        if opcao == "1":
            try:
                qtd = int(input("\n🎯 Quantos leads deseja abordar nesta rodada? (ex: 5): "))
            except:
                qtd = 5
            asyncio.run(send_instagram_dms(limit=qtd))
        elif opcao == "2":
            print("\nDica: Use {nome} para o nome do lead.")
            msg = input("Mensagem: ")
            if msg:
                try:
                    qtd = int(input("🎯 Quantos leads deseja abordar nesta rodada? (ex: 5): "))
                except:
                    qtd = 5
                asyncio.run(send_instagram_dms(msg, limit=qtd))
        elif opcao == "3":
            return
        else:
            print("Opção inválida.")

if __name__ == "__main__":
    # Verifica se é um teste via terminal
    if "--test" in sys.argv:
        print("\n" + "="*40)
        print("   🧪 TESTE DE DM INSTAGRAM")
        print("="*40)
        url = input("Cole o link do perfil de TESTE: ")
        if url:
            asyncio.run(send_single_test(url))
            input("\nTeste finalizado! Pressione Enter para voltar...")
        exit()

    menu()
