from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict
import re

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/drive"]
PLACEHOLDER_RE = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")

MIME = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
}
EXT = {"docx": "docx", "pdf": "pdf"}


@dataclass
class GeneratedFile:
    data: bytes
    filename: str
    media_type: str


@dataclass
class GeneratedGoogleDoc:
    document_id: str
    name: str
    url: str


def _google_doc_text(node) -> str:
    parts: list[str] = []

    def walk(value):
        if isinstance(value, dict):
            text_run = value.get("textRun")
            if isinstance(text_run, dict) and isinstance(text_run.get("content"), str):
                parts.append(text_run["content"])
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(node)
    return "".join(parts)


def _is_pure_red_background(text_style: dict) -> bool:
    bg = text_style.get("backgroundColor") if isinstance(text_style, dict) else None
    color = bg.get("color") if isinstance(bg, dict) else None
    rgb = color.get("rgbColor") if isinstance(color, dict) else None
    if not isinstance(rgb, dict):
        return False
    red = float(rgb.get("red", 0.0) or 0.0)
    green = float(rgb.get("green", 0.0) or 0.0)
    blue = float(rgb.get("blue", 0.0) or 0.0)
    return red >= 0.99 and green <= 0.01 and blue <= 0.01


def _red_background_requests(document: dict) -> list[dict]:
    """Build style updates that remove the red variable-marker background only."""
    requests: list[dict] = []

    def scan(node, tab_id: str | None = None):
        if isinstance(node, dict):
            text_run = node.get("textRun")
            start = node.get("startIndex")
            end = node.get("endIndex")
            if (
                isinstance(text_run, dict)
                and isinstance(start, int)
                and isinstance(end, int)
                and end > start
                and _is_pure_red_background(text_run.get("textStyle") or {})
            ):
                range_spec = {"startIndex": start, "endIndex": end}
                if tab_id:
                    range_spec["tabId"] = tab_id
                requests.append({
                    "updateTextStyle": {
                        "range": range_spec,
                        "textStyle": {
                            "backgroundColor": {
                                "color": {
                                    "rgbColor": {"red": 1.0, "green": 1.0, "blue": 1.0}
                                }
                            }
                        },
                        "fields": "backgroundColor",
                    }
                })

            for key, child in node.items():
                if key not in {"textRun", "tabs"}:
                    scan(child, tab_id)
        elif isinstance(node, list):
            for child in node:
                scan(child, tab_id)

    def scan_tabs(tabs):
        for tab in tabs or []:
            if not isinstance(tab, dict):
                continue
            props = tab.get("tabProperties") or {}
            tab_id = props.get("tabId")
            scan(tab.get("documentTab") or {}, tab_id)
            scan_tabs(tab.get("childTabs") or [])

    tabs = document.get("tabs")
    if tabs:
        scan_tabs(tabs)
    else:
        scan(document.get("body") or {}, None)

    return requests


