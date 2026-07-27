from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class CrewRoleBase(BaseModel):
    name: str
    description: str | None = None
    is_default: bool = False
    sort_order: int = 0


class CrewRoleCreate(CrewRoleBase):
    pass


class CrewRoleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_default: bool | None = None
    sort_order: int | None = None


class CrewRoleRead(CrewRoleBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class CrewSkillBase(BaseModel):
    name: str
    category: str | None = None


class CrewSkillCreate(CrewSkillBase):
    pass


class CrewSkillRead(CrewSkillBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class CrewCertificationBase(BaseModel):
    name: str
    category: str | None = None


class CrewCertificationCreate(CrewCertificationBase):
    pass


class CrewCertificationRead(CrewCertificationBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class CrewMemberCertificationItem(BaseModel):
    certification_id: int
    expiry_date: date | None = None


class CrewMemberBase(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    user_id: int | None = None
    supplier_id: int | None = None
    hourly_rate: Decimal | None = None
    daily_rate: Decimal | None = None
    notes: str | None = None
    is_active: bool = True


class CrewMemberCreate(CrewMemberBase):
    skill_ids: list[int] = Field(default_factory=list)
    certification_items: list[CrewMemberCertificationItem] = Field(default_factory=list)
    preferred_role_ids: list[int] = Field(default_factory=list)


class CrewMemberUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    user_id: int | None = None
    supplier_id: int | None = None
    hourly_rate: Decimal | None = None
    daily_rate: Decimal | None = None
    notes: str | None = None
    is_active: bool | None = None
    skill_ids: list[int] | None = None
    certification_items: list[CrewMemberCertificationItem] | None = None
    preferred_role_ids: list[int] | None = None


class CrewMemberSkillRead(BaseModel):
    id: int
    crew_member_id: int
    skill: CrewSkillRead
    created_at: datetime

    model_config = {"from_attributes": True}


class CrewMemberCertificationRead(BaseModel):
    id: int
    crew_member_id: int
    certification: CrewCertificationRead
    expiry_date: date | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CrewMemberAssignmentRead(BaseModel):
    id: int
    job_id: int
    job_code: str | None = None
    crew_role_name: str | None = None
    status: str

    model_config = {"from_attributes": True}


class CrewMemberRead(CrewMemberBase):
    id: int
    created_at: datetime
    user_name: str | None = None
    supplier_name: str | None = None
    skills: list[CrewSkillRead] = Field(default_factory=list)
    certifications: list[CrewMemberCertificationRead] = Field(default_factory=list)
    preferred_roles: list[CrewRoleRead] = Field(default_factory=list)
    assignments: list[CrewMemberAssignmentRead] = Field(default_factory=list)


class JobCrewRequirementBase(BaseModel):
    job_id: int
    crew_role_id: int | None = None
    custom_role_name: str | None = None
    quantity: int = 1
    skill_ids: list[int] = Field(default_factory=list)
    hourly_rate: Decimal | None = None
    notes: str | None = None


class JobCrewRequirementCreate(JobCrewRequirementBase):
    pass


class JobCrewRequirementUpdate(BaseModel):
    crew_role_id: int | None = None
    custom_role_name: str | None = None
    quantity: int | None = None
    skill_ids: list[int] | None = None
    hourly_rate: Decimal | None = None
    notes: str | None = None


class JobCrewRequirementBulkItem(BaseModel):
    crew_role_id: int | None = None
    custom_role_name: str | None = None
    quantity: int = 1
    skill_ids: list[int] = Field(default_factory=list)
    hourly_rate: Decimal | None = None
    notes: str | None = None


class JobCrewRequirementBulkUpsert(BaseModel):
    items: list[JobCrewRequirementBulkItem]

    @model_validator(mode="after")
    def validate_items(self):
        if not self.items:
            raise ValueError("At least one crew requirement is required")
        return self


class JobCrewRequirementRead(BaseModel):
    id: int
    job_id: int
    crew_role_id: int | None = None
    custom_role_name: str | None = None
    quantity: int
    quantity_assigned: int
    skills: list[CrewSkillRead] = Field(default_factory=list)
    hourly_rate: Decimal | None = None
    notes: str | None = None
    created_at: datetime
    crew_role_name: str | None = None

    model_config = {"from_attributes": True}


class JobCrewAssignmentBase(BaseModel):
    job_crew_requirement_id: int
    crew_member_id: int
    status: str = "assigned"
    hourly_rate_override: Decimal | None = None
    notes: str | None = None


class JobCrewAssignmentCreate(JobCrewAssignmentBase):
    pass


class JobCrewAssignmentUpdate(BaseModel):
    status: str | None = None
    hourly_rate_override: Decimal | None = None
    notes: str | None = None


class JobCrewAssignmentRead(BaseModel):
    id: int
    job_crew_requirement_id: int
    crew_member_id: int
    status: str
    hourly_rate_override: Decimal | None = None
    notes: str | None = None
    created_at: datetime
    crew_member_name: str | None = None
    crew_role_name: str | None = None

    model_config = {"from_attributes": True}


class CrewSuggestion(BaseModel):
    crew_member_id: int
    name: str
    match_score: float
    matching_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    hourly_rate: Decimal | None = None
    source: str | None = None
