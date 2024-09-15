import os

from dotenv import load_dotenv

load_dotenv()

class Config:
    # Configuration settings
    groq_api_key = os.getenv("GROQ_API_KEY")
    model = os.getenv("MODEL")
    prompt_token_limit = int(os.getenv("PROMPT_TOKEN_LIMIT"))
    completion_token_limit = int(os.getenv("COMPLETION_TOKEN_LIMIT"))
    temperature = float(os.getenv("TEMPERATURE"))
    frequency_penalty = float(os.getenv("FREQUENCY_PENALTY"))
    presence_penalty = float(os.getenv("PRESENCE_PENALTY"))

    @classmethod
    def get(cls, setting_name):
        """Retrieve a setting by name."""
        return getattr(cls, setting_name, None)

    @classmethod
    def set(cls, setting_name, value):
        """Set a setting value."""
        setattr(cls, setting_name, value)