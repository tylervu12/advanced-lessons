from fastapi.testclient import TestClient

from app.categories import Category
from app.main import app, get_classifier
from app.models import ClassificationResponse, ResearchMethod, Source


class FakeClassifier:
    async def classify(self, url: str) -> ClassificationResponse:
        return ClassificationResponse(
            url=url,
            business_name="Visual Studio Code",
            category=Category.SOFTWARE,
            confidence=0.98,
            reason="The website presents a software code editor.",
            research_method=ResearchMethod.WEBSITE_ONLY,
            sources=[Source(title="Visual Studio Code", url=url)],
        )


def test_classify_returns_structured_result() -> None:
    app.dependency_overrides[get_classifier] = lambda: FakeClassifier()
    try:
        with TestClient(app) as client:
            response = client.post(
                "/classify", json={"url": "https://code.visualstudio.com/"}
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "Software"
    assert body["research_method"] == "website_only"
    assert body["sources"][0]["url"] == "https://code.visualstudio.com/"


def test_classify_rejects_invalid_url() -> None:
    with TestClient(app) as client:
        response = client.post("/classify", json={"url": "not-a-url"})

    assert response.status_code == 422


def test_classify_rejects_private_ip() -> None:
    with TestClient(app) as client:
        response = client.post("/classify", json={"url": "http://127.0.0.1/admin"})

    assert response.status_code == 422


def test_health_does_not_expose_key() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "openai_configured": False}
    assert "api_key" not in response.text.lower()
