import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_login_access_token():
    """
    本地免密模式下，输入 admin 即可获取会话 Token。
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        login_data = {
            "username": "admin",
            "password": "",
            "source": "web",
        }
        response = await ac.post("/api/auth/login", json=login_data)

        assert response.status_code == 200
        assert "token" in response.json()
        assert response.json()["user"]["user_type"] == "admin"
        assert response.json()["token_type"] == "bearer"
