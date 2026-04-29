import json
import re
import httpx
import google.generativeai as genai

from app.config import settings

genai.configure(api_key=settings.gemini_api_key)
model = genai.GenerativeModel("gemini-1.5-flash")

CATEGORIES = [
    "Alimentação", "Transporte", "Mercado", "Saúde",
    "Lazer", "Moradia", "Educação", "Outros"
]

def _parse_float(value) -> float:
    """Limpa e converte valores para float com segurança."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # Remove símbolos e troca vírgula por ponto
        clean = re.sub(r'[^\d,.]', '', value).replace(',', '.')
        try: return float(clean)
        except ValueError: return 0.0
    return 0.0


# ────────────────────────────────────────────
# 1. Classificar texto
# ────────────────────────────────────────────


async def classify_text(text: str) -> dict | None:
    text = text.strip()

    category_keywords = {
        "Pessoal": ["vestuario", "cabelereiro", "cosmetico"],
        "Alimentação": ["pizza", "lanche", "restaurante", "café", "ifood", "padaria", "janta", "almoço"],
        "Transporte": ["uber", "99", "taxi", "gasolina", "combustivel", "ônibus", "metro", "estacionamento"],
        "Mercado": ["mercado", "supermercado", "feira", "hortifruti"],
        "Saúde": ["farmacia", "remedio", "consulta", "exame", "hospital", "dentista"],
        "Lazer": ["cinema", "show", "bar", "viagem", "netflix", "spotify"],
        "Moradia": ["aluguel", "condominio", "luz", "agua", "internet", "gás", "gas"],
        "Educação": ["curso", "faculdade", "livro", "escola", "mensalidade"],
    }

    def infer_category(description: str) -> str:
        d = description.lower()
        for category, keywords in category_keywords.items():
            if any(k in d for k in keywords):
                return category
        return "Outros"

    simple_patterns = [
        r"^(?P<desc>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s\-]{1,50})\s+(?P<amount>\d+(?:[.,]\d{1,2})?)$",
        r"^(?P<amount>\d+(?:[.,]\d{1,2})?)\s+(?P<desc>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s\-]{1,50})$",
        r"^(?:gastei|paguei|comprei)\s+(?P<amount>\d+(?:[.,]\d{1,2})?)\s+(?:em|no|na|de)?\s*(?P<desc>.+)$",
    ]

    for pattern in simple_patterns:
        match = re.match(pattern, text, flags=re.IGNORECASE)
        if match:
            desc = match.group("desc").strip()
            return {
                "amount": _parse_float(match.group("amount")),
                "category": infer_category(desc),
                "description": desc,
            }

    prompt = f"""
Você é um assistente financeiro pessoal. Analise a mensagem abaixo e extraia as informações de gasto.

Mensagem: "{text}"

Categorias disponíveis: Alimentação, Transporte, Mercado, Saúde, Lazer, Moradia, Educação, Outros

Responda APENAS com JSON válido, sem explicações, sem markdown:
{{
  "is_expense": true ou false,
  "amount": valor numérico em reais,
  "category": "uma das categorias acima",
  "description": "descrição curta do gasto em português"
}}

Se não for um gasto claro, retorne {{"is_expense": false}}.
""".strip()

    try:
        response = await model.generate_content_async(prompt)
        
        # Remove possíveis blocos de código markdown que o Gemini às vezes adiciona
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        
        # Busca o conteúdo entre chaves { } de forma robusta
        match = re.search(r"\{.*\}", clean_text, re.DOTALL)
        if not match:
            return None
        data = json.loads(match.group())

        if not data.get("is_expense"):
            return None

        amount = data.get("amount")
        if amount is None:
            return None

        category = data.get("category", "Outros")
        if category not in CATEGORIES:
            category = "Outros"

        return {
            "amount": _parse_float(amount),
            "category": category,
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

        response = await model.generate_content_async([audio_part, prompt])
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

        response = await model.generate_content_async([image_part, prompt])
        
        # Busca o conteúdo do JSON de forma robusta
        match = re.search(r"\{.*\}", response.text, re.DOTALL)
        if not match:
            return None
        data = json.loads(match.group())

        items = data.get("items", [])
        if not items:
            return None

        return [
            {
                "description": i.get("description", "Item"),
                "amount": _parse_float(i.get("amount", 0)),
                "category": i.get("category", "Outros"),
            }
            for i in items
            if float(i.get("amount", 0)) > 0
        ]

    except Exception as e:
        print(f"[Gemini parse_image error] {e}")
        return None