import json
import ipaddress
import re
import socket
import threading
from collections.abc import Callable
from datetime import datetime
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler, urlopen

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, get_db
from app.domain.auth.deps import get_current_user, require_admin, require_editor
from app.domain.auth.models import User
from app.domain.inventory.models import Product, Zone
from app.domain.settings.models import AppSetting
from app.domain.auth.sso import default_sso_settings_payload, normalize_sso_settings_payload
from app.domain.realtime.events import emit_realtime_event
from app.domain.settings.schemas import (
    AuthSSOSettingsRead,
    AuthSSOSettingsUpdate,
    DEFAULT_BRAND_OPTIONS,
    DEFAULT_CATEGORY_PREFILL_PATHS,
    DEFAULT_LOCATION_TYPES,
    DEFAULT_MANUFACTURER_OPTIONS,
    CategoryPrefillPathsRead,
    CategoryPrefillPathsUpdate,
    EventoryProductRead,
    EventoryProductsRead,
    EventorySyncStartRead,
    EventorySyncStatusRead,
    EventorySyncRead,
    EventoryInstanceConfig,
    IntegrationConnectionTestRead,
    IntegrationConnectionTestRequest,
    IntegrationPluginConfig,
    IntegrationsRead,
    IntegrationsUpdate,
    LabelTemplateRead,
    LabelTemplateUpsert,
    LabelTemplateCanvas,
    LabelTemplateElement,
    LocationTypeOptionsRead,
    LocationTypeOptionsUpdate,
    ProductDefaultsRead,
    ProductDefaultsUpdate,
)
from app.domain.storage.models import AssetFile
from app.domain.storage.schemas import CompanyProfileRead, CompanyProfileUpdate

router = APIRouter(prefix="/settings", tags=["settings"], dependencies=[Depends(get_current_user)])

LOCATION_TYPES_KEY = "inventory.location_types"
CATEGORY_PREFILL_PATHS_KEY = "inventory.category_prefill_paths"
PRODUCT_DEFAULTS_KEY = "inventory.product_defaults"
INTEGRATIONS_KEY = "integrations.plugins"
AUTH_SSO_SETTINGS_KEY = "auth.sso"
COMPANY_PROFILE_KEY = "company.profile"
LABEL_TEMPLATES_KEY = "labels.templates"
DEFAULT_EVENTORY_API_URL = "https://api.eventory.se"

DEFAULT_INTEGRATIONS = {
    "eventory_instances": [
        {
            "id": "eventory-main",
            "name": "Eventory Main",
            "enabled": False,
            "api_url": DEFAULT_EVENTORY_API_URL,
            "api_key": None,
            "username": None,
            "password": None,
            "token_endpoint": None,
            "supplier_name": "Eventory",
            "sync_interval_minutes": 0,
            "price_margin_percent": 0,
            "last_sync_at": None,
            "last_sync_imported": 0,
            "last_sync_updated": 0,
            "last_sync_skipped": 0,
            "last_sync_total": 0,
            "sync_running": False,
            "sync_started_at": None,
            "sync_finished_at": None,
            "sync_progress_current": 0,
            "sync_progress_total": 0,
            "sync_progress_percent": 0,
            "sync_message": None,
        }
    ]
}
ALLOWED_INTEGRATION_PLUGINS = {"eventory"}
ALLOWED_SYNC_INTERVALS = {0, 15, 30, 60, 120, 240, 480, 1440}
EVENTORY_SYNC_LOCK = threading.Lock()
EVENTORY_SYNC_RUNNING: set[str] = set()


@router.get("/location-types", response_model=LocationTypeOptionsRead)
def get_location_types(db: Session = Depends(get_db)) -> LocationTypeOptionsRead:
    setting = _get_or_create_setting(db, LOCATION_TYPES_KEY, DEFAULT_LOCATION_TYPES)
    configured_options = _normalize_options_lower(_parse_string_list(setting.value_json, DEFAULT_LOCATION_TYPES))
    used_zone_types = _get_used_zone_types(db)
    options = _merge_unique_lower(configured_options, used_zone_types)
    return LocationTypeOptionsRead(options=options)


