from authlib.integrations.httpx_client import AsyncOAuth2Client
from app.core.config import settings


def get_google_client() -> AsyncOAuth2Client:
    """
    Returns a configured OAuth2 client for Google.
    Called fresh per request — AsyncOAuth2Client is not thread-safe
    as a shared singleton.
    """
    return AsyncOAuth2Client(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        redirect_uri=settings.google_redirect_uri,
        scope="openid email profile",  # what we're asking Google for
    )


# Google's OAuth2 endpoints — stable, rarely change
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
