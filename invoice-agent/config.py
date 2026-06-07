from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openai_api_key: str
    llm_model: str = "gpt-4o-mini"

    # Slack
    slack_webhook_url: str = ""

    # QuickBooks (optional)
    quickbooks_client_id: str = ""
    quickbooks_client_secret: str = ""
    quickbooks_realm_id: str = ""

    # Notion (optional)
    notion_api_key: str = ""
    notion_db_id: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
