from app.domain.audit.models import ActivityLog
from app.domain.auth.models import PushSubscription, User
from app.domain.calendar_feeds.models import CalendarFeed
from app.domain.custom_fields.models import CustomFieldDefinition, CustomFieldValue
from app.domain.customers.models import Company, Customer, Person
from app.domain.crew.models import (
    CrewCertification,
    CrewMember,
    CrewMemberCertification,
    CrewMemberSkill,
    CrewRole,
    CrewSkill,
    EquipmentRequiredCertification,
    JobCrewAssignment,
    JobCrewRequirement,
    JobRequiredSkill,
    JobRoleRequiredCertification,
)
from app.domain.reports.models import Letterhead, ReportTemplate, GeneratedReportLog
from app.domain.finance.models import FinancialTransaction
from app.domain.integrations.models import TwentyConfig, TwentySyncLog
from app.domain.route_planner.models import DeliveryRoute, RouteStop, RouteVehicle, Vehicle
from app.domain.warehouse_leds.models import LEDBinMapping, LEDController, LEDControllerZone
from app.domain.inventory.models import (
    DefectComment,
    DefectReport,
    Device,
    DeviceMaintenance,
    DeviceMaintenanceSchedule,
    InventoryAuditLog,
    InventoryCategory,
    MaintenanceComment,
    Product,
    ProductAccessory,
    ProductComponent,
    ProductSupplier,
    Zone,
)
from app.domain.jobs.models import Job, JobRequirement
from app.domain.notifications.models import NotificationLog, NotificationPreference, NotificationTemplate, UserNotificationPreference
from app.domain.settings.models import AppSetting
from app.domain.storage.models import AssetFile
from app.domain.venues.models import Venue

__all__ = [
    "User",
    "PushSubscription",
    "ActivityLog",
    "InventoryCategory",
    "Product",
    "ProductAccessory",
    "ProductComponent",
    "ProductSupplier",
    "Device",
    "DeviceMaintenance",
    "DeviceMaintenanceSchedule",
    "MaintenanceComment",
    "DefectReport",
    "DefectComment",
    "InventoryAuditLog",
    "Zone",
    "Company",
    "Person",
    "Customer",
    "Venue",
    "CustomFieldDefinition",
    "CustomFieldValue",
    "Job",
    "JobRequirement",
    "NotificationTemplate",
    "NotificationPreference",
    "UserNotificationPreference",
    "NotificationLog",
    "FinancialTransaction",
    "AppSetting",
    "AssetFile",
    "TwentyConfig",
    "TwentySyncLog",
    "Vehicle",
    "DeliveryRoute",
    "RouteStop",
    "RouteVehicle",
    "LEDController",
    "LEDControllerZone",
    "LEDBinMapping",
    "CrewRole",
    "CrewSkill",
    "CrewCertification",
    "CrewMember",
    "CrewMemberSkill",
    "CrewMemberCertification",
    "JobCrewRequirement",
    "JobRequiredSkill",
    "JobCrewAssignment",
    "EquipmentRequiredCertification",
    "JobRoleRequiredCertification",
    "Letterhead",
    "ReportTemplate",
    "GeneratedReportLog",
    "CalendarFeed",
]
