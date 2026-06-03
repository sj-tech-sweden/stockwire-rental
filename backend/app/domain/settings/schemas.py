from typing import Literal

from pydantic import BaseModel, Field


DEFAULT_LOCATION_TYPES = [
    "rack",
    "shelf",
    "bin",
    "pallet",
    "stage",
    "truck",
    "warehouse",
    "workshop",
]

DEFAULT_CATEGORY_PREFILL_PATHS = [
    ["Audio", "Speakers"],
    ["Audio", "Microphones"],
    ["Audio", "Mixers"],
    ["Audio", "Playback"],
    ["Audio", "Wireless"],
    ["Audio", "Cables", "XLR"],
    ["Audio", "Cables", "PowerCon"],
    ["Audio", "Cables", "Speakon"],
    ["Lighting", "Fixtures"],
    ["Lighting", "Control"],
    ["Lighting", "Dimmers"],
    ["Lighting", "Cables", "DMX"],
    ["Lighting", "Power"],
    ["Rigging", "Truss"],
    ["Rigging", "Motors"],
    ["Rigging", "Hardware"],
    ["Video", "Displays"],
    ["Video", "Projectors"],
    ["Video", "Switchers"],
    ["Video", "Cables"],
    ["Power", "Distribution"],
    ["Power", "Cables"],
    ["Staging", "Decks"],
    ["Staging", "Legs"],
    ["Accessories", "Cases"],
    ["Accessories", "Adapters"],
    ["Accessories", "Clamps"],
    ["Accessories", "Safety"],
    ["Consumables", "Tape"],
    ["Consumables", "Batteries"],
    ["Networking", "Switches"],
    ["Networking", "Cables"],
]

DEFAULT_BRAND_OPTIONS = [
    "Bosch",
    "Makita",
    "Hilti",
    "Milwaukee",
    "DeWalt",
    "Festool",
    "Ryobi",
    "Husqvarna",
    "Shure",
    "Sennheiser",
    "Yamaha",
    "Allen & Heath",
    "JBL Professional",
    "d&b audiotechnik",
    "L-Acoustics",
    "Meyer Sound",
    "DiGiCo",
    "Prolyte",
    "Global Truss",
    "ROE Visual",
    "Absen",
    "Robe Lighting",
    "Claypaky",
    "Martin (HARMAN)",
    "ETC",
    "GLP (German Light)",
    "Ayrton",
    "Elation Pro",
    "Chauvet Pro",
    "American DJ",
    "Barco",
    "Panasonic",
    "Blackmagic Design",
    "Unilumin",
    "Brompton Tech",
    "Analog Way",
]

DEFAULT_MANUFACTURER_OPTIONS = [
    "Bosch",
    "Makita",
    "Hilti",
    "Techtronic Industries",
    "Stanley Black & Decker",
    "Festool",
    "Husqvarna Group",
    "Shure Incorporated",
    "Sennheiser electronic SE & Co. KG",
    "Yamaha Corporation",
    "Allen & Heath Limited",
    "Harman International",
    "d&b audiotechnik",
    "L-Acoustics",
    "Meyer Sound Laboratories",
    "DiGiCo",
    "Prolyte Group",
    "Global Truss",
    "ROE Visual",
    "Absen",
    "Robe Lighting",
    "Claypaky",
    "Martin Professional",
    "ETC",
    "GLP German Light Products",
    "Ayrton",
    "Elation Professional",
    "CHAUVET Professional",
    "ADJ Products",
    "Barco",
    "Panasonic Connect",
    "Blackmagic Design",
    "Unilumin",
    "Brompton Technology",
    "Analog Way",
]

