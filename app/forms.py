from starlette.datastructures import FormData

from .formatting import (
    date_short,
    date_short_year,
    date_long,
    date_signature,
    period_short,
    period_long,
    years_phrase,
    years_at_jan_1,
)
from .names import decline_name
from .settings import settings
from .courts import COURTS_BY_ID


def s(form: FormData, key: str, default: str = "") -> str:
    return str(form.get(key, default) or "").strip()


def first(form: FormData, *keys: str, default: str = "") -> str:
    for key in keys:
        value = s(form, key)
        if value:
            return value
    return default


def build_values(form: FormData) -> tuple[dict[str, str], str]:
    last = s(form, "last_name")
    first_name = s(form, "first_name")
    patronymic = s(form, "patronymic")
    gender = s(form, "gender", "male")

    fio = decline_name(last, first_name, patronymic, gender)
    for case in ("nom", "gen", "dat", "acc", "ins", "loc", "voc"):
        override = s(form, f"fio_{case}")
        if override:
            fio[case] = override
    if s(form, "signature_name"):
        fio["signature_name"] = s(form, "signature_name")

    service_from = s(form, "service_from")
    service_to = s(form, "service_to")
    claim_from = s(form, "claim_from")
    claim_to = s(form, "claim_to")
    document_date = s(form, "document_date")
    claim_years = s(form, "claim_years")

    target_number = first(form, "target_unit_number", "military_unit_number")
    target_address = first(form, "target_unit_address", "military_unit_address")
    target_edrpou = first(form, "target_unit_edrpou", "military_unit_edrpou")
    target_phone = first(form, "target_unit_phone", "military_unit_phone")
    target_email = first(form, "target_unit_email", "military_unit_email")

    correspondence_address = first(
        form, "correspondence_address", default=settings.office_correspondence_address
    )
    phone = first(form, "phone", default=settings.office_phone)
    email = first(form, "email", default=settings.office_email)

    service_unit_number = s(form, "service_unit_number")
    service_order_unit_number = first(
        form,
        "service_order_unit_number",
        default=service_unit_number or target_number,
    )

    response_text = s(form, "pretrial_response_text")
    response_block = response_text or "Жодної відповіді на дану заяву я не отримав."

    indexation_full = s(form, "indexation_full_range") or period_long(service_from, service_to)

    passport_issue_date = s(form, "passport_issue_date")
    ubd_issue_date = s(form, "ubd_issue_date")
    pretrial_received_date = s(form, "pretrial_received_date")

    court = COURTS_BY_ID.get(s(form, "court_id"))
    if court:
        court_name = court["name"]
        court_address = court["address"]
        court_phone = court["phone"]
        court_phone_line = court["phone_line"]
    else:
        # Backward compatibility for old/manual POSTs. The current UI uses court_id.
        court_name = s(form, "court_name")
        court_address = s(form, "court_address")
        court_phone = s(form, "court_phone")
        court_phone_line = (f"Телефон: {court_phone}" if court_phone else "")

    values = {
        # Applicant / names
        "applicant.fio.nom": fio["nom"],
        "applicant.fio.nom_header": fio["nom_header"],
        "applicant.fio.gen": fio["gen"],
        "applicant.fio.dat": fio["dat"],
        "applicant.fio.acc": fio["acc"],
        "applicant.fio.ins": fio["ins"],
        "applicant.fio.loc": fio["loc"],
        "applicant.fio.voc": fio["voc"],
        "applicant.signature_name": fio["signature_name"],
        "applicant.electronic_cabinet": s(form, "applicant_electronic_cabinet"),

        # Passport / identifiers
        "applicant.passport.series": s(form, "passport_series"),
        "applicant.passport.number": s(form, "passport_number"),
        "applicant.passport.issuer": s(form, "passport_issuer"),
        "applicant.passport.issuer_code": s(form, "passport_issuer_code"),
        "applicant.passport.issue_date.short": date_short(passport_issue_date),
        "applicant.passport.issue_date.short_year": date_short_year(passport_issue_date),
        "applicant.passport.issue_date.long": date_long(passport_issue_date),
        "applicant.rnokpp": s(form, "rnokpp"),
        "applicant.registration_address": s(form, "registration_address"),

        # Contact aliases used by current master templates
        "contact.correspondence_address": correspondence_address,
        "contact.phone": phone,
        "contact.email": email,
        "applicant.correspondence_address": correspondence_address,
        "applicant.phone": phone,
        "applicant.email": email,

        # Court
        "court.name": court_name,
        "court.address": court_address,
        "court.phone": court_phone,
        "court.phone_line": court_phone_line,

        # Statement addressee / target unit
        "target_unit.number": target_number,
        "target_unit.address": target_address,
        "target_unit.edrpou": target_edrpou,
        "target_unit.phone": target_phone,
        "target_unit.email": target_email,

        # Backward-compatible aliases
        "military_unit.number": target_number,
        "military_unit.address": target_address,
        "military_unit.edrpou": target_edrpou,
        "military_unit.phone": target_phone,
        "military_unit.email": target_email,
        "military_unit.email_or_unknown": target_email or "невідомо",

        # Defendant
        "defendant_unit.number": s(form, "defendant_unit_number"),
        "defendant_unit.address": s(form, "defendant_unit_address"),
        "defendant_unit.edrpou": s(form, "defendant_unit_edrpou"),
        "defendant_unit.phone": s(form, "defendant_unit_phone") or "невідомо",
        "defendant_unit.email": s(form, "defendant_unit_email"),
        "defendant_unit.electronic_cabinet": s(form, "defendant_unit_electronic_cabinet"),

        # Service / disputed periods
        "service_unit.number": service_unit_number,
        "service_period.from.short": date_short(service_from),
        "service_period.from.long": date_long(service_from),
        "service_period.to.short": date_short(service_to),
        "service_period.to.long": date_long(service_to),
        "service_period.range_short": period_short(service_from, service_to),
        "service_period.range_long": period_long(service_from, service_to),

        "claim_period.from.short": date_short(claim_from),
        "claim_period.from.long": date_long(claim_from),
        "claim_period.to.short": date_short(claim_to),
        "claim_period.to.long": date_long(claim_to),
        "claim_period.range_short": period_short(claim_from, claim_to),
        "claim_period.range_long": period_long(claim_from, claim_to),

        "claim.years": years_phrase(claim_years),
        "claim.years_text": years_phrase(claim_years),
        "claim.years_at_jan_1": years_at_jan_1(claim_years),
        "claim.reference_dates_text": years_at_jan_1(claim_years),

        # Indexation
        "indexation_period.full.range_long": indexation_full,
        "indexation_period.pre_2018.range_long": s(form, "indexation_pre_2018_range"),
        "indexation_period.post_2018.range_long": s(form, "indexation_post_2018_range"),

        # Pre-trial
        "pretrial.application.date.short": date_short(s(form, "pretrial_application_date")),
        "pretrial.received_at.short": date_short(pretrial_received_date),
        "pretrial.received_date.short": date_short(pretrial_received_date),
        "pretrial.received_date.short_year": date_short_year(pretrial_received_date),
        "pretrial.incoming_number": s(form, "pretrial_incoming_number"),
        "pretrial.response_block": response_block,

        # Attachments
        "documents.military_id.series": s(form, "military_id_series"),
        "documents.military_id.number": s(form, "military_id_number"),
        "documents.military_id.issue_date.short": date_short(s(form, "military_id_issue_date")),
        "documents.officer_id.series": s(form, "officer_id_series"),
        "documents.officer_id.number": s(form, "officer_id_number"),
        "documents.ubd.number": s(form, "ubd_number"),
        "documents.ubd.issue_date.short": date_short(ubd_issue_date),
        "documents.ubd.issue_date.long": date_long(ubd_issue_date),
        "documents.service_order.unit_number": service_order_unit_number,
        "documents.service_order.number": s(form, "service_order_number"),
        "documents.service_order.date.short": date_short(s(form, "service_order_date")),

        # Document date
        "document.date.short": date_short(document_date),
        "document.date.long": date_long(document_date),
        "document.date.long_signature": date_signature(document_date),
    }

    applicant = fio["nom"] or "Заявник"
    return values, applicant
