import asyncio
import os
import pandas as pd
from playwright.async_api import async_playwright
import random
import shutil
import time

# Configurações
CSV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dados-instagram-EUA", "dados-insta-USA.csv"))

async def scrape_instagram_leads(search_query, max_results=20):
    async with async_playwright() as p:
        # Usar um contexto persistente para manter login se necessário
        user_data_dir = os.path.join(os.path.dirname(__file__), "user_data")
        context = await p.chromium.launch_persistent_context(user_data_dir, headless=False)
        page = await context.new_page()
        
        print(f"Searching on DuckDuckGo (USA): {search_query}")
        # Added kl=us-en for USA region and strictly searching for USA to avoid leaks
        await page.goto(f"https://duckduckgo.com/?q={search_query.replace(' ', '+')}+USA+site%3Ainstagram.com&kl=us-en&t=h_&ia=web")
        
        await page.wait_for_timeout(3000)
        
        # Collect Instagram links
        results = await page.query_selector_all('a')
        insta_urls = []
        for res in results:
            href = await res.get_attribute("href")
            if href and "instagram.com/" in href:
                # Filter out generic/utility pages and reels/posts
                is_utility = any(x in href for x in ["/p/", "/reels/", "/reel/", "/explore/", "/legal/", "/directory/", "duckduckgo"])
                # Extract username to check if it's just 'instagram'
                try:
                    username = href.split("instagram.com/")[1].split("/")[0].split("?")[0]
                except:
                    username = ""
                
                if not is_utility and username and username not in ["instagram", "developer", "about", "explore"]:
                    if href not in insta_urls:
                        insta_urls.append(href)
        
        leads = []
        count = 0
        
        for url in insta_urls:
            if count >= max_results:
                break
            
            try:
                print(f"Analyzing profile: {url}")
                await page.goto(url)
                await page.wait_for_timeout(5000) # Safe delay
                
                # Check for login requirement (URL or presence of login form/modal)
                if "login" in page.url or await page.query_selector('input[name="username"]'):
                    print("\n⚠️ ATTENTION: LOGIN REQUIRED!")
                    print("Please log in to your Instagram account in the opened browser window.")
                    print("The bot will wait for you to complete the login...")
                    # Wait for a typical element present only after login (header, nav, home icon)
                    await page.wait_for_selector('nav, [aria-label*="Home"], [aria-label*="Página inicial"], svg[aria-label="Instagram"]', timeout=300000)
                    print("✅ Login detected! Resuming...")
                    # Wait a bit more for the profile to reload/settle
                    await page.goto(url)
                    await page.wait_for_timeout(5000)

                # Get real name (more precise and updated selectors)
                # Instagram often puts the name in the first span after the username h2
                name = ""
                name_selectors = [
                    'header section span', 
                    'header h1', 
                    'header h2',
                    'header section div:nth-child(2) span',
                    'span[dir="auto"]'
                ]
                
                for selector in name_selectors:
                    name_el = await page.query_selector(selector)
                    if name_el:
                        text = await name_el.inner_text()
                        # Clean name and check if it's not a utility word
                        text = text.strip()
                        if text and len(text) > 1 and text.lower() not in ["instagram", "login", "entrar", "cadastrar-se", "sign up", "seguindo", "seguidores", "posts"]:
                            name = text
                            break
                
                # Fallback: if no Display Name is found, use the username from the URL
                if not name:
                    # Extract username from URL as a last resort
                    username_fallback = url.split("/")[-1].strip('/')
                    if username_fallback and username_fallback.lower() != "instagram":
                        name = username_fallback
                        print(f"ℹ️ Using username as fallback for: {url}")
                
                # Validation: Skip if still no name or invalid
                if not name:
                    print(f"⚠️ Skipping invalid profile: {url} (No name/username found)")
                    continue
                
                # Try to click 'more' button in bio (text)
                try:
                    more_btn = await page.query_selector('span:has-text("... more"), span:has-text("... mais"), button:has-text("more"), button:has-text("mais")')
                    if more_btn:
                        await more_btn.click()
                        await page.wait_for_timeout(1000)
                except:
                    pass

                # Removida verificação de website - agora adiciona todos os perfis qualificados

                
                # FINAL FILTER: Check for Brazilian indicators AND Low Quality (Gems, etc.)
                bio_section = await page.query_selector('header section')
                bio_text = await bio_section.inner_text() if bio_section else ""
                bio_text = bio_text.lower()
                
                brazilian_indicators = [
                    "rua ", "avenida ", "bairro ", "centro ", "cep:", "br-", "brasil", 
                    "agende seu", "odontologia", "dentista", "clínica", "unidade", "agende sua"
                ]
                
                low_quality_indicators = [
                    "tooth gem", "toothgem", "jewelry", "grillz", "body art", "piercing",
                    "beauty plug", "lash tech", "microblading", "vibe"
                ]

                is_brazilian = any(indicator in bio_text for indicator in brazilian_indicators)
                is_low_quality = any(indicator in bio_text for indicator in low_quality_indicators)
                
                # Address detection to avoid saving address as name
                is_address = any(char.isdigit() for char in name[:5]) and ("," in name or "rd" in name.lower() or "st" in name.lower())

                if not is_brazilian and not is_low_quality:
                    # If name is an address, try to find a better name in the bio
                    if is_address:
                        possible_name = await page.inner_text('header section h2')
                        if possible_name and not any(char.isdigit() for char in possible_name[:3]):
                            print(f"🔄 Correcting address name '{name}' to '{possible_name}'")
                            name = possible_name

                    new_lead = {
                        "nome": name,
                        "instagram": url,
                        "já_foi_abordado": "Não"
                    }
                    if save_to_csv(new_lead):
                        print(f"✨ [USA IG LEAD FOUND!] {name} | 📸 {url}")
                        count += 1
                elif is_brazilian:
                    print(f"🚫 Removing Brazilian leak: {name}")
                elif is_low_quality:
                    print(f"💎 Removing low quality (Gem/Jewelry): {name}")
                else:
                    # print(f"Skipping {name} (Has website: {web_link})")
                    pass

            except Exception as e:
                print(f"Error processing {url}: {e}")
                continue
                
        await context.close()
        return count

