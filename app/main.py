from fastapi import FastAPI
from app.routes import webhook

app = FastAPI(
    title="Bot Financeiro WhatsApp",
    description="Registre gastos pelo WhatsApp via texto, áudio ou foto",
    version="1.0.0"
)

app.include_router(webhook.router)

@app.get("/")
def health():
    return {"status": "ok", "bot": "Bot Financeiro WhatsApp"}
