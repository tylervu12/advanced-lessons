from enum import Enum
from ipaddress import ip_address

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from app.categories import Category


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ClassifyRequest(StrictModel):
    url: HttpUrl

    @field_validator("url")
    @classmethod
    def require_public_web_url(cls, value: HttpUrl) -> HttpUrl:
        host = value.host or ""
        if value.username or value.password:
            raise ValueError("URLs containing credentials are not supported")
        if host.lower() == "localhost" or host.lower().endswith(".local"):
            raise ValueError("A public website URL is required")
        try:
            if not ip_address(host).is_global:
                raise ValueError("A public website URL is required")
        except ValueError as exc:
            if str(exc) == "A public website URL is required":
                raise
            # A normal domain name is not an IP address and is allowed.
        return value


class ResearchMethod(str, Enum):
    WEBSITE_ONLY = "website_only"
    WEBSITE_PLUS_SEARCH = "website_plus_search"
    SEARCH_ONLY = "search_only"
    INSUFFICIENT = "insufficient"


class Source(StrictModel):
    title: str
    url: str


class ModelClassification(StrictModel):
    business_name: str
    category: Category
    confidence: float
    reason: str
    research_method: ResearchMethod
    sources: list[Source]

    @field_validator("confidence")
    @classmethod
    def confidence_must_be_bounded(cls, value: float) -> float:
        if not 0 <= value <= 1:
            raise ValueError("confidence must be between 0 and 1")
        return value


class ClassificationResponse(ModelClassification):
    url: str


class HealthResponse(StrictModel):
    status: str = Field(examples=["ok"])
    openai_configured: bool
