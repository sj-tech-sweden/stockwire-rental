from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.db.models import (
    Customer,
    Device,
    FinancialTransaction,
    InventoryCategory,
    Job,
    JobRequirement,
    Product,
    User,
    Venue,
    Zone,
)
from app.db.session import SessionLocal


def _ensure_category(db, name: str, parent_id: int | None = None) -> InventoryCategory:
    category = db.scalar(
        select(InventoryCategory)
        .where(InventoryCategory.name == name)
        .where(InventoryCategory.parent_id == parent_id)
    )
    if category is None:
        category = InventoryCategory(name=name, parent_id=parent_id)
        db.add(category)
        db.flush()
    return category


def seed_demo_data() -> None:
    with SessionLocal() as db:
        # Seed report templates independently (always runs)
        from app.domain.reports.seed import seed_report_templates
        seed_report_templates(db)

        if db.scalar(select(User.id).limit(1)) is not None:
            return

        admin = User(
            email="admin@stockwire.test",
            password_hash="change-me",
            full_name="Stockwire Admin",
            is_active=True,
            is_admin=True,
        )

        audio = _ensure_category(db, "Audio")
        audio_speakers = _ensure_category(db, "Speakers", parent_id=audio.id)
        lighting = _ensure_category(db, "Lighting")
        lighting_fixtures = _ensure_category(db, "Fixtures", parent_id=lighting.id)

        speaker = Product(
            sku="SPK-100",
            name='Active Speaker 12"',
            category="Speakers",
            category_id=audio_speakers.id,
            daily_rate=Decimal("350.00"),
        )
        light = Product(
            sku="LGT-200",
            name="LED Wash Bar",
            category="Fixtures",
            category_id=lighting_fixtures.id,
            daily_rate=Decimal("225.00"),
        )
        zone_main = Zone(code="A-01", name="Main Rack A-01", zone_type="rack")
        zone_stage = Zone(code="STAGE", name="Stage Prep", zone_type="stage")
        customer = Customer(name="Tsunami Events Demo", email="demo@tsunami-events.test", phone="+46 70 000 00 00")
        venue = Venue(name="Tsunami Hall", address="Main Street 1", city="Stockholm")
        db.add_all([admin, speaker, light, zone_main, zone_stage, customer, venue])
        db.flush()

        db.add_all(
            [
                Device(product_id=speaker.id, asset_tag="SPK-100-01", serial_number="SN-SPK-01"),
                Device(product_id=light.id, asset_tag="LGT-200-01", serial_number="SN-LGT-01"),
            ]
        )

        job = Job(
            job_code="JOB-2026-001",
            customer_id=customer.id,
            customer_name=customer.name,
            venue_id=venue.id,
            venue_name=venue.name,
            description="Demo event production",
            status="confirmed",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=2),
            notes="Seeded demo job",
        )
        db.add(job)
        db.flush()

        db.add(JobRequirement(job_id=job.id, product_id=speaker.id, quantity_required=2, quantity_picked=1))
        db.add(
            FinancialTransaction(
                job_id=job.id,
                transaction_type="payment",
                status="pending",
                amount=Decimal("1500.00"),
                currency="SEK",
                transaction_date=datetime.utcnow(),
                due_date=datetime.utcnow() + timedelta(days=14),
            )
        )
        db.commit()


if __name__ == "__main__":
    seed_demo_data()
    print("Seed data created")