class GoogleDocsRenderer:
    def __init__(
        self,
        token_file: str,
        generated_folder_id: str = "",
        generated_folder_name: str = "SpravaHub Generated Documents",
    ):
        self.token_file = Path(token_file)
        self.generated_folder_id = generated_folder_id.strip()
        self.generated_folder_name = generated_folder_name.strip()
        self._resolved_folder_id: str | None = None

    def _credentials(self) -> Credentials:
        if not self.token_file.exists():
            raise RuntimeError(
                f"Google token not found: {self.token_file}. "
                "Run scripts/google_oauth_setup.py first."
            )
        creds = Credentials.from_authorized_user_file(str(self.token_file), SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        if not creds.valid:
            raise RuntimeError("Google OAuth credentials are invalid.")
        return creds

    def _services(self):
        creds = self._credentials()
        drive = build("drive", "v3", credentials=creds, cache_discovery=False)
        docs = build("docs", "v1", credentials=creds, cache_discovery=False)
        return drive, docs

    @staticmethod
    def _requests(values: Dict[str, str]):
        return [
            {
                "replaceAllText": {
                    "containsText": {
                        "text": "{{" + marker + "}}",
                        "matchCase": True,
                    },
                    "replaceText": value or "",
                }
            }
            for marker, value in values.items()
        ]

    @staticmethod
    def _safe_name(name: str) -> str:
        # Google Drive accepts almost any filename, but keeping this conservative
        # also makes exported/downloaded names predictable.
        return "".join(
            ch if ch.isalnum() or ch in " _-.()" else "_"
            for ch in name
        ).strip(" ._") or "document"

    @staticmethod
    def _escape_drive_query(value: str) -> str:
        return value.replace("\\", "\\\\").replace("'", "\\'")

    def _ensure_output_folder(self, drive) -> str | None:
        if self.generated_folder_id:
            return self.generated_folder_id
        if not self.generated_folder_name:
            return None
        if self._resolved_folder_id:
            return self._resolved_folder_id

        escaped = self._escape_drive_query(self.generated_folder_name)
        result = drive.files().list(
            q=(
                "mimeType='application/vnd.google-apps.folder' "
                "and trashed=false "
                f"and name='{escaped}'"
            ),
            spaces="drive",
            fields="files(id,name,createdTime)",
            pageSize=10,
            orderBy="createdTime",
        ).execute()
        folders = result.get("files") or []
        if folders:
            self._resolved_folder_id = folders[0]["id"]
            return self._resolved_folder_id

        created = drive.files().create(
            body={
                "name": self.generated_folder_name,
                "mimeType": "application/vnd.google-apps.folder",
            },
            fields="id",
        ).execute()
        self._resolved_folder_id = created["id"]
        return self._resolved_folder_id

    def _render_copy(
        self,
        drive,
        docs,
        template_id: str,
        values: Dict[str, str],
        name: str,
        parent_folder_id: str | None = None,
    ) -> tuple[str, dict]:
        copy_body: dict = {"name": self._safe_name(name)}
        if parent_folder_id:
            copy_body["parents"] = [parent_folder_id]

        copied = drive.files().copy(
            fileId=template_id,
            body=copy_body,
            fields="id,name,webViewLink",
        ).execute()
        document_id = copied["id"]

        try:
            requests = self._requests(values)
            if requests:
                docs.documents().batchUpdate(
                    documentId=document_id,
                    body={"requests": requests},
                ).execute()

            rendered_doc = docs.documents().get(
                documentId=document_id, includeTabsContent=True
            ).execute()

            cleanup_requests = _red_background_requests(rendered_doc)
            if cleanup_requests:
                docs.documents().batchUpdate(
                    documentId=document_id,
                    body={"requests": cleanup_requests},
                ).execute()
                rendered_doc = docs.documents().get(
                    documentId=document_id, includeTabsContent=True
                ).execute()

            unresolved = sorted(
                {
                    m.group(1).strip()
                    for m in PLACEHOLDER_RE.finditer(_google_doc_text(rendered_doc))
                }
            )
            if unresolved:
                raise RuntimeError(
                    "Generated Google document still contains placeholders: "
                    + ", ".join(unresolved)
                )

            return document_id, copied
        except Exception:
            # Never leave a partially rendered copy behind.
            try:
                drive.files().delete(fileId=document_id).execute()
            except Exception:
                pass
            raise

    def render_and_export(
        self,
        template_id: str,
        values: Dict[str, str],
        output_format: str,
        download_basename: str,
    ) -> GeneratedFile:
        if output_format not in MIME:
            raise ValueError("Unsupported output format.")

        drive, docs = self._services()
        temp_id = None
        try:
            temp_id, _ = self._render_copy(
                drive=drive,
                docs=docs,
                template_id=template_id,
                values=values,
                name="__spravahub_docgen_temp__",
            )

            data = drive.files().export(
                fileId=temp_id,
                mimeType=MIME[output_format],
            ).execute()

            safe = self._safe_name(download_basename)
            return GeneratedFile(
                data=data,
                filename=f"{safe}.{EXT[output_format]}",
                media_type=MIME[output_format],
            )
        finally:
            if temp_id:
                try:
                    drive.files().delete(fileId=temp_id).execute()
                except Exception:
                    pass

    def render_and_keep(
        self,
        template_id: str,
        values: Dict[str, str],
        document_name: str,
    ) -> GeneratedGoogleDoc:
        """Create a filled native Google Doc and keep it in Drive for editing."""
        drive, docs = self._services()
        document_id = None
        try:
            folder_id = self._ensure_output_folder(drive)
            document_id, copied = self._render_copy(
                drive=drive,
                docs=docs,
                template_id=template_id,
                values=values,
                name=document_name,
                parent_folder_id=folder_id,
            )
            name = copied.get("name") or self._safe_name(document_name)
            url = copied.get("webViewLink") or (
                f"https://docs.google.com/document/d/{document_id}/edit"
            )
            return GeneratedGoogleDoc(
                document_id=document_id,
                name=name,
                url=url,
            )
        except Exception:
            # Do not leave a half-filled Google document after a failed render.
            if document_id:
                try:
                    drive.files().delete(fileId=document_id).execute()
                except Exception:
                    pass
            raise
