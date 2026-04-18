# Sistema de Automação de Leads (WhatsApp & Instagram)

E aí! Esse projeto aqui é o meu sistema completo de prospecção automática. A ideia surgiu da necessidade de encontrar leads qualificados (negócios locais e perfis específicos) e conseguir entrar em contato com eles de forma mais rápida, sem precisar fazer tudo no dedo.

## 🚀 O que ele faz?
O sistema é dividido em módulos que você controla por um menu geral:
1.  **Busca via Google Maps (WhatsApp):** Varre cidades inteiras procurando por categorias (ex: "Academia", "Dentista") e extrai os números de contato direto na planilha.
2.  **Busca via DuckDuckGo (Instagram):** Encontra perfis de Instagram baseados em palavras-chave.
3.  **Envio Automático:** Depois de coletar os dados, o script consegue abrir o WhatsApp Web ou o Instagram e enviar as mensagens de abordagem que eu configurei.

## 🛠️ Tecnologias
*   **Python** (Core do projeto)
*   **Playwright** (Pra fazer a mágica da navegação automática sem ser bloqueado fácil)
*   **Pandas** (Pra organizar toda a bagunça dos leads em CSV)
*   **Subprocess** (Pra gerenciar os módulos pelo Menu Geral)

## 📂 Estrutura
*   `procura-x/`: Scripts de extração.
*   `envia-x/`: Scripts de automação de mensagens.
*   `dados-x/`: Onde ficam salvos os meus CSVs de leads.
*   `menu_geral.py`: O "painel de controle" de tudo.

## 📦 Como usar
1.  Instala as dependências: `pip install pandas playwright`
2.  Instala o navegador: `playwright install chromium`
3.  Roda o `python menu_geral.py` e escolhe o que quer fazer.

Projeto focado em produtividade e escala. Tamo junto!
