"""
backend/tests/test_health.py
─────────────────────────────────────────────────────────────
Infrastructure tests for liveness and API root endpoints.

These tests validate the /health and / endpoints that are consumed
by the Docker healthcheck stanza and container orchestration platforms
(e.g. Kubernetes readiness probes). A failure here means the container
would be marked unhealthy and traffic would not be routed to it.
"""

from __future__ import annotations


def test_health_endpoint_returns_200(client) -> None:
    """GET /health must return HTTP 200 with a healthy status payload.

    This is the exact endpoint probed by the Docker healthcheck stanza in
    docker-compose.yml — a non-200 response would mark the container
    unhealthy and prevent the frontend from starting.
    """
    response = client.get("/health")
    assert response.status_code == 200


def test_health_endpoint_returns_json_body(client) -> None:
    """GET /health must return ``{"status": "healthy"}`` as its JSON body.

    The exact key/value is checked so that future payload changes that
    break the healthcheck contract are caught by the test suite.
    """
    response = client.get("/health")
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"


def test_health_endpoint_content_type(client) -> None:
    """GET /health must respond with a JSON Content-Type header."""
    response = client.get("/health")
    assert "application/json" in response.headers.get("content-type", "")


def test_root_endpoint_returns_200(client) -> None:
    """GET / must return HTTP 200 confirming the API is reachable."""
    response = client.get("/")
    assert response.status_code == 200


def test_root_endpoint_payload(client) -> None:
    """GET / must return status, app name, and docs_url in its payload."""
    response = client.get("/")
    data = response.json()
    assert data["status"] == "healthy"
    assert "app" in data
    assert "docs_url" in data


def test_health_endpoint_no_auth_required(client) -> None:
    """GET /health must be accessible without any Authorization header.

    Liveness probes are unauthenticated by design — the probe cannot
    carry a JWT token, and the endpoint must not require one.
    """
    # Explicitly send no auth headers
    response = client.get("/health", headers={})
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
