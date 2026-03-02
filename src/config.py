from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "AIRLOCK_"}

    database_url: str = "postgresql+asyncpg://airlock:airlock_dev@localhost:5432/airlock"
    master_key: str = "CHANGE-ME-IN-PRODUCTION"
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
