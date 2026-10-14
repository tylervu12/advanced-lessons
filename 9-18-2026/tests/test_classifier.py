import asyncio
from types import SimpleNamespace

from app.categories import Category
from app.classifier import WebsiteClassifier, _extract_tool_sources
from app.config import Settings
from app.models import ModelClassification, ResearchMethod, Source


class FakeResponses:
    def __init__(self, response: object) -> None:
        self.response = response
        self.kwargs: dict = {}

    async def parse(self, **kwargs: object) -> object:
        self.kwargs = kwargs
        return self.response


def test_classifier_uses_hosted_web_search_and_structured_output() -> None:
    parsed = ModelClassification(
        business_name="Vons",
        category=Category.GROCERY_SUPERMARKETS,
        confidence=0.99,
        reason="Vons operates supermarkets.",
        research_method=ResearchMethod.WEBSITE_PLUS_SEARCH,
        sources=[Source(title="Vons", url="https://www.vons.com/")],
    )
    api_response = SimpleNamespace(output_parsed=parsed, output=[])
    responses = FakeResponses(api_response)
    client = SimpleNamespace(responses=responses)
    classifier = WebsiteClassifier(
        Settings(openai_api_key="test-key"),
        client=client,  # type: ignore[arg-type]
    )

    result = asyncio.run(classifier.classify("https://www.vons.com/"))

    assert result.category == Category.GROCERY_SUPERMARKETS
    assert responses.kwargs["tools"] == [
        {
            "type": "web_search",
            "search_context_size": "medium",
            "external_web_access": True,
        }
    ]
    assert responses.kwargs["tool_choice"] == "required"
    assert responses.kwargs["text_format"] is ModelClassification
    assert responses.kwargs["store"] is False


def test_extract_tool_sources_deduplicates_and_ignores_invalid_urls() -> None:
    response = {
        "output": [
            {
                "type": "web_search_call",
                "action": {
                    "type": "search",
                    "sources": [
                        {"title": "Company", "url": "https://example.com/"},
                        {"title": "Duplicate", "url": "https://example.com/"},
                        {"title": "Invalid", "url": "file:///tmp/private"},
                    ],
                },
            }
        ]
    }

    sources = _extract_tool_sources(response)

    assert sources == [Source(title="Company", url="https://example.com/")]
