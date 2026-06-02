import pytest


@pytest.mark.usefixtures("app")
class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["code"] == 0
        assert data["data"]["service"] == "up"
        assert data["data"]["database"] == "up"
