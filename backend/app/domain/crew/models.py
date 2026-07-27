from datetime import datetime, date

from sqlalchemy import Boolean, Column, DateTime, Date, ForeignKey, Integer, Numeric, String, Table, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CrewSkill(Base):
    __tablename__ = "crew_skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    member_links: Mapped[list["CrewMemberSkill"]] = relationship(
        back_populates="skill", cascade="all, delete-orphan"
    )
    job_links: Mapped[list["JobRequiredSkill"]] = relationship(
        back_populates="skill", cascade="all, delete-orphan"
    )


class CrewCertification(Base):
    __tablename__ = "crew_certifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    member_links: Mapped[list["CrewMemberCertification"]] = relationship(
        back_populates="certification", cascade="all, delete-orphan"
    )


class CrewRole(Base):
    __tablename__ = "crew_roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    crew_requirements: Mapped[list["JobCrewRequirement"]] = relationship(
        back_populates="crew_role"
    )
    preferred_members: Mapped[list["CrewMember"]] = relationship(
        secondary="crew_member_preferred_roles",
        back_populates="preferred_roles"
    )


class CrewMember(Base):
    __tablename__ = "crew_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), nullable=True, index=True)
    hourly_rate: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    daily_rate: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    user: Mapped["User | None"] = relationship()
    supplier: Mapped["Customer | None"] = relationship()
    skills: Mapped[list["CrewMemberSkill"]] = relationship(
        back_populates="crew_member", cascade="all, delete-orphan"
    )
    certifications: Mapped[list["CrewMemberCertification"]] = relationship(
        back_populates="crew_member", cascade="all, delete-orphan"
    )
    assignments: Mapped[list["JobCrewAssignment"]] = relationship(
        back_populates="crew_member"
    )
    preferred_roles: Mapped[list["CrewRole"]] = relationship(
        secondary="crew_member_preferred_roles",
        back_populates="preferred_members"
    )


crew_member_preferred_roles = Table(
    "crew_member_preferred_roles",
    Base.metadata,
    Column("crew_member_id", ForeignKey("crew_members.id", ondelete="CASCADE"), primary_key=True),
    Column("crew_role_id", ForeignKey("crew_roles.id", ondelete="CASCADE"), primary_key=True),
)


class CrewMemberSkill(Base):
    __tablename__ = "crew_member_skills"
    __table_args__ = (UniqueConstraint("crew_member_id", "skill_id", name="uq_crew_member_skill"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    crew_member_id: Mapped[int] = mapped_column(ForeignKey("crew_members.id", ondelete="CASCADE"), index=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("crew_skills.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    crew_member: Mapped[CrewMember] = relationship(back_populates="skills")
    skill: Mapped[CrewSkill] = relationship(back_populates="member_links")


class CrewMemberCertification(Base):
    __tablename__ = "crew_member_certifications"
    __table_args__ = (UniqueConstraint("crew_member_id", "certification_id", name="uq_crew_member_cert"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    crew_member_id: Mapped[int] = mapped_column(ForeignKey("crew_members.id", ondelete="CASCADE"), index=True)
    certification_id: Mapped[int] = mapped_column(ForeignKey("crew_certifications.id", ondelete="CASCADE"), index=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    crew_member: Mapped[CrewMember] = relationship(back_populates="certifications")
    certification: Mapped[CrewCertification] = relationship(back_populates="member_links")


class JobCrewRequirement(Base):
    __tablename__ = "job_crew_requirements"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    crew_role_id: Mapped[int | None] = mapped_column(ForeignKey("crew_roles.id"), nullable=True, index=True)
    custom_role_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    quantity_assigned: Mapped[int] = mapped_column(Integer, default=0)
    hourly_rate: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    job: Mapped["Job"] = relationship(back_populates="crew_requirements")
    crew_role: Mapped[CrewRole | None] = relationship(back_populates="crew_requirements")
    assignments: Mapped[list["JobCrewAssignment"]] = relationship(
        back_populates="job_crew_requirement", cascade="all, delete-orphan"
    )
    required_skills: Mapped[list["JobRequiredSkill"]] = relationship(
        back_populates="job_crew_requirement", cascade="all, delete-orphan"
    )


class JobRequiredSkill(Base):
    __tablename__ = "job_required_skills"
    __table_args__ = (UniqueConstraint("job_crew_requirement_id", "skill_id", name="uq_job_required_skill"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    job_crew_requirement_id: Mapped[int] = mapped_column(
        ForeignKey("job_crew_requirements.id", ondelete="CASCADE"), index=True
    )
    skill_id: Mapped[int] = mapped_column(ForeignKey("crew_skills.id", ondelete="CASCADE"), index=True)

    job_crew_requirement: Mapped[JobCrewRequirement] = relationship(back_populates="required_skills")
    skill: Mapped[CrewSkill] = relationship(back_populates="job_links")


class JobCrewAssignment(Base):
    __tablename__ = "job_crew_assignments"
    __table_args__ = (UniqueConstraint("job_crew_requirement_id", "crew_member_id", name="uq_job_crew_assignment"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    job_crew_requirement_id: Mapped[int] = mapped_column(
        ForeignKey("job_crew_requirements.id", ondelete="CASCADE"), index=True
    )
    crew_member_id: Mapped[int] = mapped_column(ForeignKey("crew_members.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="assigned", index=True)
    hourly_rate_override: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    job_crew_requirement: Mapped[JobCrewRequirement] = relationship(back_populates="assignments")
    crew_member: Mapped[CrewMember] = relationship(back_populates="assignments")
