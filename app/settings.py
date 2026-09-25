from dataclasses import dataclass
import os

def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}

@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "SpravaHub Documents")
    app_env: str = os.getenv("APP_ENV", "production")
    base_url: str = os.getenv("BASE_URL", "")
    admin_username: str = os.getenv("ADMIN_USERNAME", "admin")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "")
    session_secret: str = os.getenv("SESSION_SECRET", "")
    session_https_only: bool = _bool("SESSION_HTTPS_ONLY", True)

    google_token_file: str = os.getenv(
        "GOOGLE_TOKEN_FILE", "/srv/app/secrets/google-token.json"
    )
    google_generated_folder_id: str = os.getenv("GOOGLE_GENERATED_FOLDER_ID", "")
    google_generated_folder_name: str = os.getenv(
        "GOOGLE_GENERATED_FOLDER_NAME", "SpravaHub Generated Documents"
    )

    template_application_recalc_id: str = os.getenv(
        "TEMPLATE_APPLICATION_RECALC_ID",
        "13pl29xCjmo4fDtbHH8Cug5_ssGOqq_reyDW-k4dnjHg",
    )
    template_claim_indexation_id: str = os.getenv(
        "TEMPLATE_CLAIM_INDEXATION_ID",
        "157jeX1I3HERMeiFozpc-wtYOkExPdS4dXHfY2CKGQgY",
    )
    template_claim_recalc_id: str = os.getenv(
        "TEMPLATE_CLAIM_RECALC_ID",
        "1bu4hcNQnE9hWx4j6mmYSWTS0j3W4RkiUg2elqheO_OM",
    )

    local_template_dir: str = os.getenv("LOCAL_TEMPLATE_DIR", "/srv/app/local_templates")
    local_template_application_recalc: str = os.getenv(
        "LOCAL_TEMPLATE_APPLICATION_RECALC", "application_recalc.docx"
    )
    local_template_claim_indexation: str = os.getenv(
        "LOCAL_TEMPLATE_CLAIM_INDEXATION", "claim_indexation.docx"
    )
    local_template_claim_recalc: str = os.getenv(
        "LOCAL_TEMPLATE_CLAIM_RECALC", "claim_recalc.docx"
    )
    local_pdf_enabled: bool = _bool("LOCAL_PDF_ENABLED", True)

    office_correspondence_address: str = os.getenv(
        "OFFICE_CORRESPONDENCE_ADDRESS", ""
    )
    office_phone: str = os.getenv("OFFICE_PHONE", "")
    office_email: str = os.getenv("OFFICE_EMAIL", "")

settings = Settings()
