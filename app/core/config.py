from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Bulk Certificate Generator"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/certificates"
    CERTIFICATE_OUTPUT_DIR: str = "certificates_output"

    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore")

settings = Settings()
