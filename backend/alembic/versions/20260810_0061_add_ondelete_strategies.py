"""add ondelete strategies to foreign keys

Revision ID: 0061
Revises: 0060
Create Date: 2026-08-10
"""

from alembic import op
import sqlalchemy as sa

revision = "0061"
down_revision = "20260804_0060"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- auth ---
    op.alter_column("user_roles", "user_id", existing_type=sa.Integer(), nullable=False)
    op.drop_constraint("user_roles_user_id_fkey", "user_roles", type_="foreignkey")
    op.create_foreign_key("user_roles_user_id_fkey", "user_roles", "users", ["user_id"], ["id"], ondelete="CASCADE")

    op.drop_constraint("user_roles_role_id_fkey", "user_roles", type_="foreignkey")
    op.create_foreign_key("user_roles_role_id_fkey", "user_roles", "roles", ["role_id"], ["id"], ondelete="CASCADE")

    op.drop_constraint("sessions_user_id_fkey", "sessions", type_="foreignkey")
    op.create_foreign_key("sessions_user_id_fkey", "sessions", "users", ["user_id"], ["id"], ondelete="CASCADE")

    op.drop_constraint("push_subscriptions_user_id_fkey", "push_subscriptions", type_="foreignkey")
    op.create_foreign_key("push_subscriptions_user_id_fkey", "push_subscriptions", "users", ["user_id"], ["id"], ondelete="CASCADE")

    # --- inventory ---
    op.drop_constraint("inventory_categories_parent_id_fkey", "inventory_categories", type_="foreignkey")
    op.create_foreign_key("inventory_categories_parent_id_fkey", "inventory_categories", "inventory_categories", ["parent_id"], ["id"], ondelete="SET NULL")

    op.drop_constraint("products_category_id_fkey", "products", type_="foreignkey")
    op.create_foreign_key("products_category_id_fkey", "products", "inventory_categories", ["category_id"], ["id"], ondelete="SET NULL")

    op.drop_constraint("devices_product_id_fkey", "devices", type_="foreignkey")
    op.create_foreign_key("devices_product_id_fkey", "devices", "products", ["product_id"], ["id"], ondelete="CASCADE")

    op.drop_constraint("devices_location_zone_id_fkey", "devices", type_="foreignkey")
    op.create_foreign_key("devices_location_zone_id_fkey", "devices", "zones", ["location_zone_id"], ["id"], ondelete="SET NULL")

    op.drop_constraint("devices_case_device_id_fkey", "devices", type_="foreignkey")
    op.create_foreign_key("devices_case_device_id_fkey", "devices", "devices", ["case_device_id"], ["id"], ondelete="SET NULL")

    op.drop_constraint("devices_parent_component_device_id_fkey", "devices", type_="foreignkey")
    op.create_foreign_key("devices_parent_component_device_id_fkey", "devices", "devices", ["parent_component_device_id"], ["id"], ondelete="SET NULL")

    op.drop_constraint("device_maintenance_device_id_fkey", "device_maintenance", type_="foreignkey")
    op.create_foreign_key("device_maintenance_device_id_fkey", "device_maintenance", "devices", ["device_id"], ["id"], ondelete="CASCADE")

    op.drop_constraint("maintenance_comments_created_by_user_id_fkey", "maintenance_comments", type_="foreignkey")
    op.create_foreign_key("maintenance_comments_created_by_user_id_fkey", "maintenance_comments", "users", ["created_by_user_id"], ["id"], ondelete="SET NULL")

    op.drop_constraint("defect_reports_created_by_user_id_fkey", "defect_reports", type_="foreignkey")
    op.create_foreign_key("defect_reports_created_by_user_id_fkey", "defect_reports", "users", ["created_by_user_id"], ["id"], ondelete="SET NULL")

    op.drop_constraint("defect_comments_created_by_user_id_fkey", "defect_comments", type_="foreignkey")
    op.create_foreign_key("defect_comments_created_by_user_id_fkey", "defect_comments", "users", ["created_by_user_id"], ["id"], ondelete="SET NULL")

    op.drop_constraint("zones_parent_id_fkey", "zones", type_="foreignkey")
    op.create_foreign_key("zones_parent_id_fkey", "zones", "zones", ["parent_id"], ["id"], ondelete="SET NULL")

    op.drop_constraint("inventory_audit_logs_user_id_fkey", "inventory_audit_logs", type_="foreignkey")
    op.create_foreign_key("inventory_audit_logs_user_id_fkey", "inventory_audit_logs", "users", ["user_id"], ["id"], ondelete="SET NULL")

    op.drop_constraint("inventory_audit_logs_device_id_fkey", "inventory_audit_logs", type_="foreignkey")
    op.create_foreign_key("inventory_audit_logs_device_id_fkey", "inventory_audit_logs", "devices", ["device_id"], ["id"], ondelete="SET NULL")

    op.drop_constraint("inventory_audit_logs_product_id_fkey", "inventory_audit_logs", type_="foreignkey")
    op.create_foreign_key("inventory_audit_logs_product_id_fkey", "inventory_audit_logs", "products", ["product_id"], ["id"], ondelete="SET NULL")

    op.drop_constraint("inventory_audit_logs_zone_id_fkey", "inventory_audit_logs", type_="foreignkey")
    op.create_foreign_key("inventory_audit_logs_zone_id_fkey", "inventory_audit_logs", "zones", ["zone_id"], ["id"], ondelete="SET NULL")

    op.drop_constraint("inventory_audit_logs_job_id_fkey", "inventory_audit_logs", type_="foreignkey")
    op.create_foreign_key("inventory_audit_logs_job_id_fkey", "inventory_audit_logs", "jobs", ["job_id"], ["id"], ondelete="SET NULL")

    # --- jobs ---
    op.drop_constraint("jobs_project_id_fkey", "jobs", type_="foreignkey")
    op.create_foreign_key("jobs_project_id_fkey", "jobs", "projects", ["project_id"], ["id"], ondelete="SET NULL")

    op.drop_constraint("jobs_customer_id_fkey", "jobs", type_="foreignkey")
    op.create_foreign_key("jobs_customer_id_fkey", "jobs", "customers", ["customer_id"], ["id"], ondelete="SET NULL")

    op.drop_constraint("jobs_venue_id_fkey", "jobs", type_="foreignkey")
    op.create_foreign_key("jobs_venue_id_fkey", "jobs", "venues", ["venue_id"], ["id"], ondelete="SET NULL")

    op.drop_constraint("jobs_owner_id_fkey", "jobs", type_="foreignkey")
    op.create_foreign_key("jobs_owner_id_fkey", "jobs", "users", ["owner_id"], ["id"], ondelete="SET NULL")

    op.drop_constraint("job_requirements_job_id_fkey", "job_requirements", type_="foreignkey")
    op.create_foreign_key("job_requirements_job_id_fkey", "job_requirements", "jobs", ["job_id"], ["id"], ondelete="CASCADE")

    op.drop_constraint("job_requirements_product_id_fkey", "job_requirements", type_="foreignkey")
    op.create_foreign_key("job_requirements_product_id_fkey", "job_requirements", "products", ["product_id"], ["id"], ondelete="CASCADE")

    # --- projects ---
    op.drop_constraint("projects_customer_id_fkey", "projects", type_="foreignkey")
    op.create_foreign_key("projects_customer_id_fkey", "projects", "customers", ["customer_id"], ["id"], ondelete="SET NULL")

    op.drop_constraint("projects_venue_id_fkey", "projects", type_="foreignkey")
    op.create_foreign_key("projects_venue_id_fkey", "projects", "venues", ["venue_id"], ["id"], ondelete="SET NULL")

    # --- finance ---
    op.drop_constraint("financial_transactions_job_id_fkey", "financial_transactions", type_="foreignkey")
    op.create_foreign_key("financial_transactions_job_id_fkey", "financial_transactions", "jobs", ["job_id"], ["id"], ondelete="SET NULL")

    # --- crew ---
    op.drop_constraint("crew_members_user_id_fkey", "crew_members", type_="foreignkey")
    op.create_foreign_key("crew_members_user_id_fkey", "crew_members", "users", ["user_id"], ["id"], ondelete="SET NULL")

    op.drop_constraint("crew_members_supplier_id_fkey", "crew_members", type_="foreignkey")
    op.create_foreign_key("crew_members_supplier_id_fkey", "crew_members", "customers", ["supplier_id"], ["id"], ondelete="SET NULL")

    op.drop_constraint("job_crew_requirements_crew_role_id_fkey", "job_crew_requirements", type_="foreignkey")
    op.create_foreign_key("job_crew_requirements_crew_role_id_fkey", "job_crew_requirements", "crew_roles", ["crew_role_id"], ["id"], ondelete="SET NULL")

    op.drop_constraint("job_crew_assignments_crew_member_id_fkey", "job_crew_assignments", type_="foreignkey")
    op.create_foreign_key("job_crew_assignments_crew_member_id_fkey", "job_crew_assignments", "crew_members", ["crew_member_id"], ["id"], ondelete="CASCADE")

    # --- route_planner ---
    op.drop_constraint("delivery_routes_created_by_id_fkey", "delivery_routes", type_="foreignkey")
    op.create_foreign_key("delivery_routes_created_by_id_fkey", "delivery_routes", "users", ["created_by_id"], ["id"], ondelete="SET NULL")

    op.drop_constraint("route_vehicles_vehicle_id_fkey", "route_vehicles", type_="foreignkey")
    op.create_foreign_key("route_vehicles_vehicle_id_fkey", "route_vehicles", "vehicles", ["vehicle_id"], ["id"], ondelete="CASCADE")

    op.drop_constraint("route_stops_job_id_fkey", "route_stops", type_="foreignkey")
    op.alter_column("route_stops", "job_id", existing_type=sa.Integer(), nullable=True)
    op.create_foreign_key("route_stops_job_id_fkey", "route_stops", "jobs", ["job_id"], ["id"], ondelete="SET NULL")

    op.drop_constraint("route_stops_vehicle_id_fkey", "route_stops", type_="foreignkey")
    op.create_foreign_key("route_stops_vehicle_id_fkey", "route_stops", "vehicles", ["vehicle_id"], ["id"], ondelete="SET NULL")

    # --- calendar_feeds ---
    op.drop_constraint("calendar_feeds_crew_member_id_fkey", "calendar_feeds", type_="foreignkey")
    op.create_foreign_key("calendar_feeds_crew_member_id_fkey", "calendar_feeds", "crew_members", ["crew_member_id"], ["id"], ondelete="SET NULL")

    # --- notifications ---
    op.drop_constraint("notification_logs_job_id_fkey", "notification_logs", type_="foreignkey")
    op.create_foreign_key("notification_logs_job_id_fkey", "notification_logs", "jobs", ["job_id"], ["id"], ondelete="SET NULL")

    # --- storage ---
    op.drop_constraint("asset_files_created_by_user_id_fkey", "asset_files", type_="foreignkey")
    op.create_foreign_key("asset_files_created_by_user_id_fkey", "asset_files", "users", ["created_by_user_id"], ["id"], ondelete="SET NULL")

    # --- audit ---
    op.drop_constraint("activity_logs_user_id_fkey", "activity_logs", type_="foreignkey")
    op.create_foreign_key("activity_logs_user_id_fkey", "activity_logs", "users", ["user_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    # Revert all ondelete changes back to no ondelete
    # --- audit ---
    op.drop_constraint("activity_logs_user_id_fkey", "activity_logs", type_="foreignkey")
    op.create_foreign_key("activity_logs_user_id_fkey", "activity_logs", "users", ["user_id"], ["id"])

    # --- storage ---
    op.drop_constraint("asset_files_created_by_user_id_fkey", "asset_files", type_="foreignkey")
    op.create_foreign_key("asset_files_created_by_user_id_fkey", "asset_files", "users", ["created_by_user_id"], ["id"])

    # --- notifications ---
    op.drop_constraint("notification_logs_job_id_fkey", "notification_logs", type_="foreignkey")
    op.create_foreign_key("notification_logs_job_id_fkey", "notification_logs", "jobs", ["job_id"], ["id"])

    # --- calendar_feeds ---
    op.drop_constraint("calendar_feeds_crew_member_id_fkey", "calendar_feeds", type_="foreignkey")
    op.create_foreign_key("calendar_feeds_crew_member_id_fkey", "calendar_feeds", "crew_members", ["crew_member_id"], ["id"])

    # --- route_planner ---
    op.drop_constraint("route_stops_vehicle_id_fkey", "route_stops", type_="foreignkey")
    op.create_foreign_key("route_stops_vehicle_id_fkey", "route_stops", "vehicles", ["vehicle_id"], ["id"])

    op.drop_constraint("route_stops_job_id_fkey", "route_stops", type_="foreignkey")
    op.alter_column("route_stops", "job_id", existing_type=sa.Integer(), nullable=False)
    op.create_foreign_key("route_stops_job_id_fkey", "route_stops", "jobs", ["job_id"], ["id"])

    op.drop_constraint("route_vehicles_vehicle_id_fkey", "route_vehicles", type_="foreignkey")
    op.create_foreign_key("route_vehicles_vehicle_id_fkey", "route_vehicles", "vehicles", ["vehicle_id"], ["id"])

    op.drop_constraint("delivery_routes_created_by_id_fkey", "delivery_routes", type_="foreignkey")
    op.create_foreign_key("delivery_routes_created_by_id_fkey", "delivery_routes", "users", ["created_by_id"], ["id"])

    # --- crew ---
    op.drop_constraint("job_crew_assignments_crew_member_id_fkey", "job_crew_assignments", type_="foreignkey")
    op.create_foreign_key("job_crew_assignments_crew_member_id_fkey", "job_crew_assignments", "crew_members", ["crew_member_id"], ["id"])

    op.drop_constraint("job_crew_requirements_crew_role_id_fkey", "job_crew_requirements", type_="foreignkey")
    op.create_foreign_key("job_crew_requirements_crew_role_id_fkey", "job_crew_requirements", "crew_roles", ["crew_role_id"], ["id"])

    op.drop_constraint("crew_members_supplier_id_fkey", "crew_members", type_="foreignkey")
    op.create_foreign_key("crew_members_supplier_id_fkey", "crew_members", "customers", ["supplier_id"], ["id"])

    op.drop_constraint("crew_members_user_id_fkey", "crew_members", type_="foreignkey")
    op.create_foreign_key("crew_members_user_id_fkey", "crew_members", "users", ["user_id"], ["id"])

    # --- finance ---
    op.drop_constraint("financial_transactions_job_id_fkey", "financial_transactions", type_="foreignkey")
    op.create_foreign_key("financial_transactions_job_id_fkey", "financial_transactions", "jobs", ["job_id"], ["id"])

    # --- projects ---
    op.drop_constraint("projects_venue_id_fkey", "projects", type_="foreignkey")
    op.create_foreign_key("projects_venue_id_fkey", "projects", "venues", ["venue_id"], ["id"])

    op.drop_constraint("projects_customer_id_fkey", "projects", type_="foreignkey")
    op.create_foreign_key("projects_customer_id_fkey", "projects", "customers", ["customer_id"], ["id"])

    # --- jobs ---
    op.drop_constraint("job_requirements_product_id_fkey", "job_requirements", type_="foreignkey")
    op.create_foreign_key("job_requirements_product_id_fkey", "job_requirements", "products", ["product_id"], ["id"])

    op.drop_constraint("job_requirements_job_id_fkey", "job_requirements", type_="foreignkey")
    op.create_foreign_key("job_requirements_job_id_fkey", "job_requirements", "jobs", ["job_id"], ["id"])

    op.drop_constraint("jobs_owner_id_fkey", "jobs", type_="foreignkey")
    op.create_foreign_key("jobs_owner_id_fkey", "jobs", "users", ["owner_id"], ["id"])

    op.drop_constraint("jobs_venue_id_fkey", "jobs", type_="foreignkey")
    op.create_foreign_key("jobs_venue_id_fkey", "jobs", "venues", ["venue_id"], ["id"])

    op.drop_constraint("jobs_customer_id_fkey", "jobs", type_="foreignkey")
    op.create_foreign_key("jobs_customer_id_fkey", "jobs", "customers", ["customer_id"], ["id"])

    op.drop_constraint("jobs_project_id_fkey", "jobs", type_="foreignkey")
    op.create_foreign_key("jobs_project_id_fkey", "jobs", "projects", ["project_id"], ["id"])

    # --- inventory ---
    op.drop_constraint("inventory_audit_logs_job_id_fkey", "inventory_audit_logs", type_="foreignkey")
    op.create_foreign_key("inventory_audit_logs_job_id_fkey", "inventory_audit_logs", "jobs", ["job_id"], ["id"])

    op.drop_constraint("inventory_audit_logs_zone_id_fkey", "inventory_audit_logs", type_="foreignkey")
    op.create_foreign_key("inventory_audit_logs_zone_id_fkey", "inventory_audit_logs", "zones", ["zone_id"], ["id"])

    op.drop_constraint("inventory_audit_logs_product_id_fkey", "inventory_audit_logs", type_="foreignkey")
    op.create_foreign_key("inventory_audit_logs_product_id_fkey", "inventory_audit_logs", "products", ["product_id"], ["id"])

    op.drop_constraint("inventory_audit_logs_device_id_fkey", "inventory_audit_logs", type_="foreignkey")
    op.create_foreign_key("inventory_audit_logs_device_id_fkey", "inventory_audit_logs", "devices", ["device_id"], ["id"])

    op.drop_constraint("inventory_audit_logs_user_id_fkey", "inventory_audit_logs", type_="foreignkey")
    op.create_foreign_key("inventory_audit_logs_user_id_fkey", "inventory_audit_logs", "users", ["user_id"], ["id"])

    op.drop_constraint("zones_parent_id_fkey", "zones", type_="foreignkey")
    op.create_foreign_key("zones_parent_id_fkey", "zones", "zones", ["parent_id"], ["id"])

    op.drop_constraint("defect_comments_created_by_user_id_fkey", "defect_comments", type_="foreignkey")
    op.create_foreign_key("defect_comments_created_by_user_id_fkey", "defect_comments", "users", ["created_by_user_id"], ["id"])

    op.drop_constraint("defect_reports_created_by_user_id_fkey", "defect_reports", type_="foreignkey")
    op.create_foreign_key("defect_reports_created_by_user_id_fkey", "defect_reports", "users", ["created_by_user_id"], ["id"])

    op.drop_constraint("maintenance_comments_created_by_user_id_fkey", "maintenance_comments", type_="foreignkey")
    op.create_foreign_key("maintenance_comments_created_by_user_id_fkey", "maintenance_comments", "users", ["created_by_user_id"], ["id"])

    op.drop_constraint("device_maintenance_device_id_fkey", "device_maintenance", type_="foreignkey")
    op.create_foreign_key("device_maintenance_device_id_fkey", "device_maintenance", "devices", ["device_id"], ["id"])

    op.drop_constraint("devices_parent_component_device_id_fkey", "devices", type_="foreignkey")
    op.create_foreign_key("devices_parent_component_device_id_fkey", "devices", "devices", ["parent_component_device_id"], ["id"])

    op.drop_constraint("devices_case_device_id_fkey", "devices", type_="foreignkey")
    op.create_foreign_key("devices_case_device_id_fkey", "devices", "devices", ["case_device_id"], ["id"])

    op.drop_constraint("devices_location_zone_id_fkey", "devices", type_="foreignkey")
    op.create_foreign_key("devices_location_zone_id_fkey", "devices", "zones", ["location_zone_id"], ["id"])

    op.drop_constraint("devices_product_id_fkey", "devices", type_="foreignkey")
    op.create_foreign_key("devices_product_id_fkey", "devices", "products", ["product_id"], ["id"])

    op.drop_constraint("products_category_id_fkey", "products", type_="foreignkey")
    op.create_foreign_key("products_category_id_fkey", "products", "inventory_categories", ["category_id"], ["id"])

    op.drop_constraint("inventory_categories_parent_id_fkey", "inventory_categories", type_="foreignkey")
    op.create_foreign_key("inventory_categories_parent_id_fkey", "inventory_categories", "inventory_categories", ["parent_id"], ["id"])

    # --- auth ---
    op.drop_constraint("push_subscriptions_user_id_fkey", "push_subscriptions", type_="foreignkey")
    op.create_foreign_key("push_subscriptions_user_id_fkey", "push_subscriptions", "users", ["user_id"], ["id"])

    op.drop_constraint("sessions_user_id_fkey", "sessions", type_="foreignkey")
    op.create_foreign_key("sessions_user_id_fkey", "sessions", "users", ["user_id"], ["id"])

    op.drop_constraint("user_roles_role_id_fkey", "user_roles", type_="foreignkey")
    op.create_foreign_key("user_roles_role_id_fkey", "user_roles", "roles", ["role_id"], ["id"])

    op.drop_constraint("user_roles_user_id_fkey", "user_roles", type_="foreignkey")
    op.create_foreign_key("user_roles_user_id_fkey", "user_roles", "users", ["user_id"], ["id"])
