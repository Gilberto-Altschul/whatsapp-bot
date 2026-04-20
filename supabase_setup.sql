-- Cole este SQL no Supabase SQL Editor
-- https://supabase.com/dashboard → SQL Editor → New Query

CREATE TABLE IF NOT EXISTS expenses (
    id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    phone       TEXT NOT NULL,          -- ex: +5511999999999
    amount      NUMERIC(10,2) NOT NULL,
    category    TEXT NOT NULL,
    description TEXT,
    source      TEXT DEFAULT 'text',    -- text | audio | image
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Índice para buscas por telefone + data (usadas no resumo)
CREATE INDEX IF NOT EXISTS idx_expenses_phone_date
    ON expenses (phone, created_at DESC);

-- Linha de teste (opcional — apague depois)
INSERT INTO expenses (phone, amount, category, description, source)
VALUES ('+5511999999999', 50.00, 'Alimentação', 'Teste inicial', 'text');
