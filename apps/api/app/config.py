from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./medisphere.db"
    jwt_secret: str = "local-development-secret-change-before-deployment"
    jwt_issuer: str = "medisphere-api"
    access_token_minutes: int = 30
    cookie_secure: bool = False
    cors_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
