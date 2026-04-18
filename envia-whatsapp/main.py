import asyncio
import os
import pandas as pd
import random
import shutil
from playwright.async_api import async_playwright

import sys

CSV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dados-whatsapp", "dados-whats.csv"))

# Variações de mensagens para evitar SPAM
MENSAGENS_BASE = [
    "Olá {nome}, percebi que vocês não possuem website oficial. Posso te mostrar alguns de nossos modelos?",
    "Oi {nome}! Notei que sua clínica ainda não tem um site. Gostaria de ver como um site profissional pode ajudar vocês?",
    "Tudo bem {nome}? Vi que vocês não têm site cadastrado no Google. Posso te enviar uns modelos de sites para clínicas?",
    "Olá {nome}, trabalhamos com criação de sites e vi que vocês ainda não têm um. Quer conhecer nossos modelos para dentistas?",
    "Boa tarde {nome}! Percebi a falta de um site na sua presença online. Gostaria de ver alguns exemplos de sites que fazemos?"
]

async def send_single_test(numero, nome="Amigo"):
    # Caminho ABSOLUTO para evitar confusão entre pastas
    user_data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "whatsapp_data"))
    
    print("\n--- Gerenciamento de Conta WhatsApp (Teste) ---")
    print("1. Usar conta atual (Verificar login)")
    print("2. Trocar de conta (Limpar e novo login)")
    escolha_inicial = input("Escolha uma opção: ")

    async with async_playwright() as p:
        print("\n🚀 Iniciando navegador para verificar sessão...")
        context = await p.chromium.launch_persistent_context(user_data_dir, headless=False)
        page = await context.new_page()
        await page.goto("https://web.whatsapp.com")
        
        print("⏳ Analisando estado do WhatsApp (Aguarde o carregamento completo)...")
        
        # Sinais de que está LOGADO:
        # data-testid="chat-list" -> Lista de conversas
        # data-testid="intro-text" -> Tela de boas vindas
        # [aria-label="Conversas"] -> Barra lateral
        logged_in_selectors = [
            '[data-testid="chat-list"]',
            '[data-testid="intro-text"]',
            '[aria-label="Conversas"]',
            '[aria-label="Chats"]',
            '#pane-side'
        ]
        
        # Sinais de que está DESLOGADO:
        # canvas -> Onde desenha o QR Code
        # [data-testid="qrcode"] -> Container do QR
        logged_out_selectors = [
            'canvas',
            '[data-testid="qrcode"]'
        ]

        login_detected = False
        try:
            # Espera 20 segundos por qualquer sinal (Logado ou Deslogado)
            all_selectors = logged_in_selectors + logged_out_selectors
            await page.wait_for_selector(", ".join(all_selectors), timeout=30000)
            
            # Verifica se encontrou algum de logado
            for sel in logged_in_selectors:
                if await page.query_selector(sel):
                    login_detected = True
                    break
        except:
            login_detected = False

        # Opção 1: Usar Atual
        if escolha_inicial == "1":
            if login_detected:
                print("\n✅ STATUS: WhatsApp CONECTADO!")
                cont = input("Deseja continuar com esta conta? (S/N): ").lower()
                if cont != 's':
                    print("Operação cancelada.")
                    await context.close()
                    return
            else:
                print("\n⚠️  STATUS: WhatsApp DESCONECTADO.")
                print("Por favor, escaneie o QR Code na janela do navegador para continuar.")
                try:
                    await page.wait_for_selector('[data-testid="chat-list"]', timeout=120000)
                    print("✅ Login detectado!")
                except:
                    print("❌ Tempo esgotado para o QR Code.")
                    await context.close()
                    return

        # Opção 2: Trocar de conta
        elif escolha_inicial == "2":
            if login_detected:
                print("\n✅ STATUS: Existe uma conta conectada.")
                trocar = input("Deseja desconectar e trocar de conta? (S/N): ").lower()
                if trocar == 's':
                    print("Limpando sessão e reiniciando...")
                    await context.close()
                    try:
                        shutil.rmtree(user_data_dir)
                    except:
                        print("Aviso: Feche outras janelas se a limpeza falhar.")
                    
                    # Abre novamente para novo QR code
                    context = await p.chromium.launch_persistent_context(user_data_dir, headless=False)
                    page = await context.new_page()
                    await page.goto("https://web.whatsapp.com")
                    print("Aguardando novo escaneamento de QR Code...")
                    try:
                        await page.wait_for_selector('[data-testid="chat-list"]', timeout=120000)
                        print("✅ Novo login detectado!")
                    except:
                        print("❌ Tempo limite de login esgotado.")
                        await context.close()
                        return
                else:
                    print("Mantendo conta atual...")
            else:
                print("\n⚠️  Aparelho desconectado. Por favor, escaneie o QR Code.")
                try:
                    await page.wait_for_selector('[data-testid="chat-list"]', timeout=120000)
                    print("✅ Login detectado!")
                except:
                    print("❌ Falha no login.")
                    await context.close()
                    return

        # Parte Comum: Enviar o Teste
        msg = random.choice(MENSAGENS_BASE).replace("{nome}", nome)
        print(f"\n🚀 Enviando TESTE para {numero}...")
        
        await page.goto(f"https://web.whatsapp.com/send?phone={numero}&text={msg}")
        
        try:
            # Espera a caixa de mensagem específica do chat carregar
            await page.wait_for_selector('div[contenteditable="true"]', timeout=40000)
            await page.wait_for_timeout(3000)
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(3000)
            print("✅ Teste enviado com sucesso!")
        except Exception as e:
            print(f"❌ Erro ao enviar teste: {e}")
        
        await context.close()

