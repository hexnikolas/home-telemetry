import os
import bcrypt

# ---------------------------------------------------------------------------
# Client registry
#
# Secrets are stored as bcrypt hashes — never plaintext.
# To generate a hash:
#   python -c "import bcrypt; print(bcrypt.hashpw(b'your-secret', bcrypt.gensalt()).decode())"
#
# Set the corresponding env var in services/api/app/.env
# ---------------------------------------------------------------------------
CLIENTS: dict[str, dict] = {
    # Admin — full access, use in Swagger UI / manual testing
    "admin": {
        "secret_hash": os.getenv("CLIENT_SECRET_ADMIN_HASH", ""),
        "scopes": [
            "observations:read",
            "observations:write",
            "systems:read",
            "systems:write",
            "datastreams:read",
            "datastreams:write",
            "deployments:read",
            "deployments:write",
            "procedures:read",
            "procedures:write",
            "properties:read",
            "properties:write",
            "admin:read",
            "admin:write",
        ],
    },
    # Ingestion worker — may only write observations
    "ingestion-worker": {
        "secret_hash": os.getenv("CLIENT_SECRET_INGESTION_HASH", ""),
        "scopes": ["observations:write"],
    },
    # Jobs worker / scheduler — may read systems, datastreams, and job state
    "jobs-worker": {
        "secret_hash": os.getenv("CLIENT_SECRET_JOBS_HASH", ""),
        "scopes": ["systems:read", "datastreams:read", "admin:read"],
    },
}


def authenticate_client(client_id: str, client_secret: str) -> dict | None:
    """Verify client_id + plaintext secret against the stored bcrypt hash.
    Returns the client dict on success, None on failure."""
    client = CLIENTS.get(client_id)
    if not client or not client["secret_hash"]:
        return None
    stored = client["secret_hash"].encode()
    if not bcrypt.checkpw(client_secret.encode(), stored):
        return None
    return client
