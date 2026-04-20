from fastapi import APIRouter, Form, Request
from fastapi.responses import PlainTextResponse
from twilio.twiml.messaging_response import MessagingResponse

from app.services.message_router import route_message

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post("/whatsapp", response_class=PlainTextResponse)
async def whatsapp_webhook(
    request: Request,
    From: str = Form(...),           # ex: whatsapp:+5511999999999
    Body: str = Form(default=""),    # texto da mensagem
    NumMedia: int = Form(default=0), # qtd de mídias (áudio ou foto)
    MediaUrl0: str = Form(default=""),
    MediaContentType0: str = Form(default=""),
):
    """
    Twilio chama este endpoint a cada mensagem recebida.
    Retorna TwiML com a resposta do bot.
    """
    phone = From.replace("whatsapp:", "")

    # Determina tipo de mensagem
    if NumMedia > 0:
        if "audio" in MediaContentType0:
            msg_type = "audio"
        elif "image" in MediaContentType0:
            msg_type = "image"
        else:
            msg_type = "unknown"
        payload = MediaUrl0
    else:
        msg_type = "text"
        payload = Body.strip()

    # Roteia para o serviço correto e obtém resposta
    reply = await route_message(
        phone=phone,
        msg_type=msg_type,
        payload=payload,
    )

    # Monta resposta TwiML
    response = MessagingResponse()
    response.message(reply)
    return str(response)
