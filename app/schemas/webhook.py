from pydantic import BaseModel, Field
class WebhookConfigUpdate(BaseModel):
    verify_token: str | None = Field(default=None, min_length=8, max_length=255)
    page_access_token: str | None = Field(default=None, max_length=1024)
    page_id: str | None = Field(default=None, max_length=255)
class WebhookConfigRead(BaseModel):
    callback_url: str
    configured: bool
    verify_token_masked: str | None
    page_access_token_masked: str | None
    page_id: str | None