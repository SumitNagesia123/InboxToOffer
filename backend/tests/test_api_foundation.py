import pytest
from fastapi import status


def test_root_endpoint(client):
    """Verify root endpoint returns project metadata."""
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert data["docs"] == "/docs"
    assert data["health"] == "/api/v1/health"


def test_health_check_endpoint(client):
    """Verify health check endpoint returns 200 and healthy database connectivity."""
    response = client.get("/api/v1/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert "version" in data
    assert "timestamp" in data


def test_openapi_schema_endpoint(client):
    """Verify OpenAPI 3 specification is available."""
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == status.HTTP_200_OK
    schema = response.json()
    assert schema["openapi"].startswith("3.")
    assert "info" in schema
    assert "paths" in schema
    assert "/api/v1/health" in schema["paths"]


def test_swagger_docs_endpoint(client):
    """Verify Swagger UI documentation is accessible."""
    response = client.get("/docs")
    assert response.status_code == status.HTTP_200_OK
    assert "swagger-ui" in response.text.lower()


def test_standardized_404_error_response(client):
    """Verify unknown routes return standardized JSON error format."""
    response = client.get("/api/v1/non_existent_route_12345")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert data["success"] is False
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"
    assert "message" in data["error"]


def test_cors_headers(client):
    """Verify CORS middleware responds with correct headers for allowed origins."""
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "GET",
    }
    response = client.options("/api/v1/health", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
