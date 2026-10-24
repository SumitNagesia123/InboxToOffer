from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class GmailConnectUrlResponse(BaseModel):
    """Response containing Google OAuth consent URL and CSRF state token."""
    authorization_url: str = Field(..., description="Google OAuth 2.0 authorization consent URL")
    state: str = Field(..., description="CSRF-safe state parameter for verification")
    is_configured: bool = Field(default=True, description="Whether Google OAuth client ID is configured")
    client_id: Optional[str] = None


class GmailConfigureOAuthRequest(BaseModel):
    """Payload to configure Google OAuth credentials."""
    client_id: str = Field(..., description="Google Cloud OAuth Client ID")
    client_secret: str = Field(..., description="Google Cloud OAuth Client Secret")


class GmailDirectConnectResponse(BaseModel):
    """Response returned upon direct connecting and ingesting sample correspondence."""
    success: bool
    message: str
    emails_ingested: int
    jobs_extracted: int
    matches_computed: int


class GmailCallbackRequest(BaseModel):
    """Payload for processing OAuth callback authorization code."""
    code: str = Field(..., description="Google OAuth authorization code")
    state: str = Field(..., description="CSRF state parameter returned by Google")


class GmailStatusResponse(BaseModel):
    """Current user Gmail connection status."""
    model_config = ConfigDict(from_attributes=True)

    connected: bool = Field(..., description="Whether user has connected an active Gmail account")
    is_connected: bool = False
    provider: str = "google"
    client_id: Optional[str] = None
    scopes: List[str] = Field(default_factory=list)
    expires_at: Optional[datetime] = None

    def __init__(self, **data):
        if "connected" in data and "is_connected" not in data:
            data["is_connected"] = data["connected"]
        elif "is_connected" in data and "connected" not in data:
            data["connected"] = data["is_connected"]
        super().__init__(**data)


class GmailDisconnectResponse(BaseModel):
    """Response returned upon disconnecting Gmail account."""
    success: bool
    message: str


class GmailAppPasswordConnectRequest(BaseModel):
    """Payload to connect real Gmail account using an App Password."""
    app_password: str = Field(..., min_length=8, description="16-character Google App Password")


class GmailAppPasswordConnectResponse(BaseModel):
    """Response returned upon connecting and synchronizing real Gmail inbox."""
    success: bool
    connected: bool
    message: str
    total_fetched: int = 0
    new_stored: int = 0
    jobs_extracted: int = 0
    matches_computed: int = 0
