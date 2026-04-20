import json
import httpx
import google.generativeai as genai

from app.config import settings

genai.configure(api_key=settings.gemini_api_key)
model = genai.GenerativeModel("gemini-1.5-flash")

CATEGORIES = [
    "Alimentação", "Transporte", "Mercado", "Saúde",
    "Lazer", "Moradia", "Educação", "Outros"
]


# ────────────────────────────────────────────
# 1. Classificar texto
# ────────────────────────────────────────────

async def classify_text(text: str) -> dict | None:
    """
    Extrai valor, categoria e descrição de uma mensagem de texto.
    Retorna None se não identificar um gasto.
    """
    prompt = f"""
Você é um assistente financeiro pessoal. Analise a mensagem abaixo e extraia as informações de gasto.

Mensagem: "{text}"

Categorias disponíveis: {", ".join(CATEGORIES)}

Responda APENAS com JSON válido, sem explicações, sem markdown:
{{
  "is_expense": true ou false,
  "amount": valor numérico em reais (ex: 50.00),
  "category": "uma das categorias acima",
  "description": "descrição curta do gasto em português"
}}

Se não for um gasto claro, retorne {{"is_expense": false}}.
""".strip()

    try:
        response = model.generate_content(prompt)
        raw = response.text.strip().replace("```json", "").replace("```", "")
        data = json.loads(raw)

        if not data.get("is_expense"):
            return None

        return {
            "amount": float(data["amount"]),
            "category": data.get("category", "Outros"),
            "description": data.get("description", text[:60]),
        }
    except Exception as e:
        print(f"[Gemini classify_text error] {e}")
        return None


# ────────────────────────────────────────────
# 2. Transcrever áudio
# ────────────────────────────────────────────

async def transcribe_audio(audio_url: str) -> str | None:
    """
    Baixa o áudio do Twilio e usa Gemini para transcrever.
    """
    try:
        # Baixa o arquivo de áudio
        async with httpx.AsyncClient(
            auth=(settings.twilio_account_sid, settings.twilio_auth_token)
        ) as client:
            resp = await client.get(audio_url)
            audio_bytes = resp.content
            content_type = resp.headers.get("content-type", "audio/ogg")

        # Envia para Gemini com instrução de transcrição
        prompt = (
            "Transcreva exatamente o que foi dito neste áudio em português. "
            "Retorne apenas o texto transcrito, sem pontuação extra."
        )

        audio_part = {
            "inline_data": {
                "mime_type": content_type,
                "data": audio_bytes,
            }
        }

        response = model.generate_content([audio_part, prompt])
        return response.text.strip()

    except Exception as e:
        print(f"[Gemini transcribe_audio error] {e}")
        return None


# ────────────────────────────────────────────
# 3. Ler imagem / cupom fiscal
# ────────────────────────────────────────────

async def parse_image(image_url: str) -> list[dict] | None:
    """
    Lê uma foto de cupom fiscal ou boleto e extrai os itens e valores.
    """
    try:
        # Baixa a imagem
        async with httpx.AsyncClient(
            auth=(settings.twilio_account_sid, settings.twilio_auth_token)
        ) as client:
            resp = await client.get(image_url)
            image_bytes = resp.content
            content_type = resp.headers.get("content-type", "image/jpeg")

        prompt = f"""
Analise esta imagem. Pode ser um cupom fiscal, nota fiscal, boleto ou foto de uma compra.

Extraia todos os itens e valores encontrados.

Categorias disponíveis: {", ".join(CATEGORIES)}

Responda APENAS com JSON válido:
{{
  "items": [
    {{
      "description": "nome do item ou descrição",
      "amount": valor numérico em reais,
      "category": "categoria mais apropriada"
    }}
  ]
}}

Se for um boleto ou conta, retorne um único item com o valor total.
Se não conseguir ler, retorne {{"items": []}}.
""".strip()

        image_part = {
            "inline_data": {
                "mime_type": content_type,
                "data": image_bytes,
            }
        }

        response = model.generate_content([image_part, prompt])
        raw = response.text.strip().replace("```json", "").replace("```", "")
        data = json.loads(raw)

        items = data.get("items", [])
        if not items:
            return None

        return [
            {
                "description": i.get("description", "Item"),
                "amount": float(i.get("amount", 0)),
                "category": i.get("category", "Outros"),
            }
            for i in items
            if float(i.get("amount", 0)) > 0
        ]

    except Exception as e:
        print(f"[Gemini parse_image error] {e}")
        return None