DEFAULT_BRAND_MANUFACTURER_MAP = {
    "Bosch": "Bosch",
    "Makita": "Makita",
    "Hilti": "Hilti",
    "Milwaukee": "Techtronic Industries",
    "DeWalt": "Stanley Black & Decker",
    "Festool": "Festool",
    "Ryobi": "Techtronic Industries",
    "Husqvarna": "Husqvarna Group",
    "Shure": "Shure Incorporated",
    "Sennheiser": "Sennheiser electronic SE & Co. KG",
    "Yamaha": "Yamaha Corporation",
    "Allen & Heath": "Allen & Heath Limited",
    "JBL Professional": "Harman International",
    "d&b audiotechnik": "d&b audiotechnik",
    "L-Acoustics": "L-Acoustics",
    "Meyer Sound": "Meyer Sound Laboratories",
    "DiGiCo": "DiGiCo",
    "Prolyte": "Prolyte Group",
    "Global Truss": "Global Truss",
    "ROE Visual": "ROE Visual",
    "Absen": "Absen",
    "Robe Lighting": "Robe Lighting",
    "Claypaky": "Claypaky",
    "Martin (HARMAN)": "Martin Professional",
    "ETC": "ETC",
    "GLP (German Light)": "GLP German Light Products",
    "Ayrton": "Ayrton",
    "Elation Pro": "Elation Professional",
    "Chauvet Pro": "CHAUVET Professional",
    "American DJ": "ADJ Products",
    "Barco": "Barco",
    "Panasonic": "Panasonic Connect",
    "Blackmagic Design": "Blackmagic Design",
    "Unilumin": "Unilumin",
    "Brompton Tech": "Brompton Technology",
    "Analog Way": "Analog Way",
}

DEFAULT_BRAND_LINKS = {
    "Bosch": "https://www.bosch-professional.com/",
    "Makita": "https://www.makita.com/",
    "Hilti": "https://www.hilti.com/",
    "Milwaukee": "https://www.milwaukeetool.com/",
    "DeWalt": "https://www.dewalt.com/",
    "Festool": "https://www.festool.com/",
    "Ryobi": "https://www.ryobitools.com/",
    "Husqvarna": "https://www.husqvarna.com/",
    "Shure": "https://www.shure.com/",
    "Sennheiser": "https://www.sennheiser.com/",
    "Yamaha": "https://www.yamaha.com/",
    "Allen & Heath": "https://www.allen-heath.com/",
    "JBL Professional": "https://jblpro.com/",
    "d&b audiotechnik": "https://www.dbaudio.com/",
    "L-Acoustics": "https://www.l-acoustics.com/",
    "Meyer Sound": "https://meyersound.com/",
    "DiGiCo": "https://digico.biz/",
    "Prolyte": "https://www.prolyte.com/",
    "Global Truss": "https://www.globaltruss.com/",
    "ROE Visual": "https://www.roevisual.com/",
    "Absen": "https://www.absen.com/",
    "Robe Lighting": "https://www.robe.cz/",
    "Claypaky": "https://www.claypaky.it/",
    "Martin (HARMAN)": "https://www.martin.com/",
    "ETC": "https://www.etcconnect.com/",
    "GLP (German Light)": "https://www.glp.de/",
    "Ayrton": "https://www.ayrton.eu/",
    "Elation Pro": "https://www.elationlighting.com/",
    "Chauvet Pro": "https://www.chauvetprofessional.com/",
    "American DJ": "https://www.adj.com/",
    "Barco": "https://www.barco.com/",
    "Panasonic": "https://pro-av.panasonic.net/",
    "Blackmagic Design": "https://www.blackmagicdesign.com/",
    "Unilumin": "https://www.unilumin.com/",
    "Brompton Tech": "https://www.bromptontech.com/",
    "Analog Way": "https://www.analogway.com/",
}