def save_to_csv(new_lead):
    # Save lead immediately
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
        print(f"❌ Error saving lead to CSV: {e}")
        return False

def menu():
    from search_config import SEARCH_TERMS, USA_LOCATIONS
    
    # Check for existing user data
    user_data_dir = os.path.join(os.path.dirname(__file__), "user_data")
    if os.path.exists(user_data_dir):
        print("\n--- Instagram Account Management ---")
        print("Existing account detected.")
        escolha_login = input("Do you want to (1) Continue with current account or (2) Log in with a different account? ")
        
        if escolha_login == "2":
            print("Clearing login data... You will need to log in again in the next window.")
            try:
                shutil.rmtree(user_data_dir)
            except Exception as e:
                print(f"Warning: Could not clear all files. Error: {e}")

    while True:
        print("\n" + "="*45)
        print("   📸 CLIENT FINDER USA (INSTAGRAM - NO WEBSITE)")
        print("="*45)
        print("1. Start AUTOMATIC search across USA")
        print("2. Start MANUAL search (Specific term)")
        print("3. Exit")
        opcao = input("\nChoose an option: ")
        
        if opcao == "1":
            try:
                meta_leads = int(input("\n🎯 How many new leads do you want to find? (e.g., 20): "))
            except:
                meta_leads = 5
            
            print(f"\n🚀 Starting strategic scan in the USA...")
            total_encontrados = 0
            
            while total_encontrados < meta_leads:
                termo = random.choice(SEARCH_TERMS)
                cidade = random.choice(USA_LOCATIONS)
                query = f"{termo} in {cidade}"
                
                falta = meta_leads - total_encontrados
                print(f"\n🔎 Searching for {termo} in {cidade}... ({falta} leads remaining)")
                
                encontrados_rodada = asyncio.run(scrape_instagram_leads(query, falta))
                total_encontrados += encontrados_rodada
                
                # Pausa de segurança removida conforme solicitação do usuário
            
            print(f"\n✅ SUCCESS! You found {total_encontrados} new Instagram leads in the USA.")
            input("\nPress Enter to return to menu...")
            return

        elif opcao == "2":
            termo = input("\nWhat term do you want to search for on Instagram? ")
            try:
                max_r = int(input("How many leads do you want to extract? "))
            except:
                max_r = 10
            
            print(f"\n🔎 Starting search for: {termo}...")
            asyncio.run(scrape_instagram_leads(termo, max_r))
            print("\n✅ Search completed!")
            input("\nPress Enter to return to menu...")
            return
        elif opcao == "3":
            return
        else:
            print("Invalid option.")

if __name__ == "__main__":
    menu()
