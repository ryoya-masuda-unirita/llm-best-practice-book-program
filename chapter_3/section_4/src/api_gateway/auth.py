"""Authentication and authorization module for LLM API Gateway."""

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.config import config
from src.logger import make_logger

logger = make_logger(__name__)

security = HTTPBearer()


class GatewayAuthenticator:
    """Handles authentication for the LLM API Gateway.

    This centralizes API token validation and ensures that only authorized
    clients can access the gateway services.
    """

    def __init__(self):
        self.valid_token = config.gateway_api_token.get_secret_value()

    def verify_token(self, token: str) -> bool:
        """Verify if the provided token is valid.

        Args:
            token: The API token to verify

        Returns:
            True if token is valid, False otherwise
        """
        return token == self.valid_token

    def authenticate(self, credentials: HTTPAuthorizationCredentials) -> str:
        """Authenticate a request using bearer token.

        Args:
            credentials: HTTP authorization credentials

        Returns:
            The client identifier (token prefix) if authenticated

        Raises:
            HTTPException: If authentication fails
        """
        token = credentials.credentials

        if not self.verify_token(token):
            logger.warning("Failed authentication attempt with invalid token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # In production, you would extract actual client_id from a database
        # For now, we use a portion of the token as client identifier
        client_id = f"client_{token[:8]}"
        logger.info(f"Successfully authenticated client: {client_id}")
        return client_id


# Global authenticator instance
authenticator = GatewayAuthenticator()


async def verify_api_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """Dependency function to verify API token.

    Args:
        credentials: HTTP authorization credentials from request

    Returns:
        Client identifier if authenticated

    Raises:
        HTTPException: If authentication fails
    """
    return authenticator.authenticate(credentials)