DEFAULT_MANUFACTURER_LINKS = {
    "Bosch": "https://www.bosch.com/",
    "Makita": "https://www.makita.com/",
    "Hilti": "https://www.hilti.group/",
    "Techtronic Industries": "https://www.ttigroup.com/",
    "Stanley Black & Decker": "https://www.stanleyblackanddecker.com/",
    "Festool": "https://www.festool.com/",
    "Husqvarna Group": "https://www.husqvarnagroup.com/",
    "Shure Incorporated": "https://www.shure.com/",
    "Sennheiser electronic SE & Co. KG": "https://www.sennheiser.com/",
    "Yamaha Corporation": "https://www.yamaha.com/",
    "Allen & Heath Limited": "https://www.allen-heath.com/",
    "Harman International": "https://www.harman.com/",
    "d&b audiotechnik": "https://www.dbaudio.com/",
    "L-Acoustics": "https://www.l-acoustics.com/",
    "Meyer Sound Laboratories": "https://meyersound.com/",
    "DiGiCo": "https://digico.biz/",
    "Prolyte Group": "https://www.prolyte.com/",
    "Global Truss": "https://www.globaltruss.com/",
    "ROE Visual": "https://www.roevisual.com/",
    "Absen": "https://www.absen.com/",
    "Robe Lighting": "https://www.robe.cz/",
    "Claypaky": "https://www.claypaky.it/",
    "Martin Professional": "https://www.martin.com/",
    "ETC": "https://www.etcconnect.com/",
    "GLP German Light Products": "https://www.glp.de/",
    "Ayrton": "https://www.ayrton.eu/",
    "Elation Professional": "https://www.elationlighting.com/",
    "CHAUVET Professional": "https://www.chauvetprofessional.com/",
    "ADJ Products": "https://www.adj.com/",
    "Barco": "https://www.barco.com/",
    "Panasonic Connect": "https://pro-av.panasonic.net/",
    "Blackmagic Design": "https://www.blackmagicdesign.com/",
    "Unilumin": "https://www.unilumin.com/",
    "Brompton Technology": "https://www.bromptontech.com/",
    "Analog Way": "https://www.analogway.com/",
}


class LocationTypeOptionsRead(BaseModel):
    options: list[str] = Field(default_factory=list)


class LocationTypeOptionsUpdate(BaseModel):
    options: list[str] = Field(default_factory=list)


class CategoryPrefillPathsRead(BaseModel):
    paths: list[list[str]] = Field(default_factory=list)


class CategoryPrefillPathsUpdate(BaseModel):
    paths: list[list[str]] = Field(default_factory=list)


class ProductDefaultsRead(BaseModel):
    brand_options: list[str] = Field(default_factory=list)
    manufacturer_options: list[str] = Field(default_factory=list)
    default_brand: str | None = None
    default_manufacturer: str | None = None
    brand_manufacturer_map: dict[str, str] = Field(default_factory=dict)
    brand_links: dict[str, str] = Field(default_factory=dict)
    manufacturer_links: dict[str, str] = Field(default_factory=dict)


class ProductDefaultsUpdate(BaseModel):
    brand_options: list[str] = Field(default_factory=list)
    manufacturer_options: list[str] = Field(default_factory=list)
    default_brand: str | None = None
    default_manufacturer: str | None = None
    brand_manufacturer_map: dict[str, str] = Field(default_factory=dict)
    brand_links: dict[str, str] = Field(default_factory=dict)
    manufacturer_links: dict[str, str] = Field(default_factory=dict)


class IntegrationPluginConfig(BaseModel):
    enabled: bool = False
    api_url: str | None = None
    api_key: str | None = None
    username: str | None = None
    password: str | None = None
    token_endpoint: str | None = None
    supplier_name: str | None = None
    sync_interval_minutes: int = Field(default=0, ge=0)
    price_margin_percent: float = Field(default=0, ge=0)
    last_sync_at: str | None = None
    last_sync_imported: int = Field(default=0, ge=0)
    last_sync_updated: int = Field(default=0, ge=0)
    last_sync_skipped: int = Field(default=0, ge=0)
    last_sync_total: int = Field(default=0, ge=0)
    sync_running: bool = False
    sync_started_at: str | None = None
    sync_finished_at: str | None = None
    sync_progress_current: int = Field(default=0, ge=0)
    sync_progress_total: int = Field(default=0, ge=0)
    sync_progress_percent: int = Field(default=0, ge=0, le=100)
    sync_message: str | None = None


class EventoryInstanceConfig(IntegrationPluginConfig):
    id: str
    name: str


class IntegrationsRead(BaseModel):
    eventory_instances: list[EventoryInstanceConfig] = Field(default_factory=list)


class IntegrationsUpdate(BaseModel):
    eventory_instances: list[EventoryInstanceConfig] = Field(default_factory=list)


