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
    ["Audio", "Soundcards"],
    ["Audio", "Interfaces"],
    ["Audio", "Headphones"],
    ["Audio", "Amplifiers"],
    ["Audio", "Cables", "XLR"],
    ["Audio", "Cables", "PowerCon"],
    ["Audio", "Cables", "Speakon"],
    ["Audio", "Cables", "Jack"],
    ["Audio", "Cables", "CAT5"],
    ["Lighting", "Fixtures"],
    ["Lighting", "LED Panels"],
    ["Lighting", "Follow Spots"],
    ["Lighting", "Strobes"],
    ["Lighting", "UV Lights"],
    ["Lighting", "Control"],
    ["Lighting", "Dimmers"],
    ["Lighting", "Cables", "DMX"],
    ["Lighting", "Power"],
    ["Lighting", "Gels"],
    ["Lighting", "Clamps"],
    ["Rigging", "Truss"],
    ["Rigging", "Motors"],
    ["Rigging", "Hardware"],
    ["Rigging", "Chain Hoists"],
    ["Rigging", "Safety Lines"],
    ["Rigging", "Shackles"],
    ["Rigging", "Slings"],
    ["Video", "Displays"],
    ["Video", "Projectors"],
    ["Video", "Cameras"],
    ["Video", "Switchers"],
    ["Video", "Recorders"],
    ["Video", "Cables", "HDMI"],
    ["Video", "Cables", "SDI"],
    ["Video", "Cables", "DisplayPort"],
    ["Video", "Converters"],
    ["Power", "Distribution"],
    ["Power", "Cables"],
    ["Power", "UPS"],
    ["Power", "Generators"],
    ["Power", "Adapters"],
    ["Staging", "Decks"],
    ["Staging", "Legs"],
    ["Staging", "Drapes"],
    ["Staging", "Backdrops"],
    ["Staging", "Flooring"],
    ["Staging", "Tables"],
    ["Accessories", "Cases"],
    ["Accessories", "Adapters"],
    ["Accessories", "Clamps"],
    ["Accessories", "Safety"],
    ["Accessories", "Labels"],
    ["Consumables", "Tape"],
    ["Consumables", "Batteries"],
    ["Consumables", "Cleaning"],
    ["Consumables", "Gaffer Tape"],
    ["Consumables", "Cable Ties"],
    ["Effects", "Smoke Machines"],
    ["Effects", "Haze Machines"],
    ["Effects", "Confetti"],
    ["Effects", "Pyro"],
    ["Effects", "Bubble Machines"],
    ["Effects", "Fans"],
    ["Effects", "Fluids"],
    ["Effects", "Smoke Fluid"],
    ["Effects", "Haze Fluid"],
    ["Lamps", "Lamp Bulbs"],
    ["Tools", "Wrenches"],
    ["Tools", "Screwdrivers"],
    ["Tools", "Pliers"],
    ["Tools", "Cutters"],
    ["Tools", "Soldering"],
    ["Tools", "Multimeters"],
    ["Tools", "Crimpers"],
    ["Networking", "Switches"],
    ["Networking", "Cables"],
    ["Networking", "Routers"],
    ["Networking", "Access Points"],
    ["Networking", "Patch Panels"],
    ["Networking", "Connectors"],
]

DEFAULT_BRAND_OPTIONS = [
    "Absen",
    "Allen & Heath",
    "American DJ",
    "Analog Way",
    "Ayrton",
    "Barco",
    "Behringer",
    "Blackmagic Design",
    "Bosch",
    "Brompton Tech",
    "Chauvet Pro",
    "Claypaky",
    "d&b audiotechnik",
    "DeWalt",
    "DiGiCo",
    "Doughty",
    "Elation Pro",
    "Electro-Voice",
    "ETC",
    "Festool",
    "Global Truss",
    "GLP (German Light)",
    "Hilti",
    "Husqvarna",
    "JBL Professional",
    "L-Acoustics",
    "Makita",
    "Manfrotto",
    "Martin (HARMAN)",
    "Meyer Sound",
    "Milwaukee",
    "Neutrik",
    "Panasonic",
    "Powersoft",
    "Prolyte",
    "QSC",
    "RCF",
    "Robe Lighting",
    "ROE Visual",
    "Ryobi",
    "Sennheiser",
    "Shure",
    "Soundcraft",
    "ssnake",
    "Unilumin",
    "Yamaha",
]

