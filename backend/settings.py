from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    COGNITO_CLIENT_ID: str = ""
    COGNITO_CLIENT_SECRET: str = ""
    DATABASE_URL: str = ""
