from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    SQS_VIDEO_PROCESSING_QUEUE_URL: str = ""
