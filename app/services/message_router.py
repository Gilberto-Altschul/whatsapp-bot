from app.services.gemini_service import (
    classify_text,
    transcribe_audio,
    parse_image,
)
from app.services.db_service import save_expense, get_monthly_summary


HELP_TEXT = """
👋 Olá! Sou seu *Bot Financeiro*.

Você pode me enviar:
📝 *Texto* — "gastei 50 no mercado"
🎙 *Áudio* — grave falando o gasto
📷 *Foto* — foto do cupom ou boleto

Comandos especiais:
• *resumo* — ver gastos do mês
• *semana* — ver gastos da semana
• *ajuda* — ver esta mensagem
""".strip()


async def route_message(phone: str, msg_type: str, payload: str) -> str:
    """
    Roteia a mensagem para o serviço correto e retorna a resposta.
    """

    # ── Comandos especiais ──
    if msg_type == "text":
        lower = payload.lower().strip()

        if lower in ("oi", "olá", "ola", "start", "comecar", "começar"):
            return HELP_TEXT

        if lower in ("ajuda", "help", "menu"):
            return HELP_TEXT

        if lower in ("resumo", "resumo do mês", "resumo do mes"):
            return await _build_summary(phone, period="month")

        if lower in ("semana", "essa semana", "resumo semana"):
            return await _build_summary(phone, period="week")

    # ── Processar gasto por texto ──
    if msg_type == "text":
        return await _handle_text(phone, payload)

    # ── Processar gasto por áudio ──
    if msg_type == "audio":
        return await _handle_audio(phone, payload)

    # ── Processar gasto por foto ──
    if msg_type == "image":
        return await _handle_image(phone, payload)

    return "❓ Não entendi o tipo de mensagem. Digite *ajuda* para ver as opções."


# ────────────────────────────────────────────
# Handlers internos
# ────────────────────────────────────────────

async def _handle_text(phone: str, text: str) -> str:
    result = await classify_text(text)

    print(f"Texto recebido: {text}")
    print(f"Resultado da classificação: {result}")

    if not result:
        return (
            "🤔 Não consegui identificar um gasto nessa mensagem.\n\n"
            "Tente: _'gastei 50 reais no mercado'_ ou _'pizza 35'_"
        )

    expense = await save_expense(
        phone=phone,
        amount=result["amount"],
        category=result["category"],
        description=result["description"],
        source="text",
    )

    monthly = await _get_category_total(phone, result["category"])

    return (
        f"✅ *Registrado!*\n"
        f"💰 R$ {result['amount']:.2f}\n"
        f"{_category_emoji(result['category'])} {result['category']}\n"
        f"📝 _{result['description']}_\n\n"
        f"Total em {result['category']} esse mês: *R$ {monthly:.2f}*"
    )


async def _handle_audio(phone: str, audio_url: str) -> str:
    transcript = await transcribe_audio(audio_url)

    if not transcript:
        return "❌ Não consegui entender o áudio. Pode tentar em texto?"

    # Aproveita o mesmo fluxo de texto com a transcrição
    result = await classify_text(transcript)

    if not result:
        return (
            f"🎙 Ouvi: _{transcript}_\n\n"
            "🤔 Mas não identifiquei um valor. Pode repetir?"
        )

    await save_expense(
        phone=phone,
        amount=result["amount"],
        category=result["category"],
        description=result["description"],
        source="audio",
    )

    monthly = await _get_category_total(phone, result["category"])

    return (
        f"🎙 Ouvi: _{transcript}_\n\n"
        f"✅ *Registrado!*\n"
        f"💰 R$ {result['amount']:.2f}\n"
        f"{_category_emoji(result['category'])} {result['category']}\n\n"
        f"Total em {result['category']} esse mês: *R$ {monthly:.2f}*"
    )


async def _handle_image(phone: str, image_url: str) -> str:
    items = await parse_image(image_url)

    if not items:
        return "❌ Não consegui ler a imagem. Tente uma foto mais nítida do cupom."

    total = sum(i["amount"] for i in items)
    lines = "\n".join(
        f"  • {i['description']} — R$ {i['amount']:.2f}" for i in items
    )

    # Salva cada item separadamente
    for item in items:
        await save_expense(
            phone=phone,
            amount=item["amount"],
            category=item["category"],
            description=item["description"],
            source="image",
        )

    return (
        f"📷 *Cupom lido!*\n\n"
        f"{lines}\n"
        f"──────────\n"
        f"💰 *Total: R$ {total:.2f}*\n"
        f"🛒 Categoria: Mercado\n\n"
        f"✅ {len(items)} itens registrados!"
    )


async def _build_summary(phone: str, period: str) -> str:
    summary = await get_monthly_summary(phone, period)

    if not summary or summary["total"] == 0:
        return "📭 Nenhum gasto registrado ainda. Mande uma mensagem como:\n_'gastei 50 no almoço'_"

    lines = ""
    for cat, amount in sorted(summary["by_category"].items(), key=lambda x: -x[1]):
        pct = (amount / summary["total"]) * 100
        lines += f"{_category_emoji(cat)} {cat} — R$ {amount:.2f} ({pct:.0f}%)\n"

    period_label = "mês" if period == "month" else "semana"
    alert = ""
    if summary.get("top_category"):
        alert = f"\n⚠️ Maior gasto: *{summary['top_category']}*"

    return (
        f"📊 *Resumo da {period_label}:*\n\n"
        f"{lines}"
        f"──────────\n"
        f"💸 *Total: R$ {summary['total']:.2f}*"
        f"{alert}"
    )


async def _get_category_total(phone: str, category: str) -> float:
    summary = await get_monthly_summary(phone, "month")
    return summary.get("by_category", {}).get(category, 0.0)


def _category_emoji(category: str) -> str:
    emojis = {
        "Alimentação": "🍔",
        "Transporte": "🚗",
        "Mercado": "🛒",
        "Saúde": "💊",
        "Lazer": "🎬",
        "Moradia": "🏠",
        "Educação": "📚",
        "Outros": "📦",
    }
    return emojis.get(category, "💰")