DEFAULT_MANUFACTURER_OPTIONS = [
    "Absen",
    "ADJ Products",
    "Allen & Heath Limited",
    "Analog Way",
    "Ayrton",
    "Barco",
    "Blackmagic Design",
    "Bosch",
    "Brompton Technology",
    "CHAUVET Professional",
    "Claypaky",
    "d&b audiotechnik",
    "DiGiCo",
    "Doughty Engineering",
    "Elation Professional",
    "ETC",
    "Festool",
    "Global Truss",
    "GLP German Light Products",
    "Harman International",
    "Hilti",
    "Husqvarna Group",
    "L-Acoustics",
    "Makita",
    "Martin Professional",
    "Meyer Sound Laboratories",
    "Music Tribe",
    "Neutrik AG",
    "Panasonic Connect",
    "Powersoft S.p.A.",
    "Prolyte Group",
    "QSC LLC",
    "RCF S.p.A.",
    "Robe Lighting",
    "ROE Visual",
    "Sennheiser electronic SE & Co. KG",
    "Shure Incorporated",
    "ssnake",
    "Stanley Black & Decker",
    "Techtronic Industries",
    "Unilumin",
    "Videndum",
    "Yamaha Corporation",
]

DEFAULT_BRAND_MANUFACTURER_MAP = {
    "Absen": "Absen",
    "Allen & Heath": "Allen & Heath Limited",
    "American DJ": "ADJ Products",
    "Analog Way": "Analog Way",
    "Ayrton": "Ayrton",
    "Barco": "Barco",
    "Behringer": "Music Tribe",
    "Blackmagic Design": "Blackmagic Design",
    "Bosch": "Bosch",
    "Brompton Tech": "Brompton Technology",
    "Chauvet Pro": "CHAUVET Professional",
    "Claypaky": "Claypaky",
    "d&b audiotechnik": "d&b audiotechnik",
    "DeWalt": "Stanley Black & Decker",
    "DiGiCo": "DiGiCo",
    "Doughty": "Doughty Engineering",
    "Elation Pro": "Elation Professional",
    "Electro-Voice": "Bosch",
    "ETC": "ETC",
    "Festool": "Festool",
    "Global Truss": "Global Truss",
    "GLP (German Light)": "GLP German Light Products",
    "Hilti": "Hilti",
    "Husqvarna": "Husqvarna Group",
    "JBL Professional": "Harman International",
    "L-Acoustics": "L-Acoustics",
    "Makita": "Makita",
    "Manfrotto": "Videndum",
    "Martin (HARMAN)": "Martin Professional",
    "Meyer Sound": "Meyer Sound Laboratories",
    "Milwaukee": "Techtronic Industries",
    "Neutrik": "Neutrik AG",
    "Panasonic": "Panasonic Connect",
    "Powersoft": "Powersoft S.p.A.",
    "Prolyte": "Prolyte Group",
    "QSC": "QSC LLC",
    "RCF": "RCF S.p.A.",
    "Robe Lighting": "Robe Lighting",
    "ROE Visual": "ROE Visual",
    "Ryobi": "Techtronic Industries",
    "Sennheiser": "Sennheiser electronic SE & Co. KG",
    "Shure": "Shure Incorporated",
    "Soundcraft": "Harman International",
    "ssnake": "ssnake",
    "Unilumin": "Unilumin",
    "Yamaha": "Yamaha Corporation",
}