class IntegrationConnectionTestRequest(BaseModel):
    config: IntegrationPluginConfig | None = None


class IntegrationConnectionTestRead(BaseModel):
    ok: bool
    plugin: str
    message: str
    status_code: int | None = None


class EventoryProductRead(BaseModel):
    id: str
    name: str
    description: str | None = None
    category: str | None = None
    price: float = 0
    quantity_available: int = 0


class EventoryProductsRead(BaseModel):
    products: list[EventoryProductRead] = Field(default_factory=list)
    count: int = 0


class EventorySyncRead(BaseModel):
    imported: int
    updated: int
    skipped: int
    total: int
    message: str


class EventorySyncStartRead(BaseModel):
    started: bool
    message: str


class EventorySyncStatusRead(BaseModel):
    running: bool
    progress_current: int = 0
    progress_total: int = 0
    progress_percent: int = 0
    started_at: str | None = None
    finished_at: str | None = None
    imported: int = 0
    updated: int = 0
    skipped: int = 0
    total: int = 0
    message: str | None = None


class SSOProviderConfig(BaseModel):
    key: str
    display_name: str | None = None
    enabled: bool = True
    allow_auto_create: bool | None = None

    issuer: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    authorization_endpoint: str | None = None
    token_endpoint: str | None = None
    jwks_uri: str | None = None
    scopes: str | None = None
    group_claim: str | None = None
    email_claim: str | None = None
    name_claim: str | None = None
    subject_claim: str | None = None

    idp_entity_id: str | None = None
    idp_sso_url: str | None = None
    idp_x509_cert: str | None = None
    sp_entity_id: str | None = None
    acs_url: str | None = None
    group_attribute: str | None = None
    email_attribute: str | None = None
    name_attribute: str | None = None
    subject_attribute: str | None = None


class AuthSSOSettingsRead(BaseModel):
    enabled: bool = False
    auto_create_users: bool = True
    sync_roles_on_login: bool = True
    default_role: str = "viewer"
    group_role_map: dict[str, str] = Field(default_factory=dict)
    oidc_providers: list[SSOProviderConfig] = Field(default_factory=list)
    saml_providers: list[SSOProviderConfig] = Field(default_factory=list)


class AuthSSOSettingsUpdate(BaseModel):
    enabled: bool = False
    auto_create_users: bool = True
    sync_roles_on_login: bool = True
    default_role: str = "viewer"
    group_role_map: dict[str, str] = Field(default_factory=dict)
    oidc_providers: list[SSOProviderConfig] = Field(default_factory=list)
    saml_providers: list[SSOProviderConfig] = Field(default_factory=list)


class LabelTemplateCanvas(BaseModel):
    width: float = Field(default=420, gt=0)
    height: float = Field(default=280, gt=0)


class LabelTemplateElement(BaseModel):
    id: str
    kind: Literal["field", "text", "barcode", "qrcode", "logo"] = "field"
    source: str | None = None
    text: str | None = None
    x: float = 0
    y: float = 0
    w: float = 120
    h: float = 30
    fontSize: float = 12


class LabelTemplateUpsert(BaseModel):
    name: str
    entity_type: Literal["device", "product", "location", "case"]
    print_preset: Literal["62x29", "50x25", "a4-3x8"] = "62x29"
    visibility: Literal["all", "admin", "owner"] = "all"
    edit_roles: list[Literal["admin", "manager", "viewer"]] = Field(default_factory=lambda: ["admin", "manager"])
    canvas: LabelTemplateCanvas = Field(default_factory=LabelTemplateCanvas)
    elements: list[LabelTemplateElement] = Field(default_factory=list)


class LabelTemplateRead(LabelTemplateUpsert):
    id: str
    created_by_user_id: int | None = None
    created_by_name: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class AppVersionRead(BaseModel):
    version: str
    backend_version: str | None = None
    image_tag: str | None = None
    postgres_version: str | None = None
    valkey_version: str | None = None
    latest_version: str | None = None
    latest_release_notes: str | None = None
    latest_release_url: str | None = None
    up_to_date: bool | None = None
