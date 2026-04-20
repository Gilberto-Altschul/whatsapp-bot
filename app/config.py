from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_whatsapp_from: str
    gemini_api_key: str
    supabase_url: str
    supabase_key: str

    class Config:
        env_file = ".env"

settings = Settings()