DEFAULT_BRAND_LINKS = {
    "Absen": "https://www.absen.com/",
    "Allen & Heath": "https://www.allen-heath.com/",
    "American DJ": "https://www.adj.com/",
    "Analog Way": "https://www.analogway.com/",
    "Ayrton": "https://www.ayrton.eu/",
    "Barco": "https://www.barco.com/",
    "Behringer": "https://www.behringer.com/",
    "Blackmagic Design": "https://www.blackmagicdesign.com/",
    "Bosch": "https://www.bosch-professional.com/",
    "Brompton Tech": "https://www.bromptontech.com/",
    "Chauvet Pro": "https://www.chauvetprofessional.com/",
    "Claypaky": "https://www.claypaky.it/",
    "d&b audiotechnik": "https://www.dbaudio.com/",
    "DeWalt": "https://www.dewalt.com/",
    "DiGiCo": "https://digico.biz/",
    "Doughty": "https://www.doughty-engineering.co.uk/",
    "Elation Pro": "https://www.elationlighting.com/",
    "Electro-Voice": "https://www.electrovoice.com/",
    "ETC": "https://www.etcconnect.com/",
    "Festool": "https://www.festool.com/",
    "Global Truss": "https://www.globaltruss.com/",
    "GLP (German Light)": "https://www.glp.de/",
    "Hilti": "https://www.hilti.com/",
    "Husqvarna": "https://www.husqvarna.com/",
    "JBL Professional": "https://jblpro.com/",
    "L-Acoustics": "https://www.l-acoustics.com/",
    "Makita": "https://www.makita.com/",
    "Manfrotto": "https://www.manfrotto.com/",
    "Martin (HARMAN)": "https://www.martin.com/",
    "Meyer Sound": "https://meyersound.com/",
    "Milwaukee": "https://www.milwaukeetool.com/",
    "Neutrik": "https://www.neutrik.com/",
    "Panasonic": "https://pro-av.panasonic.net/",
    "Powersoft": "https://www.powersoft.com/",
    "Prolyte": "https://www.prolyte.com/",
    "QSC": "https://www.qsc.com/",
    "RCF": "https://www.rcf.it/",
    "Robe Lighting": "https://www.robe.cz/",
    "ROE Visual": "https://www.roevisual.com/",
    "Ryobi": "https://www.ryobitools.com/",
    "Sennheiser": "https://www.sennheiser.com/",
    "Shure": "https://www.shure.com/",
    "Soundcraft": "https://www.soundcraft.com/",
    "ssnake": "https://www.ssnake.se/",
    "Unilumin": "https://www.unilumin.com/",
    "Yamaha": "https://www.yamaha.com/",
}

