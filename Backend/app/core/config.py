from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    database_url: str = "sqlite:///./strokecore.db"
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    model_api_url: str
    model_api_key: str = ""
    upload_dir: str = "./uploads"
    frontend_url: str = "http://localhost:5173"
    max_upload_mb: int = 512
    average_brain_height_mm: float = 150.0
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
def get_settings() -> Settings: return Settings()
settings = get_settings()