async def send_messages(message_template=None, limit=None):
    if not os.path.exists(CSV_PATH):
        print("❌ Planilha dados-whats.csv não encontrada.")
        return

    df = pd.read_csv(CSV_PATH)
    leads = df[df["já_foi_abordado"] == "Não"]

    if leads.empty:
        print("ℹ️  Nenhum lead pendente na planilha.")
        return

    # Se houver limite, pega apenas a quantidade pedida
    if limit and limit > 0:
        leads = leads.head(limit)

    print(f"🚀 Iniciando envio para {len(leads)} leads no WhatsApp...")

    user_data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "whatsapp_data"))
    
    print("\n--- Gerenciamento de Conta WhatsApp ---")
    print("1. Usar conta atual (Verificar login)")
    print("2. Trocar de conta (Limpar e novo login)")
    escolha_inicial = input("Escolha uma opção: ")

    async with async_playwright() as p:
        print("\n🚀 Iniciando navegador para verificar sessão...")
        context = await p.chromium.launch_persistent_context(user_data_dir, headless=False)
        page = await context.new_page()
        await page.goto("https://web.whatsapp.com")
        
        print("⏳ Analisando estado do WhatsApp (Aguarde o carregamento completo)...")
        
        logged_in_selectors = [
            '[data-testid="chat-list"]',
            '[data-testid="intro-text"]',
            '[aria-label="Conversas"]',
            '[aria-label="Chats"]',
            '#pane-side'
        ]
        
        logged_out_selectors = [
            'canvas',
            '[data-testid="qrcode"]'
        ]

        login_detected = False
        try:
            all_selectors = logged_in_selectors + logged_out_selectors
            await page.wait_for_selector(", ".join(all_selectors), timeout=30000)
            
            for sel in logged_in_selectors:
                if await page.query_selector(sel):
                    login_detected = True
                    break
        except:
            login_detected = False

        # Opção 1: Usar Atual
        if escolha_inicial == "1":
            if login_detected:
                print("\n✅ STATUS: WhatsApp CONECTADO!")
                cont = input("Deseja continuar com esta conta? (S/N): ").lower()
                if cont != 's':
                    print("Operação cancelada.")
                    await context.close()
                    return
            else:
                print("\n⚠️  STATUS: WhatsApp DESCONECTADO.")
                print("Por favor, escaneie o QR Code na janela do navegador para continuar.")
                try:
                    await page.wait_for_selector('[data-testid="chat-list"]', timeout=300000)
                    print("✅ Login detectado!")
                except:
                    print("❌ Tempo esgotado para o QR Code.")
                    await context.close()
                    return

        # Opção 2: Trocar de conta
        elif escolha_inicial == "2":
            if login_detected:
                print("\n✅ STATUS: Existe uma conta conectada.")
                trocar = input("Deseja desconectar e trocar de conta? (S/N): ").lower()
                if trocar == 's':
                    print("Limpando sessão e reiniciando...")
                    await context.close()
                    try:
                        shutil.rmtree(user_data_dir)
                    except:
                        print("Aviso: Feche outras janelas se a limpeza falhar.")
                    
                    context = await p.chromium.launch_persistent_context(user_data_dir, headless=False)
                    page = await context.new_page()
                    await page.goto("https://web.whatsapp.com")
                    print("Aguardando novo escaneamento de QR Code...")
                    try:
                        await page.wait_for_selector('[data-testid="chat-list"]', timeout=300000)
                        print("✅ Novo login detectado!")
                    except:
                        print("❌ Tempo limite de login esgotado.")
                        await context.close()
                        return
                else:
                    print("Mantendo conta atual...")
            else:
                print("\n⚠️  Aparelho desconectado. Por favor, escaneie o QR Code.")
                try:
                    await page.wait_for_selector('[data-testid="chat-list"]', timeout=300000)
                    print("✅ Login detectado!")
                except:
                    print("❌ Falha no login.")
                    await context.close()
                    return

        # --- Início do Envio em Massa ---
        for index, row in leads.iterrows():
            nome = row["nome"]
            telefone = row["telefone_formatado"]
            
            if message_template:
                msg = message_template.replace("{nome}", nome)
            else:
                msg = random.choice(MENSAGENS_BASE).replace("{nome}", nome)
            
            print(f"\n📡 Enviando para: {nome} ({telefone})...")
            
            try:
                link = f"https://web.whatsapp.com/send?phone={telefone}&text={msg}"
                await page.goto(link)
                
                await page.wait_for_selector('div[contenteditable="true"]', timeout=40000)
                await page.wait_for_timeout(3000)
                
                await page.keyboard.press("Enter")
                await page.wait_for_timeout(2000)
                
                df.at[index, "já_foi_abordado"] = "Sim"
                df.to_csv(CSV_PATH, index=False, encoding='utf-8-sig')
                
                print(f"✅ Mensagem enviada para {nome}!")
                
                delay = 5
                print(f"⏳ Pausa: {delay}s...")
                await asyncio.sleep(delay)
                
            except Exception as e:
                print(f"⚠️ Erro ao enviar para {nome}: {e}")
                # Mesmo com erro, marca como abordado para não travar o bot nas próximas vezes
                df.at[index, "já_foi_abordado"] = "Sim"
                df.to_csv(CSV_PATH, index=False, encoding='utf-8-sig')
                continue

        await context.close()

