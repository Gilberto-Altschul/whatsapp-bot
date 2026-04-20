# 🤖 Bot Financeiro WhatsApp

Registre gastos pelo WhatsApp via **texto**, **áudio** ou **foto de cupom**.  
Powered by **Gemini AI** + **Supabase** + **Twilio**.

---

## ⚡ Início rápido — do zero ao bot em ~2 horas

### Passo 1 — Clonar e instalar

```bash
# Instale as dependências
pip install -r requirements.txt

# Copie o arquivo de configuração
cp .env.example .env
```

---

### Passo 2 — Configurar o Twilio (canal WhatsApp)

1. Crie conta gratuita em https://twilio.com
2. Vá em **Messaging → Try it out → Send a WhatsApp message**
3. Siga as instruções para ativar o **Sandbox** (manda "join xxx-xxx" para o número deles)
4. Copie o **Account SID** e **Auth Token** para o `.env`

---

### Passo 3 — Configurar o Gemini

1. Acesse https://aistudio.google.com/apikey
2. Crie uma API Key
3. Cole em `GEMINI_API_KEY` no `.env`

---

### Passo 4 — Configurar o Supabase (banco de dados)

1. Crie conta gratuita em https://supabase.com
2. Crie um novo projeto
3. Vá em **SQL Editor** e cole o conteúdo de `supabase_setup.sql`
4. Copie a **Project URL** e **anon key** para o `.env`

---

### Passo 5 — Rodar o servidor local

```bash
uvicorn app.main:app --reload --port 8000
```

Teste se está funcionando:
```bash
curl http://localhost:8000/
# {"status": "ok", "bot": "Bot Financeiro WhatsApp"}
```

---

### Passo 6 — Expor para a internet com ngrok

O Twilio precisa de uma URL pública para enviar mensagens.

```bash
# Instale o ngrok: https://ngrok.com/download
ngrok http 8000
```

Copie a URL gerada (ex: `https://abc123.ngrok.io`)

---

### Passo 7 — Configurar o Webhook no Twilio

1. No painel Twilio → **Messaging → Sandbox Settings**
2. Em **"When a message comes in"**, cole:
   ```
   https://abc123.ngrok.io/webhook/whatsapp
   ```
3. Método: **HTTP POST**
4. Salve

---

### Passo 8 — Testar!

Mande uma mensagem no WhatsApp para o número do Twilio Sandbox:

```
oi
```

O bot deve responder com o menu de boas-vindas. ✅

---

## 💬 Exemplos de uso

| Você manda | Bot responde |
|---|---|
| `oi` | Menu de boas-vindas |
| `gastei 50 na pizza` | ✅ R$50 — Alimentação |
| `35 reais no uber` | ✅ R$35 — Transporte |
| `resumo` | 📊 Gastos do mês por categoria |
| `semana` | 📊 Gastos da semana |
| 🎙 Áudio "gastei 80 no mercado" | Transcreve e registra |
| 📷 Foto do cupom | Lê e registra cada item |

---

## 🗂 Estrutura do projeto

```
whatsapp-bot/
├── app/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Variáveis de ambiente
│   ├── routes/
│   │   └── webhook.py       # POST /webhook/whatsapp
│   └── services/
│       ├── message_router.py  # Roteador de mensagens
│       ├── gemini_service.py  # IA: texto, áudio, imagem
│       └── db_service.py      # Supabase: salvar e consultar
├── supabase_setup.sql       # Cria a tabela no banco
├── requirements.txt
└── .env.example
```

---

## 🚀 Deploy em produção (Railway)

```bash
# Instale o Railway CLI
npm install -g @railway/cli

# Login e deploy
railway login
railway init
railway up

# Configure as variáveis de ambiente no painel Railway
# e atualize a URL do webhook no Twilio
```

---

## 📍 Roadmap

- [x] **Fase 1** — Webhook + texto + Gemini + Supabase
- [x] **Fase 2** — Áudio (transcrição Gemini)
- [x] **Fase 3** — Foto de cupom (OCR Gemini Vision)
- [ ] **Fase 4** — Alertas de meta por categoria
- [ ] **Fase 5** — Export para Google Sheets
- [ ] **Fase 6** — Multi-usuário com registro por telefone