@router.put("/location-types", response_model=LocationTypeOptionsRead)
def update_location_types(
    payload: LocationTypeOptionsUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> LocationTypeOptionsRead:
    setting = _get_or_create_setting(db, LOCATION_TYPES_KEY, DEFAULT_LOCATION_TYPES)
    options = _normalize_options_lower(payload.options)
    setting.value_json = json.dumps(options)
    db.commit()
    return LocationTypeOptionsRead(options=options)


@router.get("/category-prefill", response_model=CategoryPrefillPathsRead)
def get_category_prefill_paths(db: Session = Depends(get_db)) -> CategoryPrefillPathsRead:
    setting = _get_or_create_setting(db, CATEGORY_PREFILL_PATHS_KEY, DEFAULT_CATEGORY_PREFILL_PATHS)
    paths = _normalize_category_paths(_parse_nested_string_list(setting.value_json, DEFAULT_CATEGORY_PREFILL_PATHS))
    return CategoryPrefillPathsRead(paths=paths)


@router.put("/category-prefill", response_model=CategoryPrefillPathsRead)
def update_category_prefill_paths(
    payload: CategoryPrefillPathsUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> CategoryPrefillPathsRead:
    setting = _get_or_create_setting(db, CATEGORY_PREFILL_PATHS_KEY, DEFAULT_CATEGORY_PREFILL_PATHS)
    paths = _normalize_category_paths(payload.paths)
    setting.value_json = json.dumps(paths)
    db.commit()
    return CategoryPrefillPathsRead(paths=paths)


@router.get("/product-defaults", response_model=ProductDefaultsRead)
def get_product_defaults(db: Session = Depends(get_db)) -> ProductDefaultsRead:
    setting = _get_or_create_setting(
        db,
        PRODUCT_DEFAULTS_KEY,
        {
            "brand_options": DEFAULT_BRAND_OPTIONS,
            "manufacturer_options": DEFAULT_MANUFACTURER_OPTIONS,
            "default_brand": DEFAULT_BRAND_OPTIONS[0],
            "default_manufacturer": DEFAULT_MANUFACTURER_OPTIONS[0],
            "brand_manufacturer_map": {},
            "brand_links": {},
            "manufacturer_links": {},
        },
    )
    data = _parse_product_defaults(setting.value_json)
    return ProductDefaultsRead(**data)


@router.put("/product-defaults", response_model=ProductDefaultsRead)
def update_product_defaults(
    payload: ProductDefaultsUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> ProductDefaultsRead:
    setting = _get_or_create_setting(
        db,
        PRODUCT_DEFAULTS_KEY,
        {
            "brand_options": DEFAULT_BRAND_OPTIONS,
            "manufacturer_options": DEFAULT_MANUFACTURER_OPTIONS,
            "default_brand": DEFAULT_BRAND_OPTIONS[0],
            "default_manufacturer": DEFAULT_MANUFACTURER_OPTIONS[0],
            "brand_manufacturer_map": {},
            "brand_links": {},
            "manufacturer_links": {},
        },
    )

    brand_options = _normalize_options_keep_case(payload.brand_options, DEFAULT_BRAND_OPTIONS)
    manufacturer_options = _normalize_options_keep_case(payload.manufacturer_options, DEFAULT_MANUFACTURER_OPTIONS)
    default_brand = _normalize_default_option(payload.default_brand, brand_options)
    default_manufacturer = _normalize_default_option(payload.default_manufacturer, manufacturer_options)
    brand_manufacturer_map = _normalize_brand_manufacturer_map(payload.brand_manufacturer_map, brand_options, manufacturer_options)
    brand_links = _normalize_links(payload.brand_links, brand_options)
    manufacturer_links = _normalize_links(payload.manufacturer_links, manufacturer_options)

    data = {
        "brand_options": brand_options,
        "manufacturer_options": manufacturer_options,
        "default_brand": default_brand,
        "default_manufacturer": default_manufacturer,
        "brand_manufacturer_map": brand_manufacturer_map,
        "brand_links": brand_links,
        "manufacturer_links": manufacturer_links,
    }

    setting.value_json = json.dumps(data)
    db.commit()
    return ProductDefaultsRead(**data)


@router.get("/integrations", response_model=IntegrationsRead)
def get_integrations(db: Session = Depends(get_db)) -> IntegrationsRead:
    setting = _get_or_create_setting(db, INTEGRATIONS_KEY, DEFAULT_INTEGRATIONS)
    data = _parse_integrations(setting.value_json)
    return IntegrationsRead(**data)


@router.put("/integrations", response_model=IntegrationsRead)
def update_integrations(
    payload: IntegrationsUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> IntegrationsRead:
    setting = _get_or_create_setting(db, INTEGRATIONS_KEY, DEFAULT_INTEGRATIONS)
    persisted = _parse_integrations(setting.value_json)
    persisted_instances = persisted.get("eventory_instances") if isinstance(persisted, dict) else []
    persisted_by_id = {
        str(item.get("id") or "").strip(): item
        for item in (persisted_instances or [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    eventory_instances = payload.eventory_instances or [
        EventoryInstanceConfig(id="eventory-main", name="Eventory Main", supplier_name="Eventory")
    ]
    normalized_instances: list[dict[str, object]] = []
    for instance in eventory_instances:
        _validate_url_port(str(instance.api_url or "").strip(), "API URL")
        token_endpoint = str(instance.token_endpoint or "").strip()
        if token_endpoint:
            _validate_url_port(token_endpoint, "Token endpoint")
        normalized_instances.append(
            _merge_sync_metadata(
                _normalize_eventory_instance(instance),
                persisted_by_id.get(str(instance.id or "").strip() or "eventory-main"),
            )
        )
    data = {
        "eventory_instances": normalized_instances,
    }
    setting.value_json = json.dumps(data)
    db.commit()
    return IntegrationsRead(**data)


@router.get("/auth-sso", response_model=AuthSSOSettingsRead)
def get_auth_sso_settings(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> AuthSSOSettingsRead:
    setting = _get_or_create_setting(db, AUTH_SSO_SETTINGS_KEY, default_sso_settings_payload())
    try:
        parsed = json.loads(setting.value_json or "{}")
    except Exception:
        parsed = {}
    normalized = normalize_sso_settings_payload(parsed)
    return AuthSSOSettingsRead(**normalized)


@router.put("/auth-sso", response_model=AuthSSOSettingsRead)
def update_auth_sso_settings(
    payload: AuthSSOSettingsUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> AuthSSOSettingsRead:
    setting = _get_or_create_setting(db, AUTH_SSO_SETTINGS_KEY, default_sso_settings_payload())
    normalized = normalize_sso_settings_payload(payload.model_dump())
    setting.value_json = json.dumps(normalized)
    db.commit()
    return AuthSSOSettingsRead(**normalized)


@router.get("/company-profile", response_model=CompanyProfileRead)
def get_company_profile(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> CompanyProfileRead:
    setting = _get_or_create_setting(
        db,
        COMPANY_PROFILE_KEY,
        {
            "company_name": None,
            "default_language": "en",
            "logo_file_id": None,
            "logo_light_wide_file_id": None,
            "logo_light_small_file_id": None,
            "logo_dark_wide_file_id": None,
            "logo_dark_small_file_id": None,
            "currency": "SEK",
            "vat_number": None,
            "address_line1": None,
            "address_line2": None,
            "postal_code": None,
            "city": None,
            "country": None,
            "contact_email": None,
            "contact_phone": None,
            "website": None,
        },
    )
    try:
        parsed = json.loads(setting.value_json or "{}")
    except Exception:
        parsed = {}

    company_name = parsed.get("company_name") if isinstance(parsed, dict) else None
    def resolve_logo_field(field_name: str) -> tuple[int | None, str | None]:
        file_id = parsed.get(field_name) if isinstance(parsed, dict) else None
        if not isinstance(file_id, int) or file_id <= 0:
            return None, None
        logo_file = db.get(AssetFile, file_id)
        if not logo_file or logo_file.is_deleted:
            return None, None
        return file_id, f"/api/v1/storage/files/{logo_file.id}/download"

    logo_file_id, logo_url = resolve_logo_field("logo_file_id")
    logo_light_wide_file_id, logo_light_wide_url = resolve_logo_field("logo_light_wide_file_id")
    logo_light_small_file_id, logo_light_small_url = resolve_logo_field("logo_light_small_file_id")
    logo_dark_wide_file_id, logo_dark_wide_url = resolve_logo_field("logo_dark_wide_file_id")
    logo_dark_small_file_id, logo_dark_small_url = resolve_logo_field("logo_dark_small_file_id")

    return CompanyProfileRead(
        company_name=company_name,
        default_language=(parsed.get("default_language") if isinstance(parsed, dict) else None) or "en",
        logo_file_id=logo_file_id,
        logo_url=logo_url,
        logo_light_wide_file_id=logo_light_wide_file_id,
        logo_light_wide_url=logo_light_wide_url,
        logo_light_small_file_id=logo_light_small_file_id,
        logo_light_small_url=logo_light_small_url,
        logo_dark_wide_file_id=logo_dark_wide_file_id,
        logo_dark_wide_url=logo_dark_wide_url,
        logo_dark_small_file_id=logo_dark_small_file_id,
        logo_dark_small_url=logo_dark_small_url,
        currency=parsed.get("currency") if isinstance(parsed, dict) else None,
        vat_number=parsed.get("vat_number") if isinstance(parsed, dict) else None,
        address_line1=parsed.get("address_line1") if isinstance(parsed, dict) else None,
        address_line2=parsed.get("address_line2") if isinstance(parsed, dict) else None,
        postal_code=parsed.get("postal_code") if isinstance(parsed, dict) else None,
        city=parsed.get("city") if isinstance(parsed, dict) else None,
        country=parsed.get("country") if isinstance(parsed, dict) else None,
        contact_email=parsed.get("contact_email") if isinstance(parsed, dict) else None,
        contact_phone=parsed.get("contact_phone") if isinstance(parsed, dict) else None,
        website=parsed.get("website") if isinstance(parsed, dict) else None,
    )


@router.put("/company-profile", response_model=CompanyProfileRead)
def update_company_profile(
    payload: CompanyProfileUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> CompanyProfileRead:
    def validate_logo_field(field_name: str, file_id: int | None) -> tuple[int | None, str | None]:
        if file_id is None:
            return None, None
        logo_file = db.get(AssetFile, file_id)
        if not logo_file or logo_file.is_deleted:
            raise HTTPException(status_code=400, detail=f"{field_name} does not reference an existing file")
        return file_id, f"/api/v1/storage/files/{logo_file.id}/download"

    logo_file_id, logo_url = validate_logo_field("logo_file_id", payload.logo_file_id)
    logo_light_wide_file_id, logo_light_wide_url = validate_logo_field("logo_light_wide_file_id", payload.logo_light_wide_file_id)
    logo_light_small_file_id, logo_light_small_url = validate_logo_field("logo_light_small_file_id", payload.logo_light_small_file_id)
    logo_dark_wide_file_id, logo_dark_wide_url = validate_logo_field("logo_dark_wide_file_id", payload.logo_dark_wide_file_id)
    logo_dark_small_file_id, logo_dark_small_url = validate_logo_field("logo_dark_small_file_id", payload.logo_dark_small_file_id)

    setting = _get_or_create_setting(
        db,
        COMPANY_PROFILE_KEY,
        {
            "company_name": None,
            "default_language": "en",
            "logo_file_id": None,
            "logo_light_wide_file_id": None,
            "logo_light_small_file_id": None,
            "logo_dark_wide_file_id": None,
            "logo_dark_small_file_id": None,
            "currency": "SEK",
            "vat_number": None,
            "address_line1": None,
            "address_line2": None,
            "postal_code": None,
            "city": None,
            "country": None,
            "contact_email": None,
            "contact_phone": None,
            "website": None,
        },
    )

    normalized_name = payload.company_name.strip() if isinstance(payload.company_name, str) else None
    normalized_default_language = payload.default_language.strip().lower() if isinstance(payload.default_language, str) else None
    if normalized_default_language not in {"en", "sv"}:
        normalized_default_language = "en"
    normalized_currency = payload.currency.strip().upper() if isinstance(payload.currency, str) else None
    normalized_vat = payload.vat_number.strip() if isinstance(payload.vat_number, str) else None
    normalized_address1 = payload.address_line1.strip() if isinstance(payload.address_line1, str) else None
    normalized_address2 = payload.address_line2.strip() if isinstance(payload.address_line2, str) else None
    normalized_postal = payload.postal_code.strip() if isinstance(payload.postal_code, str) else None
    normalized_city = payload.city.strip() if isinstance(payload.city, str) else None
    normalized_country = payload.country.strip() if isinstance(payload.country, str) else None
    normalized_email = payload.contact_email.strip() if isinstance(payload.contact_email, str) else None
    normalized_phone = payload.contact_phone.strip() if isinstance(payload.contact_phone, str) else None
    normalized_website = payload.website.strip() if isinstance(payload.website, str) else None

    setting.value_json = json.dumps(
        {
            "company_name": normalized_name or None,
            "default_language": normalized_default_language,
            "logo_file_id": logo_file_id,
            "logo_light_wide_file_id": logo_light_wide_file_id,
            "logo_light_small_file_id": logo_light_small_file_id,
            "logo_dark_wide_file_id": logo_dark_wide_file_id,
            "logo_dark_small_file_id": logo_dark_small_file_id,
            "currency": normalized_currency or "SEK",
            "vat_number": normalized_vat or None,
            "address_line1": normalized_address1 or None,
            "address_line2": normalized_address2 or None,
            "postal_code": normalized_postal or None,
            "city": normalized_city or None,
            "country": normalized_country or None,
            "contact_email": normalized_email or None,
            "contact_phone": normalized_phone or None,
            "website": normalized_website or None,
        }
    )
    db.commit()

    return CompanyProfileRead(
        company_name=normalized_name or None,
        default_language=normalized_default_language,
        logo_file_id=logo_file_id,
        logo_url=logo_url,
        logo_light_wide_file_id=logo_light_wide_file_id,
        logo_light_wide_url=logo_light_wide_url,
        logo_light_small_file_id=logo_light_small_file_id,
        logo_light_small_url=logo_light_small_url,
        logo_dark_wide_file_id=logo_dark_wide_file_id,
        logo_dark_wide_url=logo_dark_wide_url,
        logo_dark_small_file_id=logo_dark_small_file_id,
        logo_dark_small_url=logo_dark_small_url,
        currency=normalized_currency or "SEK",
        vat_number=normalized_vat or None,
        address_line1=normalized_address1 or None,
        address_line2=normalized_address2 or None,
        postal_code=normalized_postal or None,
        city=normalized_city or None,
        country=normalized_country or None,
        contact_email=normalized_email or None,
        contact_phone=normalized_phone or None,
        website=normalized_website or None,
    )


@router.get("/label-templates", response_model=list[LabelTemplateRead])
def list_label_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[LabelTemplateRead]:
    setting = _get_or_create_setting(db, LABEL_TEMPLATES_KEY, [])
    templates = _parse_label_templates(setting.value_json)
    visible = [item for item in templates if _can_view_label_template(item, current_user)]
    return [LabelTemplateRead(**item) for item in visible]


@router.post("/label-templates", response_model=LabelTemplateRead)
def create_label_template(
    payload: LabelTemplateUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
) -> LabelTemplateRead:
    setting = _get_or_create_setting(db, LABEL_TEMPLATES_KEY, [])
    templates = _parse_label_templates(setting.value_json)

    new_template = _normalize_label_template_payload(payload, current_user)
    templates.insert(0, new_template)
    setting.value_json = json.dumps(templates)
    db.commit()

    emit_realtime_event(
        "settings.updated",
        {
            "entity": "label_template",
            "action": "create",
            "id": new_template["id"],
        },
    )
    return LabelTemplateRead(**new_template)


@router.put("/label-templates/{template_id}", response_model=LabelTemplateRead)
def update_label_template(
    template_id: str,
    payload: LabelTemplateUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
) -> LabelTemplateRead:
    setting = _get_or_create_setting(db, LABEL_TEMPLATES_KEY, [])
    templates = _parse_label_templates(setting.value_json)

    normalized_id = str(template_id or "").strip()
    if not normalized_id:
        raise HTTPException(status_code=400, detail="Template id is required")

    index = next((idx for idx, item in enumerate(templates) if item.get("id") == normalized_id), -1)
    if index < 0:
        raise HTTPException(status_code=404, detail="Label template not found")

    existing = templates[index]
    if not _can_edit_label_template(existing, current_user):
        raise HTTPException(status_code=403, detail="Insufficient permissions to edit this template")

    updated = _normalize_label_template_payload(payload, current_user, existing=existing)
    templates[index] = updated
    setting.value_json = json.dumps(templates)
    db.commit()

    emit_realtime_event(
        "settings.updated",
        {
            "entity": "label_template",
            "action": "update",
            "id": updated["id"],
        },
    )
    return LabelTemplateRead(**updated)


@router.delete("/label-templates/{template_id}")
def delete_label_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
) -> dict[str, bool]:
    setting = _get_or_create_setting(db, LABEL_TEMPLATES_KEY, [])
    templates = _parse_label_templates(setting.value_json)

    normalized_id = str(template_id or "").strip()
    if not normalized_id:
        raise HTTPException(status_code=400, detail="Template id is required")

    index = next((idx for idx, item in enumerate(templates) if item.get("id") == normalized_id), -1)
    if index < 0:
        raise HTTPException(status_code=404, detail="Label template not found")

    existing = templates[index]
    if not _can_edit_label_template(existing, current_user):
        raise HTTPException(status_code=403, detail="Insufficient permissions to delete this template")

    removed_id = existing.get("id")
    templates.pop(index)
    setting.value_json = json.dumps(templates)
    db.commit()

    emit_realtime_event(
        "settings.updated",
        {
            "entity": "label_template",
            "action": "delete",
            "id": removed_id,
        },
    )
    return {"ok": True}


@router.post("/integrations/{plugin}/test", response_model=IntegrationConnectionTestRead)
def test_integration_connection(
    plugin: str,
    payload: IntegrationConnectionTestRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> IntegrationConnectionTestRead:
    plugin_key = str(plugin or "").strip().lower()
    if plugin_key not in ALLOWED_INTEGRATION_PLUGINS:
        raise HTTPException(status_code=404, detail=f"Unknown integration plugin: {plugin}")

    setting = _get_or_create_setting(db, INTEGRATIONS_KEY, DEFAULT_INTEGRATIONS)
    persisted = _parse_integrations(setting.value_json)
    persisted_config = {}
    if plugin_key == "eventory":
        instances = persisted.get("eventory_instances") if isinstance(persisted, dict) else []
        if isinstance(instances, list) and instances:
            persisted_config = instances[0]

    incoming_config = payload.config or IntegrationPluginConfig(**persisted_config)
    normalized = _normalize_plugin_config(incoming_config)

    api_url = str(normalized.get("api_url") or "").strip()
    api_key = str(normalized.get("api_key") or "").strip()

    if not api_url:
        return IntegrationConnectionTestRead(
            ok=False,
            plugin=plugin_key,
            message="API URL is required to test connection",
        )

    try:
        _validate_integration_url(api_url, "API URL")
    except HTTPException as exc:
        return IntegrationConnectionTestRead(
            ok=False,
            plugin=plugin_key,
            message=str(exc.detail),
        )
    parsed = urlparse(api_url)

    headers = {
        "User-Agent": "stockwire-rental-settings-test/1.0",
        "Accept": "application/json, text/plain, */*",
    }

    access_token = None
    username = str(normalized.get("username") or "").strip()
    password = str(normalized.get("password") or "").strip()
    token_endpoint = str(normalized.get("token_endpoint") or "").strip()

    if parsed.scheme != "https":
        if username or password:
            return IntegrationConnectionTestRead(
                ok=False,
                plugin=plugin_key,
                message="API URL must use HTTPS when username/password are configured",
            )
        if api_key:
            return IntegrationConnectionTestRead(
                ok=False,
                plugin=plugin_key,
                message="API URL must use HTTPS when API key is configured",
            )

    if username and password:
        try:
            access_token = _fetch_eventory_token(api_url, token_endpoint, username, password)
        except HTTPException as exc:
            # Allow API-key-only connectivity tests even if OAuth token probing fails.
            if not api_key:
                return IntegrationConnectionTestRead(
                    ok=False,
                    plugin=plugin_key,
                    message=f"Token request failed: {exc.detail}",
                )

    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    elif api_key:
        headers["X-API-Key"] = api_key
        headers["Authorization"] = f"Bearer {api_key}"

    req = Request(api_url, headers=headers, method="HEAD")
    try:
        with build_opener(_NoRedirectHandler()).open(req, timeout=5) as response:
            _ensure_public_response_peer(response, "API URL")
            status_code = int(getattr(response, "status", 0) or 0)
            return IntegrationConnectionTestRead(
                ok=status_code < 500,
                plugin=plugin_key,
                message=f"Connection established (status {status_code})",
                status_code=status_code,
            )
    except HTTPException as exc:
        return IntegrationConnectionTestRead(
            ok=False,
            plugin=plugin_key,
            message=str(exc.detail),
        )
    except HTTPError as exc:
        try:
            try:
                _ensure_public_response_peer(exc, "API URL")
            except HTTPException as peer_exc:
                return IntegrationConnectionTestRead(
                    ok=False,
                    plugin=plugin_key,
                    message=str(peer_exc.detail),
                )
            status_code = int(getattr(exc, "code", 0) or 0)
            return IntegrationConnectionTestRead(
                ok=status_code < 500,
                plugin=plugin_key,
                message=f"Connection reached endpoint (status {status_code})",
                status_code=status_code,
            )
        finally:
            exc.close()
    except URLError as exc:
        get_req = Request(api_url, headers=headers, method="GET")
        try:
            with build_opener(_NoRedirectHandler()).open(get_req, timeout=5) as response:
                _ensure_public_response_peer(response, "API URL")
                status_code = int(getattr(response, "status", 0) or 0)
                return IntegrationConnectionTestRead(
                    ok=status_code < 500,
                    plugin=plugin_key,
                    message=f"Connection established (GET status {status_code})",
                    status_code=status_code,
                )
        except HTTPException as get_peer_exc:
            return IntegrationConnectionTestRead(
                ok=False,
                plugin=plugin_key,
                message=str(get_peer_exc.detail),
            )
        except HTTPError as get_exc:
            try:
                try:
                    _ensure_public_response_peer(get_exc, "API URL")
                except HTTPException as get_peer_exc:
                    return IntegrationConnectionTestRead(
                        ok=False,
                        plugin=plugin_key,
                        message=str(get_peer_exc.detail),
                    )
                status_code = int(getattr(get_exc, "code", 0) or 0)
                return IntegrationConnectionTestRead(
                    ok=status_code < 500,
                    plugin=plugin_key,
                    message=f"Connection reached endpoint (GET status {status_code})",
                    status_code=status_code,
                )
            finally:
                get_exc.close()
        except Exception as get_exc:
            return IntegrationConnectionTestRead(
                ok=False,
                plugin=plugin_key,
                message=f"Connection failed: {get_exc.reason if hasattr(get_exc, 'reason') else str(get_exc)}",
            )


@router.get("/integrations/eventory/{instance_id}/products", response_model=EventoryProductsRead)
def eventory_products_preview(
    instance_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> EventoryProductsRead:
    config = _get_eventory_instance_config(db, instance_id)
    products = _fetch_eventory_products(config)
    normalized = [
        EventoryProductRead(
            id=str(item.get("id") or ""),
            name=str(item.get("name") or ""),
            description=str(item.get("description") or "").strip() or None,
            category=str(item.get("category") or "").strip() or None,
            price=float(item.get("price") or 0),
            quantity_available=max(0, int(item.get("quantity_available") or 0)),
        )
        for item in products
        if str(item.get("id") or "").strip() and str(item.get("name") or "").strip()
    ]
    return EventoryProductsRead(products=normalized, count=len(normalized))


@router.post("/integrations/eventory/{instance_id}/sync", response_model=EventorySyncStartRead)
def eventory_sync(
    instance_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> EventorySyncStartRead:
    target = str(instance_id or "").strip()
    if not target:
        raise HTTPException(status_code=400, detail="Eventory instance id is required")

    _get_eventory_instance_config(db, target)

    with EVENTORY_SYNC_LOCK:
        if target in EVENTORY_SYNC_RUNNING:
            return EventorySyncStartRead(started=False, message="Sync already running for this Eventory instance")
        EVENTORY_SYNC_RUNNING.add(target)

    _set_eventory_sync_runtime_status(
        db,
        target,
        {
            "sync_running": True,
            "sync_started_at": datetime.utcnow().isoformat() + "Z",
            "sync_finished_at": None,
            "sync_progress_current": 0,
            "sync_progress_total": 0,
            "sync_progress_percent": 0,
            "sync_message": "Sync started",
        },
    )
    background_tasks.add_task(_run_eventory_sync_in_background, target)
    return EventorySyncStartRead(started=True, message="Sync started")


@router.get("/integrations/eventory/{instance_id}/sync", response_model=EventorySyncStatusRead)
def eventory_sync_status(
    instance_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> EventorySyncStatusRead:
    config = _get_eventory_instance_config(db, instance_id)
    current = max(0, int(config.get("sync_progress_current") or 0))
    total = max(0, int(config.get("sync_progress_total") or 0))
    percent = max(0, min(100, int(config.get("sync_progress_percent") or 0)))
    if total > 0:
        percent = max(percent, min(100, int(round((current / total) * 100))))

    return EventorySyncStatusRead(
        running=bool(config.get("sync_running") or False),
        progress_current=current,
        progress_total=total,
        progress_percent=percent,
        started_at=str(config.get("sync_started_at") or "").strip() or None,
        finished_at=str(config.get("sync_finished_at") or "").strip() or None,
        imported=max(0, int(config.get("last_sync_imported") or 0)),
        updated=max(0, int(config.get("last_sync_updated") or 0)),
        skipped=max(0, int(config.get("last_sync_skipped") or 0)),
        total=max(0, int(config.get("last_sync_total") or 0)),
        message=str(config.get("sync_message") or "").strip() or None,
    )


def _run_eventory_sync_in_background(instance_id: str) -> None:
    db = SessionLocal()
    try:
        _run_eventory_sync(db, instance_id)
    except Exception as exc:
        _set_eventory_sync_runtime_status(
            db,
            instance_id,
            {
                "sync_running": False,
                "sync_finished_at": datetime.utcnow().isoformat() + "Z",
                "sync_message": f"Sync failed: {str(exc)}",
            },
        )
    finally:
        with EVENTORY_SYNC_LOCK:
            EVENTORY_SYNC_RUNNING.discard(instance_id)
        db.close()


def _run_eventory_sync(db: Session, instance_id: str) -> EventorySyncRead:
    config = _get_eventory_instance_config(db, instance_id)

    _set_eventory_sync_runtime_status(
        db,
        instance_id,
        {
            "sync_running": True,
            "sync_progress_current": 0,
            "sync_progress_total": 100,
            "sync_progress_percent": 0,
            "sync_message": "Preparing Eventory sync",
        },
    )

    def on_fetch_progress(current: int, total: int, message: str) -> None:
        safe_total = max(1, int(total or 1))
        safe_current = max(0, int(current or 0))
        fetch_percent = max(0, min(60, int(round((safe_current / safe_total) * 60))))
        _set_eventory_sync_runtime_status(
            db,
            instance_id,
            {
                "sync_running": True,
                "sync_progress_current": fetch_percent,
                "sync_progress_total": 100,
                "sync_progress_percent": fetch_percent,
                "sync_message": message or "Fetching Eventory rental details",
            },
        )

    products = _fetch_eventory_products(config, on_progress=on_fetch_progress)

    imported = 0
    updated = 0
    skipped = 0
    processed = 0
    total = len(products)
    now = datetime.utcnow()
    supplier_name = str(config.get("supplier_name") or "").strip() or "Eventory"
    margin = max(0.0, float(config.get("price_margin_percent") or 0.0))

    _set_eventory_sync_runtime_status(
        db,
        instance_id,
        {
            "sync_running": True,
            "sync_progress_current": 60 if total > 0 else 100,
            "sync_progress_total": 100,
            "sync_progress_percent": 60 if total > 0 else 100,
            "sync_message": f"Syncing {total} products",
        },
    )

    for item in products:
        external_id = str(item.get("id") or "").strip()
        name = str(item.get("name") or "").strip()
        if not external_id or not name:
            skipped += 1
            processed += 1
            if total > 0:
                db_phase_percent = 60 + int(round((processed / total) * 40))
                _set_eventory_sync_runtime_status(
                    db,
                    instance_id,
                    {
                        "sync_progress_current": max(0, min(100, db_phase_percent)),
                        "sync_progress_total": 100,
                        "sync_progress_percent": max(0, min(100, db_phase_percent)),
                        "sync_message": f"Syncing products ({processed}/{total})",
                    },
                )
            continue

        category = str(item.get("category") or "").strip() or "general"
        rental_price = max(0.0, float(item.get("price") or 0.0))
        eventory_available_qty = max(0, int(item.get("quantity_available") or 0))
        packlists = item.get("packlists") if isinstance(item.get("packlists"), list) else []
        external_reference = f"{instance_id}:{external_id}"
        sku = f"EVT-{instance_id.upper()}-{external_id}"[:64]

        existing = db.scalar(
            select(Product).where(
                Product.external_source == "eventory",
                Product.external_reference == external_reference,
            )
        )
        if existing is None:
            existing = db.scalar(select(Product).where(Product.sku == sku))

        target_daily_rate = _apply_margin_price(rental_price, margin) if margin > 0 else rental_price

        if existing is None:
            row = Product(
                sku=sku,
                name=name,
                category=category,
                product_type="rental",
                is_rental_product=True,
                supplier_name=supplier_name,
                rental_price=rental_price,
                eventory_available_qty=eventory_available_qty,
                eventory_packlists_json=json.dumps(packlists, ensure_ascii=True),
                daily_rate=target_daily_rate,
                external_source="eventory",
                external_reference=external_reference,
                created_at=now,
            )
            db.add(row)
            imported += 1
        else:
            existing.name = name
            existing.category = category
            existing.product_type = "rental"
            existing.is_rental_product = True
            existing.supplier_name = supplier_name
            existing.rental_price = rental_price
            existing.eventory_available_qty = eventory_available_qty
            existing.eventory_packlists_json = json.dumps(packlists, ensure_ascii=True)
            if margin > 0:
                existing.daily_rate = target_daily_rate
            existing.external_source = "eventory"
            existing.external_reference = external_reference
            updated += 1

        processed += 1
        if processed % 20 == 0:
            db.commit()
        if total > 0:
            db_phase_percent = 60 + int(round((processed / total) * 40))
            _set_eventory_sync_runtime_status(
                db,
                instance_id,
                {
                    "sync_progress_current": max(0, min(100, db_phase_percent)),
                    "sync_progress_total": 100,
                    "sync_progress_percent": max(0, min(100, db_phase_percent)),
                    "sync_message": f"Syncing products ({processed}/{total})",
                },
            )

    db.commit()
    _record_eventory_sync_status(
        db,
        instance_id,
        imported=imported,
        updated=updated,
        skipped=skipped,
        total=total,
    )
    message = f"Sync complete: {imported} imported, {updated} updated, {skipped} skipped"
    _set_eventory_sync_runtime_status(
        db,
        instance_id,
        {
            "sync_running": False,
            "sync_finished_at": datetime.utcnow().isoformat() + "Z",
            "sync_progress_current": 100,
            "sync_progress_total": 100,
            "sync_progress_percent": 100,
            "sync_message": message,
        },
    )
    emit_realtime_event(
        "inventory.updated",
        {
            "entity": "product",
            "action": "eventory_sync",
            "instance_id": instance_id,
            "imported": imported,
            "updated": updated,
            "skipped": skipped,
            "total": total,
        },
    )
    emit_realtime_event(
        "settings.updated",
        {
            "entity": "integration",
            "action": "eventory_sync_status",
            "instance_id": instance_id,
            "running": False,
            "progress_current": 100,
            "progress_total": 100,
            "progress_percent": 100,
        },
    )
    return EventorySyncRead(imported=imported, updated=updated, skipped=skipped, total=total, message=message)


def _get_or_create_setting(db: Session, key: str, default_value: object) -> AppSetting:
    setting = db.scalar(select(AppSetting).where(AppSetting.key == key))
    if setting is None:
        setting = AppSetting(key=key, value_json=json.dumps(default_value))
        db.add(setting)
        db.commit()
        db.refresh(setting)
    return setting


def _parse_string_list(raw: str | None, fallback: list[str]) -> list[str]:
    if not raw:
        return fallback.copy()
    try:
        data = json.loads(raw)
    except Exception:
        return fallback.copy()
    if isinstance(data, list):
        return [str(item) for item in data]
    return fallback.copy()


def _parse_nested_string_list(raw: str | None, fallback: list[list[str]]) -> list[list[str]]:
    if not raw:
        return [path[:] for path in fallback]
    try:
        data = json.loads(raw)
    except Exception:
        return [path[:] for path in fallback]
    if not isinstance(data, list):
        return [path[:] for path in fallback]

    output: list[list[str]] = []
    for item in data:
        if not isinstance(item, list):
            continue
        output.append([str(part) for part in item])
    return output or [path[:] for path in fallback]


def _normalize_options_lower(options: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for item in options:
        value = str(item or "").strip().lower()
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return normalized or DEFAULT_LOCATION_TYPES.copy()


def _normalize_options_keep_case(options: list[str], fallback: list[str]) -> list[str]:
    normalized: list[str] = []
    seen_lower: set[str] = set()
    for item in options:
        value = str(item or "").strip()
        if not value:
            continue
        lower = value.lower()
        if lower in seen_lower:
            continue
        seen_lower.add(lower)
        normalized.append(value)
    return normalized or fallback.copy()


def _normalize_default_option(value: str | None, options: list[str]) -> str | None:
    if not options:
        return None
    requested = str(value or "").strip()
    if not requested:
        return options[0]

    requested_lower = requested.lower()
    for option in options:
        if option.lower() == requested_lower:
            return option
    return options[0]


def _normalize_category_paths(paths: list[list[str]]) -> list[list[str]]:
    normalized: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    for path in paths:
        if not isinstance(path, list):
            continue
        parts = [str(part or "").strip() for part in path]
        parts = [part for part in parts if part]
        if not parts:
            continue
        dedupe_key = tuple(part.lower() for part in parts)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        normalized.append(parts)

    return normalized or [path[:] for path in DEFAULT_CATEGORY_PREFILL_PATHS]


def _merge_unique_lower(primary: list[str], secondary: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for values in (primary, secondary):
        for item in values:
            value = str(item or "").strip().lower()
            if not value or value in seen:
                continue
            seen.add(value)
            merged.append(value)
    return merged or DEFAULT_LOCATION_TYPES.copy()


def _get_used_zone_types(db: Session) -> list[str]:
    rows = db.scalars(select(Zone.zone_type)).all()
    normalized: list[str] = []
    seen: set[str] = set()
    for row in rows:
        value = str(row or "").strip().lower()
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return normalized


def _parse_integrations(raw: str | None) -> dict[str, object]:
    if not raw:
        return {
            "eventory_instances": [_normalize_eventory_instance(EventoryInstanceConfig(**DEFAULT_INTEGRATIONS["eventory_instances"][0]))],
        }
    try:
        data = json.loads(raw)
    except Exception:
        data = {}

    eventory_instances_raw = []
    if isinstance(data, dict):
        if isinstance(data.get("eventory_instances"), list):
            eventory_instances_raw = data.get("eventory_instances") or []
        elif isinstance(data.get("eventory"), dict):
            # Backward compatibility for old single-instance eventory shape.
            eventory_instances_raw = [
                {
                    "id": "eventory-main",
                    "name": "Eventory Main",
                    **(data.get("eventory") or {}),
                }
            ]
    normalized_instances = []
    for index, item in enumerate(eventory_instances_raw):
        payload = item if isinstance(item, dict) else {}
        if not payload.get("id"):
            payload = {**payload, "id": f"eventory-{index + 1}"}
        if not payload.get("name"):
            payload = {**payload, "name": f"Eventory {index + 1}"}
        normalized_instances.append(_normalize_eventory_instance(EventoryInstanceConfig(**payload)))
    if not normalized_instances:
        normalized_instances.append(_normalize_eventory_instance(EventoryInstanceConfig(**DEFAULT_INTEGRATIONS["eventory_instances"][0])))

    return {
        "eventory_instances": normalized_instances,
    }


def _parse_label_templates(raw: str | None) -> list[dict[str, object]]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except Exception:
        return []
    if not isinstance(data, list):
        return []

    normalized: list[dict[str, object]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            parsed = LabelTemplateRead(**item)
        except Exception:
            continue
        normalized.append(parsed.model_dump())
    return normalized


def _normalize_label_template_payload(
    payload: LabelTemplateUpsert,
    current_user: User,
    existing: dict[str, object] | None = None,
) -> dict[str, object]:
    now = datetime.utcnow().isoformat()
    existing_id = str(existing.get("id") or "").strip() if isinstance(existing, dict) else ""
    template_id = existing_id or f"tpl-{int(datetime.utcnow().timestamp() * 1000)}"

    created_by_user_id = int(existing.get("created_by_user_id") or 0) if isinstance(existing, dict) else int(current_user.id or 0)
    created_by_name = str(existing.get("created_by_name") or "").strip() if isinstance(existing, dict) else str(current_user.full_name or current_user.email or "")
    created_at = str(existing.get("created_at") or "").strip() if isinstance(existing, dict) else now

    if not created_by_user_id:
        created_by_user_id = int(current_user.id or 0)
    if not created_by_name:
        created_by_name = str(current_user.full_name or current_user.email or "")
    if not created_at:
        created_at = now

    clean_roles: list[str] = []
    for role in payload.edit_roles or []:
        value = str(role or "").strip().lower()
        if value not in {"admin", "manager", "viewer"}:
            continue
        if value in clean_roles:
            continue
        clean_roles.append(value)
    if not clean_roles:
        clean_roles = ["admin", "manager"]

    canvas = LabelTemplateCanvas(**payload.canvas.model_dump())
    elements = [LabelTemplateElement(**item.model_dump()) for item in (payload.elements or [])]

    normalized = LabelTemplateRead(
        id=template_id,
        name=str(payload.name or "").strip(),
        entity_type=payload.entity_type,
        print_preset=payload.print_preset,
        visibility=payload.visibility,
        edit_roles=clean_roles,
        canvas=canvas,
        elements=elements,
        created_by_user_id=created_by_user_id,
        created_by_name=created_by_name,
        created_at=created_at,
        updated_at=now,
    )
    return normalized.model_dump()


def _can_view_label_template(template: dict[str, object], current_user: User) -> bool:
    role = str(current_user.role or "").strip().lower()
    visibility = str(template.get("visibility") or "all").strip().lower()
    owner_id = int(template.get("created_by_user_id") or 0)
    current_user_id = int(current_user.id or 0)

    if role == "admin" or bool(getattr(current_user, "is_admin", False)):
        return True
    if visibility == "all":
        return True
    if visibility == "owner":
        return owner_id > 0 and owner_id == current_user_id
    if visibility == "admin":
        return role == "admin"
    return True


def _can_edit_label_template(template: dict[str, object], current_user: User) -> bool:
    role = str(current_user.role or "").strip().lower()
    if role == "admin" or bool(getattr(current_user, "is_admin", False)):
        return True

    owner_id = int(template.get("created_by_user_id") or 0)
    current_user_id = int(current_user.id or 0)
    if owner_id > 0 and owner_id == current_user_id:
        return True

    edit_roles = template.get("edit_roles")
    if isinstance(edit_roles, list):
        normalized_roles = {str(item or "").strip().lower() for item in edit_roles}
        if role in normalized_roles:
            return True

    return False


def _normalize_eventory_instance(config: EventoryInstanceConfig) -> dict[str, object]:
    base = _normalize_plugin_config(config)
    identifier = _normalize_instance_identifier(config.id) or "eventory-main"
    name = str(config.name or "").strip() or identifier
    return {
        "id": identifier,
        "name": name,
        **base,
    }


def _normalize_plugin_config(config: IntegrationPluginConfig) -> dict[str, object]:
    api_url = str(config.api_url or "").strip() or DEFAULT_EVENTORY_API_URL
    api_key = str(config.api_key or "").strip() or None
    username = str(config.username or "").strip() or None
    password = str(config.password or "").strip() or None
    token_endpoint = str(config.token_endpoint or "").strip() or None
    supplier_name = str(config.supplier_name or "").strip() or None
    last_sync_at = str(config.last_sync_at or "").strip() or None
    sync_started_at = str(config.sync_started_at or "").strip() or None
    sync_finished_at = str(config.sync_finished_at or "").strip() or None
    sync_message = str(config.sync_message or "").strip() or None

    return {
        "enabled": bool(config.enabled),
        "api_url": api_url,
        "api_key": api_key,
        "username": username,
        "password": password,
        "token_endpoint": token_endpoint,
        "supplier_name": supplier_name,
        "sync_interval_minutes": max(0, int(config.sync_interval_minutes or 0)),
        "price_margin_percent": max(0.0, float(config.price_margin_percent or 0)),
        "last_sync_at": last_sync_at,
        "last_sync_imported": max(0, int(config.last_sync_imported or 0)),
        "last_sync_updated": max(0, int(config.last_sync_updated or 0)),
        "last_sync_skipped": max(0, int(config.last_sync_skipped or 0)),
        "last_sync_total": max(0, int(config.last_sync_total or 0)),
        "sync_running": bool(config.sync_running),
        "sync_started_at": sync_started_at,
        "sync_finished_at": sync_finished_at,
        "sync_progress_current": max(0, int(config.sync_progress_current or 0)),
        "sync_progress_total": max(0, int(config.sync_progress_total or 0)),
        "sync_progress_percent": max(0, min(100, int(config.sync_progress_percent or 0))),
        "sync_message": sync_message,
    }


def _validate_url_port(raw_url: str, label: str) -> None:
    value = str(raw_url or "").strip()
    if not value:
        return
    try:
        port = urlparse(value).port
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"{label} contains an invalid port") from exc
    if port is not None and port <= 0:
        raise HTTPException(status_code=422, detail=f"{label} contains an invalid port")


def _parse_product_defaults(raw: str | None) -> dict[str, object]:
    fallback = {
        "brand_options": DEFAULT_BRAND_OPTIONS.copy(),
        "manufacturer_options": DEFAULT_MANUFACTURER_OPTIONS.copy(),
        "default_brand": DEFAULT_BRAND_OPTIONS[0],
        "default_manufacturer": DEFAULT_MANUFACTURER_OPTIONS[0],
        "brand_manufacturer_map": {},
        "brand_links": {},
        "manufacturer_links": {},
    }
    if not raw:
        return fallback

    try:
        data = json.loads(raw)
    except Exception:
        return fallback

    if not isinstance(data, dict):
        return fallback

    brand_options = _normalize_options_keep_case(data.get("brand_options") or [], DEFAULT_BRAND_OPTIONS)
    manufacturer_options = _normalize_options_keep_case(data.get("manufacturer_options") or [], DEFAULT_MANUFACTURER_OPTIONS)
    brand_manufacturer_map = _normalize_brand_manufacturer_map(data.get("brand_manufacturer_map") or {}, brand_options, manufacturer_options)
    brand_links = _normalize_links(data.get("brand_links") or {}, brand_options)
    manufacturer_links = _normalize_links(data.get("manufacturer_links") or {}, manufacturer_options)

    return {
        "brand_options": brand_options,
        "manufacturer_options": manufacturer_options,
        "default_brand": _normalize_default_option(data.get("default_brand"), brand_options),
        "default_manufacturer": _normalize_default_option(data.get("default_manufacturer"), manufacturer_options),
        "brand_manufacturer_map": brand_manufacturer_map,
        "brand_links": brand_links,
        "manufacturer_links": manufacturer_links,
    }


def _normalize_brand_manufacturer_map(
    raw_map: dict[str, str],
    brand_options: list[str],
    manufacturer_options: list[str],
) -> dict[str, str]:
    if not isinstance(raw_map, dict):
        return {}

    normalized: dict[str, str] = {}
    for raw_brand, raw_manufacturer in raw_map.items():
        brand = _find_matching_option(str(raw_brand or ""), brand_options)
        manufacturer = _find_matching_option(str(raw_manufacturer or ""), manufacturer_options)
        if not brand or not manufacturer:
            continue
        normalized[brand] = manufacturer
    return normalized


def _normalize_links(raw_links: dict[str, str], options: list[str]) -> dict[str, str]:
    if not isinstance(raw_links, dict):
        return {}

    normalized: dict[str, str] = {}
    for raw_key, raw_url in raw_links.items():
        key = _find_matching_option(str(raw_key or ""), options)
        url = str(raw_url or "").strip()
        if not key or not url:
            continue
        normalized[key] = url
    return normalized


def _find_matching_option(value: str, options: list[str]) -> str | None:
    needle = str(value or "").strip().lower()
    if not needle:
        return None
    for option in options:
        if option.lower() == needle:
            return option
    return None


def _get_eventory_instance_config(db: Session, instance_id: str) -> dict[str, object]:
    key = str(instance_id or "").strip()
    key_normalized = _normalize_instance_identifier(key)
    if not key:
        raise HTTPException(status_code=400, detail="Instance ID is required")

    setting = _get_or_create_setting(db, INTEGRATIONS_KEY, DEFAULT_INTEGRATIONS)
    parsed = _parse_integrations(setting.value_json)
    instances = parsed.get("eventory_instances") if isinstance(parsed, dict) else []
    if not isinstance(instances, list):
        instances = []

    for item in instances:
        item_id = str(item.get("id") or "").strip()
        item_id_normalized = _normalize_instance_identifier(item_id)
        item_name_normalized = _normalize_instance_identifier(item.get("name"))
        if key not in {item_id, item_id_normalized, item_name_normalized} and key_normalized not in {
            item_id,
            item_id_normalized,
            item_name_normalized,
        }:
            continue

        cfg = dict(item)
        if not bool(cfg.get("enabled")):
            raise HTTPException(status_code=409, detail="Eventory instance is disabled")

        _validate_integration_url(str(cfg.get("api_url") or ""), "API URL")
        token_endpoint = str(cfg.get("token_endpoint") or "").strip()
        if token_endpoint:
            _validate_integration_url(token_endpoint, "Token endpoint")

        username = str(cfg.get("username") or "").strip()
        password = str(cfg.get("password") or "").strip()
        api_url = str(cfg.get("api_url") or "").strip().lower()
        api_key = str(cfg.get("api_key") or "").strip()

        if (username or password) and not token_endpoint and not api_url.startswith("https://"):
            raise HTTPException(status_code=400, detail="API URL must use HTTPS when username/password are configured")
        if (username or password) and token_endpoint and not token_endpoint.lower().startswith("https://"):
            raise HTTPException(status_code=400, detail="Token endpoint must use HTTPS when username/password are configured")
        if api_key and not api_url.startswith("https://"):
            raise HTTPException(status_code=400, detail="API URL must use HTTPS when API key is configured")

        interval = int(cfg.get("sync_interval_minutes") or 0)
        if interval not in ALLOWED_SYNC_INTERVALS:
            raise HTTPException(status_code=400, detail="Invalid sync interval")

        return cfg

    raise HTTPException(status_code=404, detail=f"Unknown Eventory instance: {key}")


def _normalize_instance_identifier(raw_value: object) -> str:
    value = str(raw_value or "").strip().lower()
    if not value:
        return ""
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value


def _validate_integration_url(raw_url: str, label: str) -> None:
    value = str(raw_url or "").strip()
    if not value:
        raise HTTPException(status_code=422, detail=f"{label} is required")

    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=422, detail=f"{label} must be an absolute http(s) URL")
    if parsed.username or parsed.password:
        raise HTTPException(status_code=422, detail=f"{label} must not contain embedded credentials")
    try:
        port = parsed.port
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"{label} contains an invalid port") from exc
    if port is not None and port <= 0:
        raise HTTPException(status_code=422, detail=f"{label} contains an invalid port")

    host = (parsed.hostname or "").strip()
    if not host:
        raise HTTPException(status_code=422, detail=f"{label} hostname is invalid")

    host_l = host.lower()
    if host_l in {"localhost", "127.0.0.1", "::1"}:
        raise HTTPException(status_code=422, detail=f"{label} must not target localhost")

    try:
        ip_obj = ipaddress.ip_address(host)
        if _is_blocked_ip(ip_obj):
            raise HTTPException(status_code=422, detail=f"{label} must not target private/reserved IP addresses")
        return
    except ValueError:
        pass

    try:
        resolved = socket.getaddrinfo(host, None)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"{label} hostname could not be resolved: {exc}") from exc

    for item in resolved:
        candidate = item[4][0]
        try:
            ip_obj = ipaddress.ip_address(candidate)
        except ValueError:
            continue
        if _is_blocked_ip(ip_obj):
            raise HTTPException(status_code=422, detail=f"{label} resolves to private/reserved IP addresses")


def _is_blocked_ip(ip_obj: ipaddress._BaseAddress) -> bool:
    return bool(
        ip_obj.is_private
        or ip_obj.is_loopback
        or ip_obj.is_link_local
        or ip_obj.is_multicast
        or ip_obj.is_reserved
        or ip_obj.is_unspecified
    )


def _eventory_set_headers(headers: dict[str, str], oauth_token: str | None, api_key: str | None) -> None:
    token = str(oauth_token or "").strip()
    key = str(api_key or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    elif key:
        headers["Authorization"] = f"Bearer {key}"
    if key:
        headers["X-API-Key"] = key


def _fetch_eventory_products(
    config: dict[str, object],
    on_progress: Callable[[int, int, str], None] | None = None,
) -> list[dict[str, object]]:
    api_url = str(config.get("api_url") or "").strip()
    api_key = str(config.get("api_key") or "").strip()
    username = str(config.get("username") or "").strip()
    password = str(config.get("password") or "").strip()
    token_endpoint = str(config.get("token_endpoint") or "").strip()

    oauth_token = ""
    if username and password:
        oauth_token = _fetch_eventory_token(api_url, token_endpoint, username, password)

    inventory_url = urljoin(api_url.rstrip("/") + "/", "inventory-rentals")
    headers = {
        "User-Agent": "stockwire-rental-eventory-sync/1.0",
        "Accept": "application/json",
    }
    _eventory_set_headers(headers, oauth_token, api_key)

    req = Request(inventory_url, headers=headers, method="GET")
    try:
        with urlopen(req, timeout=15) as response:
            if int(getattr(response, "status", 0) or 0) != 200:
                raise HTTPException(status_code=502, detail=f"Eventory inventory endpoint returned status {getattr(response, 'status', 0)}")
            payload = json.loads(response.read().decode("utf-8") or "[]")
            if not isinstance(payload, list):
                raise HTTPException(status_code=502, detail="Eventory inventory response has unsupported format")
            leaf_total = _count_inventory_leaf_nodes(payload)
            if on_progress:
                try:
                    on_progress(0, max(leaf_total, 1), "Fetching Eventory rental details")
                except Exception:
                    pass
            return _flatten_inventory_nodes(api_url, headers, payload, on_progress=on_progress, progress_total=max(leaf_total, 1))
    except HTTPError as exc:
        if int(getattr(exc, "code", 0) or 0) == 404:
            return _fetch_eventory_products_legacy(api_url, headers)
        raise HTTPException(status_code=502, detail=f"Eventory inventory request failed ({exc.code})") from exc
    except URLError as exc:
        raise HTTPException(status_code=502, detail=f"Eventory inventory request failed: {exc.reason if hasattr(exc, 'reason') else str(exc)}") from exc


def _url_origin(url: str) -> tuple[str, str, int] | None:
    parsed = urlparse(str(url or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    try:
        port = parsed.port if parsed.port is not None else (443 if parsed.scheme == "https" else 80)
    except ValueError:
        return None
    return (parsed.scheme, parsed.hostname.lower(), port)


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HTTPError(req.full_url, code, "redirect blocked", headers, fp)


def _is_same_origin_url(url: str, expected_origin: tuple[str, str, int]) -> bool:
    origin = _url_origin(url)
    return origin is not None and origin == expected_origin


def _is_public_http_url(url: str) -> bool:
    parsed = urlparse(str(url or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        return False
    try:
        port = parsed.port
    except ValueError:
        return False
    if port is not None and port <= 0:
        return False
    if port is None:
        port = 443 if parsed.scheme == "https" else 80
    try:
        infos = socket.getaddrinfo(parsed.hostname, port, type=socket.SOCK_STREAM)
    except (OSError, UnicodeError):
        return False
    addresses = {info[4][0] for info in infos if info and len(info) > 4 and info[4]}
    if not addresses:
        return False
    try:
        return not any(_is_blocked_ip(ipaddress.ip_address(addr)) for addr in addresses)
    except ValueError:
        return False


def _response_peer_ip(response: object) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    seen: set[int] = set()
    stack: list[object] = [response]
    while stack:
        current = stack.pop()
        if current is None or id(current) in seen:
            continue
        seen.add(id(current))

        sock = getattr(current, "_sock", None)
        if sock is not None:
            try:
                peer = sock.getpeername()
            except OSError:
                peer = None
            if isinstance(peer, tuple) and peer:
                try:
                    return ipaddress.ip_address(peer[0])
                except ValueError:
                    pass

        for attr in ("fp", "raw"):
            nested = getattr(current, attr, None)
            if nested is not None:
                stack.append(nested)
    return None


def _ensure_public_response_peer(response: object, label: str) -> None:
    peer_ip = _response_peer_ip(response)
    if peer_ip is None:
        raise HTTPException(status_code=502, detail=f"{label} peer address could not be verified")
    if _is_blocked_ip(peer_ip):
        raise HTTPException(status_code=502, detail=f"{label} connected to a non-public IP address")


def _fetch_eventory_token(api_url: str, token_endpoint: str, username: str, password: str) -> str:
    base_origin = _url_origin(api_url)
    if base_origin is None:
        raise HTTPException(status_code=400, detail="Invalid API URL for token request")

    if token_endpoint:
        token_candidate = str(token_endpoint or "").strip()
        if not _is_same_origin_url(token_candidate, base_origin):
            raise HTTPException(
                status_code=400,
                detail="Token endpoint must be an absolute http(s) URL on the same origin as API URL",
            )
        candidates = [token_candidate]
    else:
        candidates = [
            urljoin(api_url.rstrip("/") + "/", "login-json"),
            urljoin(api_url.rstrip("/") + "/", "login"),
            urljoin(api_url.rstrip("/") + "/", "oauth/token"),
        ]

    last_error: Exception | None = None
    for candidate in candidates:
        if not _is_same_origin_url(candidate, base_origin):
            continue
        if not _is_public_http_url(candidate):
            raise HTTPException(
                status_code=400,
                detail="Token endpoint must be a valid public http(s) URL",
            )
        body = urlencode(
            {
                "grant_type": "password",
                "username": username,
                "password": password,
            }
        ).encode("utf-8")
        req = Request(
            candidate,
            data=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "User-Agent": "stockwire-rental-eventory-sync/1.0",
            },
            method="POST",
        )
        try:
            with build_opener(_NoRedirectHandler()).open(req, timeout=10) as resp:
                _ensure_public_response_peer(resp, "Token endpoint")
                payload = json.loads(resp.read().decode("utf-8") or "{}")
                if not isinstance(payload, dict):
                    raise ValueError("token response is not an object")
                token = str(
                    payload.get("access_token")
                    or payload.get("token")
                    or payload.get("jwt")
                    or payload.get("id_token")
                    or ""
                ).strip()
                if not token and isinstance(payload.get("data"), dict):
                    data = payload.get("data") or {}
                    token = str(
                        data.get("access_token")
                        or data.get("token")
                        or data.get("jwt")
                        or data.get("id_token")
                        or ""
                    ).strip()
                if token:
                    return token
                raise ValueError("token response contained no token field")
        except HTTPError as exc:
            try:
                _ensure_public_response_peer(exc, "Token endpoint")
            except HTTPException:
                exc.close()
                raise
            last_error = exc
            exc.close()
            continue
        except HTTPException:
            raise
        except Exception as exc:
            last_error = exc
            continue

    raise HTTPException(status_code=502, detail=f"Eventory token request failed: {last_error}")


def _flatten_inventory_nodes(
    api_url: str,
    headers: dict[str, str],
    nodes: list[object],
    category_path: str = "",
    on_progress: Callable[[int, int, str], None] | None = None,
    progress_total: int = 0,
    progress_state: dict[str, int] | None = None,
) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    state = progress_state if isinstance(progress_state, dict) else {"processed": 0}
    for item in nodes:
        if not isinstance(item, dict):
            continue
        children = item.get("children")
        if isinstance(children, list):
            node_name = str(item.get("name") or "").strip()
            child_path = node_name if not category_path else (f"{category_path} > {node_name}" if node_name else category_path)
            child_rows = _flatten_inventory_nodes(
                api_url,
                headers,
                children,
                child_path,
                on_progress=on_progress,
                progress_total=progress_total,
                progress_state=state,
            )
            output.extend(child_rows)
            continue

        external_id = str(item.get("id") or "").strip()
        name = str(item.get("name") or "").strip()
        if not external_id or not name:
            continue
        description, daily_rate, detail_available_qty, detail_packlists = _fetch_eventory_rental_detail(api_url, headers, external_id)
        item_available_qty = _parse_available_quantity(item)
        output.append(
            {
                "id": external_id,
                "name": name,
                "description": description,
                "category": category_path or None,
                "price": daily_rate,
                "quantity_available": max(detail_available_qty, item_available_qty),
                "packlists": detail_packlists,
            }
        )
        state["processed"] = max(0, int(state.get("processed") or 0)) + 1
        if on_progress and progress_total > 0:
            try:
                current = max(0, int(state.get("processed") or 0))
                on_progress(current, progress_total, f"Fetching Eventory rental details ({current}/{progress_total})")
            except Exception:
                pass
    return output


def _count_inventory_leaf_nodes(nodes: list[object]) -> int:
    count = 0
    for item in nodes:
        if not isinstance(item, dict):
            continue
        children = item.get("children")
        if isinstance(children, list):
            count += _count_inventory_leaf_nodes(children)
            continue
        external_id = str(item.get("id") or "").strip()
        name = str(item.get("name") or "").strip()
        if external_id and name:
            count += 1
    return count


def _fetch_eventory_rental_detail(api_url: str, headers: dict[str, str], rental_id: str) -> tuple[str | None, float, int, list[dict[str, object]]]:
    detail_url = urljoin(api_url.rstrip("/") + "/", f"rentals/{rental_id}")
    req = Request(detail_url, headers=headers, method="GET")
    try:
        with urlopen(req, timeout=10) as resp:
            if int(getattr(resp, "status", 0) or 0) != 200:
                return None, 0.0, 0, []
            data = json.loads(resp.read().decode("utf-8") or "{}")
            if not isinstance(data, dict):
                return None, 0.0, 0, []
            rental = _resolve_eventory_rental_payload(data)
            resolved_daily_rate = _parse_daily_rate(rental)
            if resolved_daily_rate <= 0:
                resolved_daily_rate = _parse_daily_rate(data)

            resolved_available_qty = _parse_available_quantity(rental)
            if resolved_available_qty <= 0:
                resolved_available_qty = _parse_available_quantity(data)
            resolved_packlists = _parse_eventory_packlists(data)
            return (
                str(rental.get("description") or "").strip() or None,
                resolved_daily_rate,
                resolved_available_qty,
                resolved_packlists,
            )
    except Exception:
        return None, 0.0, 0, []


def _fetch_eventory_products_legacy(api_url: str, headers: dict[str, str]) -> list[dict[str, object]]:
    endpoints = ["api/v1/products", "api/products", "products"]
    last_error: Exception | None = None
    for endpoint in endpoints:
        target = urljoin(api_url.rstrip("/") + "/", endpoint)
        req = Request(target, headers=headers, method="GET")
        try:
            with urlopen(req, timeout=15) as response:
                if int(getattr(response, "status", 0) or 0) != 200:
                    raise ValueError(f"status {getattr(response, 'status', 0)}")
                body = json.loads(response.read().decode("utf-8") or "[]")
                return _parse_legacy_products_response(body)
        except Exception as exc:
            last_error = exc
            continue

    raise HTTPException(status_code=502, detail=f"Failed to fetch Eventory products from all known endpoints: {last_error}")


def _parse_legacy_products_response(body: object) -> list[dict[str, object]]:
    if isinstance(body, list):
        rows = body
    elif isinstance(body, dict):
        rows = None
        for key in ("data", "products", "items", "results"):
            if isinstance(body.get(key), list):
                rows = body.get(key)
                break
        if rows is None:
            raise HTTPException(status_code=502, detail="Unsupported legacy Eventory response format")
    else:
        raise HTTPException(status_code=502, detail="Unsupported legacy Eventory response format")

    output: list[dict[str, object]] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        external_id = str(item.get("id") or "").strip()
        name = str(item.get("name") or "").strip()
        if not external_id or not name:
            continue
        output.append(
            {
                "id": external_id,
                "name": name,
                "description": str(item.get("description") or "").strip() or None,
                "category": str(item.get("category") or "").strip() or None,
                "price": max(0.0, float(item.get("price") or 0.0)),
                "quantity_available": _parse_available_quantity(item),
            }
        )
    return output


def _parse_available_quantity(row: object) -> int:
    if not isinstance(row, dict):
        return 0
    candidates = [
        row.get("available"),
        row.get("available_qty"),
        row.get("available_quantity"),
        row.get("qty_available"),
        row.get("quantity_available"),
        row.get("stockLevel"),
        row.get("stock_level"),
        row.get("availableStock"),
        row.get("available_stock"),
        row.get("totalAvailable"),
        row.get("numberAvailable"),
        row.get("quantity"),
        row.get("qty"),
        row.get("inStock"),
        row.get("stock"),
    ]

    stock_obj = row.get("stock") if isinstance(row.get("stock"), dict) else None
    if isinstance(stock_obj, dict):
        candidates.extend(
            [
                stock_obj.get("available"),
                stock_obj.get("available_qty"),
                stock_obj.get("available_quantity"),
                stock_obj.get("stockLevel"),
                stock_obj.get("stock_level"),
                stock_obj.get("level"),
                stock_obj.get("quantity"),
                stock_obj.get("qty"),
            ]
        )

    inventory_obj = row.get("inventory") if isinstance(row.get("inventory"), dict) else None
    if isinstance(inventory_obj, dict):
        candidates.extend(
            [
                inventory_obj.get("available"),
                inventory_obj.get("available_qty"),
                inventory_obj.get("available_quantity"),
                inventory_obj.get("stockLevel"),
                inventory_obj.get("stock_level"),
                inventory_obj.get("level"),
                inventory_obj.get("quantity"),
                inventory_obj.get("qty"),
            ]
        )

    for value in candidates:
        if value in (None, ""):
            continue
        try:
            return max(0, int(float(value)))
        except (TypeError, ValueError):
            continue
    return 0


def _resolve_eventory_rental_payload(data: dict[str, object]) -> dict[str, object]:
    if isinstance(data.get("rental"), dict):
        return data.get("rental")  # type: ignore[return-value]

    if isinstance(data.get("data"), dict):
        wrapped = data.get("data")
        if isinstance(wrapped.get("rental"), dict):
            return wrapped.get("rental")  # type: ignore[return-value]
        return wrapped

    if isinstance(data.get("item"), dict):
        return data.get("item")  # type: ignore[return-value]

    return data


def _parse_daily_rate(row: dict[str, object]) -> float:
    candidates = [
        row.get("dailyRate"),
        row.get("daily_rate"),
        row.get("pricePerDay"),
        row.get("price_per_day"),
        row.get("price"),
    ]
    for value in candidates:
        if value in (None, ""):
            continue
        try:
            return max(0.0, float(value))
        except (TypeError, ValueError):
            continue
    return 0.0


def _parse_eventory_packlists(detail_payload: dict[str, object]) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    sources: list[tuple[str, object]] = [
        ("active", detail_payload.get("activePackLists")),
        ("archived", detail_payload.get("archivedPackLists")),
    ]

    wrapped = detail_payload.get("data") if isinstance(detail_payload.get("data"), dict) else None
    if isinstance(wrapped, dict):
        sources.extend(
            [
                ("active", wrapped.get("activePackLists")),
                ("archived", wrapped.get("archivedPackLists")),
            ]
        )

    for source_name, rows in sources:
        if not isinstance(rows, list):
            continue
        for item in rows:
            if not isinstance(item, dict):
                continue
            pack_list_id = str(item.get("packListId") or item.get("pack_list_id") or "").strip()
            if not pack_list_id:
                continue
            output.append(
                {
                    "pack_list_id": pack_list_id,
                    "pack_list_name": str(item.get("packListName") or item.get("pack_list_name") or "").strip() or None,
                    "job_id": str(item.get("jobId") or item.get("job_id") or "").strip() or None,
                    "job_name": str(item.get("jobName") or item.get("job_name") or "").strip() or None,
                    "quantity": max(0, int(item.get("quantity") or 0)),
                    "out": max(0, int(item.get("out") or 0)),
                    "start_date": str(item.get("startDate") or item.get("start_date") or "").strip() or None,
                    "end_date": str(item.get("endDate") or item.get("end_date") or "").strip() or None,
                    "job_status": str(item.get("jobStatus") or item.get("job_status") or "").strip() or None,
                    "source": source_name,
                }
            )

    return output


def _apply_margin_price(rental_price: float, margin_percent: float) -> float:
    return round(rental_price * (1 + (margin_percent / 100.0)), 2)


def _merge_sync_metadata(current: dict[str, object], previous: dict[str, object] | None) -> dict[str, object]:
    if not isinstance(previous, dict):
        return current

    merged = dict(current)
    merged["last_sync_at"] = str(previous.get("last_sync_at") or "").strip() or None
    merged["last_sync_imported"] = max(0, int(previous.get("last_sync_imported") or 0))
    merged["last_sync_updated"] = max(0, int(previous.get("last_sync_updated") or 0))
    merged["last_sync_skipped"] = max(0, int(previous.get("last_sync_skipped") or 0))
    merged["last_sync_total"] = max(0, int(previous.get("last_sync_total") or 0))
    merged["sync_running"] = bool(previous.get("sync_running") or False)
    merged["sync_started_at"] = str(previous.get("sync_started_at") or "").strip() or None
    merged["sync_finished_at"] = str(previous.get("sync_finished_at") or "").strip() or None
    merged["sync_progress_current"] = max(0, int(previous.get("sync_progress_current") or 0))
    merged["sync_progress_total"] = max(0, int(previous.get("sync_progress_total") or 0))
    merged["sync_progress_percent"] = max(0, min(100, int(previous.get("sync_progress_percent") or 0)))
    merged["sync_message"] = str(previous.get("sync_message") or "").strip() or None
    return merged


def _record_eventory_sync_status(
    db: Session,
    instance_id: str,
    imported: int,
    updated: int,
    skipped: int,
    total: int,
) -> None:
    setting = _get_or_create_setting(db, INTEGRATIONS_KEY, DEFAULT_INTEGRATIONS)
    parsed = _parse_integrations(setting.value_json)
    instances = parsed.get("eventory_instances") if isinstance(parsed, dict) else []
    if not isinstance(instances, list):
        return

    target = str(instance_id or "").strip()
    changed = False
    for item in instances:
        if not isinstance(item, dict):
            continue
        if str(item.get("id") or "").strip() != target:
            continue
        item["last_sync_at"] = datetime.utcnow().isoformat() + "Z"
        item["last_sync_imported"] = max(0, int(imported or 0))
        item["last_sync_updated"] = max(0, int(updated or 0))
        item["last_sync_skipped"] = max(0, int(skipped or 0))
        item["last_sync_total"] = max(0, int(total or 0))
        changed = True
        break

    if changed:
        setting.value_json = json.dumps({"eventory_instances": instances})
        db.commit()


def _set_eventory_sync_runtime_status(
    db: Session,
    instance_id: str,
    updates: dict[str, object],
) -> None:
    setting = _get_or_create_setting(db, INTEGRATIONS_KEY, DEFAULT_INTEGRATIONS)
    parsed = _parse_integrations(setting.value_json)
    instances = parsed.get("eventory_instances") if isinstance(parsed, dict) else []
    if not isinstance(instances, list):
        return

    target = str(instance_id or "").strip()
    changed = False
    for item in instances:
        if not isinstance(item, dict):
            continue
        if str(item.get("id") or "").strip() != target:
            continue
        for key, value in updates.items():
            item[key] = value
        changed = True
        break

    if changed:
        setting.value_json = json.dumps({"eventory_instances": instances})
        db.commit()
