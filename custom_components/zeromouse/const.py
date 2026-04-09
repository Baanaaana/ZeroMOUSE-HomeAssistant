"""Constants for the ZeroMOUSE integration."""

from datetime import timedelta

DOMAIN = "zeromouse"

# Cognito (fixed for all ZeroMOUSE devices)
COGNITO_REGION = "eu-central-1"
COGNITO_CLIENT_ID = "7pdec0rbivg5hg8u3pke4veg0f"
COGNITO_ENDPOINT = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/"
COGNITO_IDENTITY_ENDPOINT = f"https://cognito-identity.{COGNITO_REGION}.amazonaws.com/"
COGNITO_USER_POOL_ID = "eu-central-1_LS6CKN0t1"
COGNITO_IDENTITY_POOL_ID = "eu-central-1:2b2f7d40-d6f9-474e-a06b-6441c4059601"

# API endpoints (fixed)
SHADOW_API_URL = (
    "https://4oj9bcxedi.execute-api.eu-central-1.amazonaws.com/DEV/device-shadow/"
)
GRAPHQL_URL = (
    "https://f36gc6o7jnewxe37dhn3fochza.appsync-api.eu-central-1.amazonaws.com/graphql"
)
S3_BUCKET = "mbr-ptf-images-eu-central-1-dev"
S3_REGION = "eu-central-1"

# Polling intervals
SHADOW_SCAN_INTERVAL = timedelta(seconds=10)
EVENT_SCAN_INTERVAL = timedelta(seconds=60)

# Token refresh margin (seconds before expiry to trigger refresh)
TOKEN_REFRESH_MARGIN = 60

# Config entry keys
CONF_DEVICE_ID = "device_id"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_DEVICE_NAME = "device_name"

# hass.data keys
DATA_SHADOW_COORDINATOR = "shadow_coordinator"
DATA_EVENT_COORDINATOR = "event_coordinator"

# Platforms
PLATFORMS = ["sensor", "binary_sensor", "image"]
