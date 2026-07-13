from datetime import datetime
from typing import Annotated, Generic, Literal, TypeVar

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.models import AssetCategory, AssetStatus, Department, Region


def require_timezone(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include a UTC offset")
    return value


AwareDatetime = Annotated[datetime, AfterValidator(require_timezone)]


class UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    department: Department


class AssetSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tag: str
    category: AssetCategory
    model: str
    status: AssetStatus
    region: Region


class AssetRead(AssetSummary):
    last_synced_at: AwareDatetime
    current_holder: UserSummary | None


class UserRead(UserSummary):
    pass


class CheckoutRead(BaseModel):
    id: int
    asset: AssetSummary
    user: UserSummary
    checked_out_at: AwareDatetime
    checked_in_at: AwareDatetime | None


class HealthRead(BaseModel):
    status: Literal["ok", "degraded"]
    database: Literal["ok", "unavailable"]


class ApiError(BaseModel):
    code: str
    message: str


class ResponseMeta(BaseModel):
    count: int = Field(ge=0)
    limit: int | None = Field(default=None, ge=1, le=100)


PayloadT = TypeVar("PayloadT")


class ApiResponse(BaseModel, Generic[PayloadT]):
    data: PayloadT | None
    error: ApiError | None
    meta: ResponseMeta


def success(
    data: PayloadT,
    *,
    count: int,
    limit: int | None = None,
) -> ApiResponse[PayloadT]:
    return ApiResponse[PayloadT](
        data=data,
        error=None,
        meta=ResponseMeta(count=count, limit=limit),
    )
