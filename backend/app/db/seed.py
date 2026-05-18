from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.db.models import Device, FinancialTransaction, Job, JobRequirement, Product, User, Zone
from app.db.session import SessionLocal


def seed_demo_data() -> None:
    with SessionLocal() as db:
        if db.scalar(select(User.id).limit(1)) is not None:
            return

        admin = User(
            email="admin@stockwire.test",
            password_hash="change-me",
            full_name="Stockwire Admin",
            is_active=True,
            is_admin=True,
        )
        speaker = Product(sku="SPK-100", name="Active Speaker 12\"", category="audio", daily_rate=Decimal("350.00"))
        light = Product(sku="LGT-200", name="LED Wash Bar", category="lighting", daily_rate=Decimal("225.00"))
        zone_main = Zone(code="A-01", name="Main Rack A-01", zone_type="rack")
        zone_stage = Zone(code="STAGE", name="Stage Prep", zone_type="stage")
        db.add_all([admin, speaker, light, zone_main, zone_stage])
        db.flush()

        db.add_all(
            [
                Device(product_id=speaker.id, asset_tag="SPK-100-01", serial_number="SN-SPK-01"),
                Device(product_id=light.id, asset_tag="LGT-200-01", serial_number="SN-LGT-01"),
            ]
        )

        job = Job(
            job_code="JOB-2026-001",
            customer_name="Tsunami Events Demo",
            status="confirmed",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=2),
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
