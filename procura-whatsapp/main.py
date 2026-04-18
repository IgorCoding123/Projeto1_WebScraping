import asyncio
import os
import pandas as pd
import re
from playwright.async_api import async_playwright
from datetime import datetime

# Configurações
CSV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dados-whatsapp", "dados-whats.csv"))

def format_phone(phone_str):
    # Remove tudo que não é dígito
    digits = re.sub(r'\D', '', phone_str)
    if not digits:
        return ""
    
    # Remove o zero inicial se existir (ex: 084 -> 84)
    if digits.startswith('0'):
        digits = digits[1:]
        
    # Se já tem o DDI 55 na frente, não mexe (comum em números de 12 ou 13 dígitos)
    if digits.startswith('55') and len(digits) >= 12:
        return digits
        
    # Para números de 10 (Fixo) ou 11 (Celular) dígitos, adiciona 55
    if len(digits) in [10, 11]:
        return "55" + digits
        
    return digits

async def scrape_google_maps(search_query, max_results=20):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False) # Headless=False para o usuário ver
        page = await browser.new_page()
        
        print(f"Buscando por: {search_query}")
        await page.goto(f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}")
        
        # Espera carregar os resultados
        await page.wait_for_timeout(5000)
        
        results = []
        
        # Scroll dinâmico para carregar o máximo de resultados (rolagem infinita no feed lateral)
        print("Rolando resultados para carregar mais...")
        for _ in range(15): # Aumentado para pegar mais leads
            # Tenta encontrar o container do feed lateral para rolar
            feed_selector = 'div[role="feed"]'
            feed_exists = await page.query_selector(feed_selector)
            if feed_exists:
                await page.hover(feed_selector)
                await page.mouse.wheel(0, 3000)
            else:
                await page.mouse.wheel(0, 2000)
            await page.wait_for_timeout(1500)

        # Seleciona os cards de resultados
        cards = await page.query_selector_all('div[role="article"]')
        
        count = 0
        for card in cards:
            if count >= max_results:
                break
            
            try:
                # Tenta clicar no card para ver detalhes
                await card.click()
                await page.wait_for_timeout(2000)
                
                # Nome
                name_el = await page.query_selector('h1.DUwDvf')
                name = await name_el.inner_text() if name_el else "Desconhecido"
                
                # Website (Botão de website)
                website_el = await page.query_selector('a[aria-label*="Website"], a[aria-label*="website"], a[data-item-id="authority"]')
                if website_el:
                    # print(f"Ignorando {name} (Possui website)")
                    continue
                
                # Telefone
                phone_el = await page.query_selector('button[aria-label^="Telefone:"], button[data-item-id^="phone:tel:"], button[aria-label^="Phone:"]')
                phone = ""
                
                if not phone_el:
                    text_content = await page.content()
                    phone_match = re.search(r'\(\d{2}\)\s\d{4,5}-\d{4}', text_content)
                    if phone_match:
                        phone = phone_match.group()
                else:
                    phone = await phone_el.get_attribute("aria-label") or await phone_el.get_attribute("data-item-id")
                    phone = phone.replace("Telefone: ", "").replace("Phone: ", "").replace("phone:tel:", "")
                
                if phone:
                    phone_formatted = format_phone(phone)
                    new_lead = {
                        "nome": name,
                        "telefone": phone,
                        "telefone_formatado": phone_formatted,
                        "já_foi_abordado": "Não"
                    }
                    
                    # SALVAMENTO IMEDIATO AQUI
                    if save_to_csv(new_lead):
                        print(f"✨ [NOVO LEAD!] {name} | 📞 {phone}")
                        count += 1
                
            except Exception as e:
                continue
                
        await browser.close()
        return count

def save_to_csv(new_lead):
    # Função agora salva um único lead por vez para garantir o registro imediato
    df_new = pd.DataFrame([new_lead])
    
    file_exists = os.path.exists(CSV_PATH)
    
    try:
        if file_exists:
            # Lê apenas para verificar duplicata e não re-escrever o arquivo inteiro a toa
            df_old = pd.read_csv(CSV_PATH, encoding='utf-8-sig')
            if new_lead['telefone_formatado'] in df_old['telefone_formatado'].values:
                # print(f"Lead {new_lead['nome']} já existe na planilha. Pulando...")
                return False
            
            # Append no arquivo
            df_new.to_csv(CSV_PATH, mode='a', index=False, header=False, encoding='utf-8-sig')
        else:
            # Cria o arquivo com header
            df_new.to_csv(CSV_PATH, index=False, encoding='utf-8-sig')
        
        # print(f"DEBUG: Escrito no CSV fixo: {CSV_PATH}")
        return True
    except Exception as e:
        print(f"❌ Erro ao salvar lead: {e}")
        return False

def menu():
    from search_config import SEARCH_TERMS, BRAZIL_LOCATIONS
    import random

    while True:
        print("\n" + "="*40)
        print("   🔍 BUSCADOR DE CLIENTES (WHATSAPP)")
        print("="*40)
        print("1. Iniciar busca AUTOMÁTICA por todo o Brasil")
        print("2. Iniciar busca MANUAL (Termo específico)")
        print("3. Voltar ao Menu Principal")
        opcao = input("\nEscolha uma opção: ")
        
        if opcao == "1":
            try:
                meta_leads = int(input("\n🎯 Quantos novos leads você deseja encontrar hoje? (ex: 50): "))
            except:
                meta_leads = 10
            
            print(f"\n🚀 Iniciando varredura em {len(BRAZIL_LOCATIONS)} cidades...")
            total_encontrados = 0
            
            while total_encontrados < meta_leads:
                termo = random.choice(SEARCH_TERMS)
                cidade = random.choice(BRAZIL_LOCATIONS)
                query = f"{termo} em {cidade}"
                
                falta = meta_leads - total_encontrados
                print(f"\n🔎 Buscando {termo} em {cidade}... (Faltam {falta} leads)")
                
                # Cada rodada tenta pegar o máximo possível para chegar na meta
                encontrados_rodada = asyncio.run(scrape_google_maps(query, falta))
                total_encontrados += encontrados_rodada
                
                if total_encontrados < meta_leads:
                    # Pausa estratégica entre cidades
                    wait = random.randint(10, 20)
                    print(f"⏳ Pausa de segurança: {wait}s...")
                    import time
                    time.sleep(wait)
            
            print(f"\n✅ MISSÃO CUMPRIDA! Você conseguiu {total_encontrados} novos leads.")
            input("\nPressione Enter para voltar ao menu...")
            return # Volta para o menu_geral

        elif opcao == "2":
            termo = input("\nO que deseja buscar? (ex: Dentista em Curitiba): ")
            try:
                max_r = int(input("Quantos leads deseja extrair desta busca? "))
            except:
                max_r = 20
            
            print(f"\n🔎 Buscando: {termo}...")
            asyncio.run(scrape_google_maps(termo, max_r))
            print("\n✅ Busca finalizada!")
            input("\nPressione Enter para voltar ao menu...")
            return # Volta para o menu_geral
        elif opcao == "3":
            return
        else:
            print("Opção inválida.")

if __name__ == "__main__":
    menu()
