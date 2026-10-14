from functools import lru_cache

from fastapi import Depends, FastAPI, HTTPException, status

from app.classifier import (
    ClassificationUpstreamError,
    ClassifierConfigurationError,
    WebsiteClassifier,
)
from app.config import Settings, get_settings
from app.models import ClassificationResponse, ClassifyRequest, HealthResponse


app = FastAPI(
    title="Business Website Classifier",
    version="1.0.0",
    description=(
        "Classifies a business website into a predefined category using OpenAI "
        "hosted web search."
    ),
)


@lru_cache
def get_classifier() -> WebsiteClassifier:
    return WebsiteClassifier(get_settings())


@app.get("/health", response_model=HealthResponse)
async def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        openai_configured=bool(settings.openai_api_key.strip()),
    )


@app.post("/classify", response_model=ClassificationResponse)
async def classify_website(
    request: ClassifyRequest,
    classifier: WebsiteClassifier = Depends(get_classifier),
) -> ClassificationResponse:
    try:
        return await classifier.classify(str(request.url))
    except ClassifierConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except ClassificationUpstreamError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
