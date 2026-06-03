from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Saliency Video Compression API"
    API_PREFIX: str = "/api"

    CLOUDFARE_ACC_ID: str
    # R2_ACCESS_KEY_ID: str
    CLOUDFLARE_API_KEY: str
    R2_BUCKET_NAME: str
    CLOUDFLARE_ACCESS_KEY: str
    CLOUDFLARE_SECRET_KEY: str

    MONGO_URI: str
    DB_NAME: str

    REDIS_URL: str

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()