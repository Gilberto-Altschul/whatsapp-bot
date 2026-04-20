from datetime import datetime, date, timedelta
from supabase import create_client, Client

from app.config import settings

supabase: Client = create_client(settings.supabase_url, settings.supabase_key)


# ────────────────────────────────────────────
# Salvar gasto
# ────────────────────────────────────────────

async def save_expense(
    phone: str,
    amount: float,
    category: str,
    description: str,
    source: str = "text",
) -> dict:
    """
    Salva um gasto na tabela 'expenses' do Supabase.
    """
    record = {
        "phone": phone,
        "amount": amount,
        "category": category,
        "description": description,
        "source": source,           # text | audio | image
        "created_at": datetime.utcnow().isoformat(),
    }

    result = supabase.table("expenses").insert(record).execute()
    return result.data[0] if result.data else record


# ────────────────────────────────────────────
# Resumo por período
# ────────────────────────────────────────────

async def get_monthly_summary(phone: str, period: str = "month") -> dict:
    """
    Retorna resumo de gastos por categoria para o período.
    period: "month" | "week"
    """
    today = date.today()

    if period == "week":
        start = today - timedelta(days=today.weekday())  # segunda-feira
    else:
        start = today.replace(day=1)  # primeiro do mês

    result = (
        supabase.table("expenses")
        .select("amount, category")
        .eq("phone", phone)
        .gte("created_at", start.isoformat())
        .execute()
    )

    rows = result.data or []

    by_category: dict[str, float] = {}
    total = 0.0

    for row in rows:
        cat = row["category"]
        amt = float(row["amount"])
        by_category[cat] = by_category.get(cat, 0.0) + amt
        total += amt

    top_category = max(by_category, key=by_category.get) if by_category else None

    return {
        "total": total,
        "by_category": by_category,
        "top_category": top_category,
        "period": period,
        "start": start.isoformat(),
    }
