from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_retrieve_returns_tfidf_scored_result_for_herd_query() -> None:
    response = client.post(
        "/retrieve",
        json={
            "query": "I am tired of the herd mentality and constant resentment around me",
            "top_k": 5,
        },
    )

    assert response.status_code == 200

    payload = response.json()
    results = payload["results"]

    assert payload["query"] == "I am tired of the herd mentality and constant resentment around me"
    assert payload["top_k"] == 5
    assert len(results) > 0

    top_result = results[0]

    assert top_result["source_id"] == "bge_herd_morality_excerpt"
    assert top_result["work"] == "Beyond Good and Evil"
    assert "display_text" in top_result
    assert "vector_score" in top_result
    assert "keyword_score" in top_result

    assert top_result["display_text"]
    assert "TITLE:" not in top_result["display_text"]
    assert top_result["vector_score"] is not None
    assert top_result["keyword_score"] is not None
    assert top_result["score"] >= top_result["keyword_score"]


def test_chat_returns_grounded_herd_answer_with_diverse_citations() -> None:
    response = client.post(
        "/chat",
        json={
            "message": "I am tired of the herd mentality and constant resentment around me",
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["message"] == "I am tired of the herd mentality and constant resentment around me"
    assert "Primary pattern detected: herd mentality." in payload["answer"]
    assert "The strongest supporting passage I found is from Beyond Good and Evil" in payload["answer"]
    assert "A second supporting passage comes from" in payload["answer"]

    matched_card_ids = payload["matched_card_ids"]
    assert "herd_morality_and_approval" in matched_card_ids

    citations = payload["citations"]
    assert len(citations) >= 2

    citation_source_ids = [
        citation["source_id"]
        for citation in citations
        if citation.get("source_id")
    ]

    assert "bge_herd_morality_excerpt" in citation_source_ids
    assert len(set(citation_source_ids)) >= 2

    first_citation_excerpt = citations[0]["text_excerpt"]
    assert "TITLE:" not in first_citation_excerpt


def test_chat_returns_grounded_excuse_answer() -> None:
    response = client.post(
        "/chat",
        json={
            "message": "I keep making excuses because struggle feels too heavy",
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["message"] == "I keep making excuses because struggle feels too heavy"
    assert len(payload["citations"]) > 0
    assert len(payload["matched_card_ids"]) > 0
    assert "The strongest supporting passage I found is from" in payload["answer"]