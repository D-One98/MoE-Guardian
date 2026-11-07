import os
from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class Settings:
    app_name: str = "MoE-GUARDIAN API (Powered by VERITY MoE)"
    app_version: str = "0.2.0-round2-foundation"
    app_env: str = field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./moe_guardian_dev.db"))
    hmac_signing_secret: str = field(
        default_factory=lambda: os.getenv("HMAC_SIGNING_SECRET", "dev-only-replace-in-production-hmac-secret-key-2026")
    )
    hmac_key_id: str = field(default_factory=lambda: os.getenv("HMAC_KEY_ID", "key-v1-local"))
    hmac_retired_keys: str = field(default_factory=lambda: os.getenv("HMAC_RETIRED_KEYS", ""))
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "none"))
    max_image_upload_bytes: int = field(
        default_factory=lambda: int(os.getenv("MAX_IMAGE_UPLOAD_BYTES", str(5 * 1024 * 1024)))
    )
    max_image_pixels: int = field(
        default_factory=lambda: int(os.getenv("MAX_IMAGE_PIXELS", str(16_000_000)))
    )
    max_pdf_upload_bytes: int = field(
        default_factory=lambda: int(os.getenv("MAX_PDF_UPLOAD_BYTES", str(10 * 1024 * 1024)))
    )
    max_pdf_pages: int = field(
        default_factory=lambda: int(os.getenv("MAX_PDF_PAGES", "50"))
    )
    max_csv_upload_bytes: int = field(
        default_factory=lambda: int(os.getenv("MAX_CSV_UPLOAD_BYTES", str(5 * 1024 * 1024)))
    )
    require_verified_tenant_auth: bool = field(
        default_factory=lambda: os.getenv("REQUIRE_VERIFIED_TENANT_AUTH", "false").lower() == "true"
    )
    supabase_jwt_secret: str = field(
        default_factory=lambda: os.getenv("SUPABASE_JWT_SECRET", "")
    )
    supabase_jwt_issuer: str = field(
        default_factory=lambda: os.getenv("SUPABASE_JWT_ISSUER", "")
    )
    supabase_jwt_audience: str = field(
        default_factory=lambda: os.getenv("SUPABASE_JWT_AUDIENCE", "authenticated")
    )
    tesseract_cmd: str = field(
        default_factory=lambda: os.getenv("TESSERACT_CMD", "")
    )
    visualguard_ocr_enabled: bool = field(
        default_factory=lambda: os.getenv("VISUALGUARD_OCR_ENABLED", "false").lower() == "true"
    )
    ocr_min_confidence: float = field(
        default_factory=lambda: float(os.getenv("OCR_MIN_CONFIDENCE", "60.0"))
    )
    cors_origins: List[str] = field(
        default_factory=lambda: [
            origin.strip()
            for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
            if origin.strip()
        ]
    )


settings = Settings()

INSECURE_DEFAULT_HMAC_SECRET = "dev-only-replace-in-production-hmac-secret-key-2026"


def get_hmac_key_ring() -> tuple[str, str, dict[str, str]]:
    """
    Returns (active_key_id, active_secret, verification_key_map) from environment/config.
    - Supports one active signing key (HMAC_KEY_ID + HMAC_SIGNING_SECRET) and multiple
      retired verification-only keys via HMAC_RETIRED_KEYS ('old_id:old_secret,older_id:older_secret').
    - Fails closed if signing configuration is missing or if APP_ENV=production uses the
      publicly known development default secret.
    """
    app_env = os.getenv("APP_ENV", settings.app_env).strip().lower()
    active_id = os.getenv("HMAC_KEY_ID", settings.hmac_key_id).strip()
    active_secret = os.getenv("HMAC_SIGNING_SECRET", settings.hmac_signing_secret).strip()
    retired_raw = os.getenv("HMAC_RETIRED_KEYS", settings.hmac_retired_keys).strip()

    if not active_id or not active_secret:
        raise RuntimeError(
            "HMAC signing configuration error: HMAC_KEY_ID and HMAC_SIGNING_SECRET must be non-empty."
        )

    if app_env == "production" and active_secret == INSECURE_DEFAULT_HMAC_SECRET:
        raise RuntimeError(
            "Security error: Production environment must not use the default development HMAC_SIGNING_SECRET."
        )

    key_map: dict[str, str] = {}
    if retired_raw:
        for pair in retired_raw.split(","):
            pair = pair.strip()
            if not pair:
                continue
            if ":" not in pair:
                raise RuntimeError(
                    "Invalid HMAC_RETIRED_KEYS format; expected comma-separated 'key_id:secret' entries."
                )
            k_id, k_sec = pair.split(":", 1)
            k_id, k_sec = k_id.strip(), k_sec.strip()
            if not k_id or not k_sec:
                raise RuntimeError("Invalid HMAC_RETIRED_KEYS entry: key_id and secret must be non-empty.")
            key_map[k_id] = k_sec

    # Active key is always available for both signing and verification
    key_map[active_id] = active_secret
    return active_id, active_secret, key_map