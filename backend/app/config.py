from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "KHOJO API"
    app_version: str = "1.1.0"
    environment: str = "development"

    database_url: str = ""

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_key: str = ""
    supabase_bucket_case_photos: str = "case-photos"
    supabase_bucket_not_match_photos: str = "not-match-photos"

    # Hugging Face (primary aging provider)
    hf_token: str = ""
    hf_aging_model: str = "nateraw/sam"

    # Colab fallback (secondary aging provider)
    colab_aging_url: str = ""

    # OpenAI (primary LLM)
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_prompt_version: str = "v1"
    gpt4o_enabled: bool = True

    # Groq (fallback LLM)
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # Master mock toggle — when True every AI service uses deterministic stubs.
    use_mock_ai: bool = False

    # Audit signing
    audit_signing_secret: str = "dev-insecure-do-not-use-in-production"

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24

    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
