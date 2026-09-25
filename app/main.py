from __future__ import annotations

import hmac
from io import BytesIO
from urllib.parse import quote

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from .settings import settings
from .google_docs import GoogleDocsRenderer
from .local_docs import LocalDocsRenderer
from .forms import build_values
from .courts import COURTS

if not settings.session_secret:
    raise RuntimeError("SESSION_SECRET is required")
if not settings.admin_password:
    raise RuntimeError("ADMIN_PASSWORD is required")

app = FastAPI(title=settings.app_name)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    https_only=settings.session_https_only,
    same_site="lax",
    max_age=60 * 60 * 12,
)

templates = Jinja2Templates(directory="app/templates")
google_renderer = GoogleDocsRenderer(
    settings.google_token_file,
    generated_folder_id=settings.google_generated_folder_id,
    generated_folder_name=settings.google_generated_folder_name,
)
local_renderer = LocalDocsRenderer(
    settings.local_template_dir,
    pdf_enabled=settings.local_pdf_enabled,
)

DOC_TYPES = {
    "application_recalc": {
        "title": "Заява — перерахунок",
        "google_template_id": settings.template_application_recalc_id,
        "local_template": settings.local_template_application_recalc,
        "prefix": "Заява_перерахунок",
    },
    "claim_indexation": {
        "title": "Позов — індексація",
        "google_template_id": settings.template_claim_indexation_id,
        "local_template": settings.local_template_claim_indexation,
        "prefix": "Позов_індексація",
    },
    "claim_recalc": {
        "title": "Позов — перерахунок",
        "google_template_id": settings.template_claim_recalc_id,
        "local_template": settings.local_template_claim_recalc,
        "prefix": "Позов_перерахунок",
    },
}


def authenticated(request: Request) -> bool:
    return request.session.get("authenticated") is True


def require_auth(request: Request):
    if not authenticated(request):
        raise HTTPException(status_code=401)


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if authenticated(request):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": None, "app_name": settings.app_name},
    )


@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    ok = (
        hmac.compare_digest(username, settings.admin_username)
        and hmac.compare_digest(password, settings.admin_password)
    )
    if not ok:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": "Невірний логін або пароль",
                "app_name": settings.app_name,
            },
            status_code=401,
        )
    request.session.clear()
    request.session["authenticated"] = True
    return RedirectResponse("/", status_code=303)


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    if not authenticated(request):
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "app_name": settings.app_name,
            "doc_types": DOC_TYPES,
            "courts": COURTS,
            "office_address": settings.office_correspondence_address,
            "office_phone": settings.office_phone,
            "office_email": settings.office_email,
            "google_folder_name": settings.google_generated_folder_name,
        },
    )


@app.post("/generate")
async def generate(request: Request):
    require_auth(request)
    form = await request.form()

    doc_type = str(form.get("document_type", ""))
    result_mode = str(form.get("result_mode", "download"))
    output_format = str(form.get("output_format", "docx"))
    render_mode = str(form.get("render_mode", "local"))

    if doc_type not in DOC_TYPES:
        raise HTTPException(400, "Unknown document type")
    if result_mode not in {"download", "google_docs"}:
        raise HTTPException(400, "Unknown result mode")

    values, applicant = build_values(form)
    cfg = DOC_TYPES[doc_type]
    document_date = str(form.get("document_date", "") or "").strip()
    basename = f'{cfg["prefix"]}_{applicant}'
    if document_date:
        basename += f"_{document_date}"

    try:
        if result_mode == "google_docs":
            generated = google_renderer.render_and_keep(
                template_id=cfg["google_template_id"],
                values=values,
                document_name=basename,
            )
            # A native Google Doc remains in Drive and is opened for editing.
            return RedirectResponse(generated.url, status_code=303)

        if output_format not in {"docx", "pdf"}:
            raise HTTPException(400, "Unknown output format")
        if render_mode not in {"local", "google"}:
            raise HTTPException(400, "Unknown render mode")

        if render_mode == "google":
            result = google_renderer.render_and_export(
                template_id=cfg["google_template_id"],
                values=values,
                output_format=output_format,
                download_basename=basename,
            )
        else:
            result = local_renderer.render(
                template_filename=cfg["local_template"],
                values=values,
                output_format=output_format,
                download_basename=basename,
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    headers = {
        "Content-Disposition": "attachment; filename*=UTF-8''" + quote(result.filename),
        "Cache-Control": "no-store, no-cache, must-revalidate, private",
        "Pragma": "no-cache",
        "X-Content-Type-Options": "nosniff",
    }
    return StreamingResponse(
        BytesIO(result.data),
        media_type=result.media_type,
        headers=headers,
    )