DEFAULT_MANUFACTURER_LINKS = {
    "Absen": "https://www.absen.com/",
    "ADJ Products": "https://www.adj.com/",
    "Allen & Heath Limited": "https://www.allen-heath.com/",
    "Analog Way": "https://www.analogway.com/",
    "Ayrton": "https://www.ayrton.eu/",
    "Barco": "https://www.barco.com/",
    "Blackmagic Design": "https://www.blackmagicdesign.com/",
    "Bosch": "https://www.bosch.com/",
    "Brompton Technology": "https://www.bromptontech.com/",
    "CHAUVET Professional": "https://www.chauvetprofessional.com/",
    "Claypaky": "https://www.claypaky.it/",
    "d&b audiotechnik": "https://www.dbaudio.com/",
    "DiGiCo": "https://digico.biz/",
    "Doughty Engineering": "https://www.doughty-engineering.co.uk/",
    "Elation Professional": "https://www.elationlighting.com/",
    "ETC": "https://www.etcconnect.com/",
    "Festool": "https://www.festool.com/",
    "Global Truss": "https://www.globaltruss.com/",
    "GLP German Light Products": "https://www.glp.de/",
    "Harman International": "https://www.harman.com/",
    "Hilti": "https://www.hilti.group/",
    "Husqvarna Group": "https://www.husqvarnagroup.com/",
    "L-Acoustics": "https://www.l-acoustics.com/",
    "Makita": "https://www.makita.com/",
    "Martin Professional": "https://www.martin.com/",
    "Meyer Sound Laboratories": "https://meyersound.com/",
    "Music Tribe": "https://www.musictribe.com/",
    "Neutrik AG": "https://www.neutrik.com/",
    "Panasonic Connect": "https://pro-av.panasonic.net/",
    "Powersoft S.p.A.": "https://www.powersoft.com/",
    "Prolyte Group": "https://www.prolyte.com/",
    "QSC LLC": "https://www.qsc.com/",
    "RCF S.p.A.": "https://www.rcf.it/",
    "Robe Lighting": "https://www.robe.cz/",
    "ROE Visual": "https://www.roevisual.com/",
    "Sennheiser electronic SE & Co. KG": "https://www.sennheiser.com/",
    "Shure Incorporated": "https://www.shure.com/",
    "ssnake": "https://www.ssnake.se/",
    "Stanley Black & Decker": "https://www.stanleyblackanddecker.com/",
    "Techtronic Industries": "https://www.ttigroup.com/",
    "Unilumin": "https://www.unilumin.com/",
    "Videndum": "https://www.videndum.com/",
    "Yamaha Corporation": "https://www.yamaha.com/",
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
    create_jobs: bool = False
    rental_customer_id: str = ""
    auto_scan_out_on_receive: bool = False
    auto_scan_in_on_return: bool = False


class StockwireInstanceConfig(BaseModel):
    id: str
    name: str
    enabled: bool = False
    api_url: str | None = None
    api_key: str | None = Field(default=None, exclude=True)
    supplier_customer_id: int | None = None
    remote_customer_id: str | None = None


class ProductionPlannerConfig(BaseModel):
    enabled: bool = False
    api_key: str | None = None
    base_url: str = "https://api.productionplanner.io/v1"


class ProductionPlannerReadConfig(BaseModel):
    enabled: bool = False
    base_url: str = "https://api.productionplanner.io/v1"
    has_api_key: bool = False


class LlmConfig(BaseModel):
    base_url: str = "http://localhost:11434/v1"
    api_key: str = "ollama"
    model: str = "qwen2.5-coder"


class IntegrationsRead(BaseModel):
    eventory_instances: list[EventoryInstanceConfig] = Field(default_factory=list)
    productionplanner: ProductionPlannerReadConfig = Field(default_factory=ProductionPlannerReadConfig)
    llm: LlmConfig | None = None
    stockwire_instances: list[StockwireInstanceConfig] = Field(default_factory=list)


class IntegrationsUpdate(BaseModel):
    eventory_instances: list[EventoryInstanceConfig] = Field(default_factory=list)
    productionplanner: ProductionPlannerConfig | None = None
    llm: LlmConfig | None = None
    stockwire_instances: list[StockwireInstanceConfig] = Field(default_factory=list)


class StockwireCustomerRead(BaseModel):
    id: int
    name: str
    email: str | None = None
    phone: str | None = None
    city: str | None = None
    country: str | None = None


class StockwireCustomersRead(BaseModel):
    customers: list[StockwireCustomerRead] = Field(default_factory=list)
    count: int = 0


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


class SmtpSettingsRead(BaseModel):
    host: str = ""
    port: int = 587
    username: str = ""
    password: str = ""
    from_email: str = ""
    from_name: str = ""
    use_tls: bool = True
    resend_api_key: str = ""
    env_managed: bool = False


class SmtpSettingsUpdate(BaseModel):
    host: str = ""
    port: int = 587
    username: str = ""
    password: str = ""
    from_email: str = ""
    from_name: str = ""
    use_tls: bool = True
    resend_api_key: str = ""


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