def menu():
    while True:
        print("\n" + "="*40)
        print("   📦 ENVIO EM MASSA - WHATSAPP")
        print("="*40)
        print("1. Iniciar envios (Usar mensagens randômicas)")
        print("2. Personalizar mensagem única")
        print("3. Voltar ao menu principal")
        opcao = input("\nEscolha uma opção: ")
        
        if opcao == "1":
            try:
                qtd = int(input("\n🎯 Quantos leads deseja abordar nesta rodada? (ex: 10): "))
            except:
                qtd = 10
            asyncio.run(send_messages(limit=qtd))
        elif opcao == "2":
            print("\nDica: Use {nome} para o nome do lead.")
            msg = input("Mensagem: ")
            if msg:
                try:
                    qtd = int(input("🎯 Quantos leads deseja abordar nesta rodada? (ex: 10): "))
                except:
                    qtd = 10
                asyncio.run(send_messages(msg, limit=qtd))
        elif opcao == "3":
            return
        else:
            print("Opção inválida.")

if __name__ == "__main__":
    # Verifica se é um teste via terminal
    if "--test" in sys.argv:
        print("\n" + "="*40)
        print("   🧪 TESTE DE ENVIO WHATSAPP")
        print("="*40)
        num = input("Digite o número com DDD (ex: 11999999999): ")
        if num:
            # Garante formato com 55 no início
            num_clean = "".join(filter(str.isdigit, num))
            if not num_clean.startswith("55"):
                num_clean = "55" + num_clean
            
            asyncio.run(send_single_test(num_clean))
            input("\nTeste finalizado! Pressione Enter para voltar...")
        exit()

    menu()
