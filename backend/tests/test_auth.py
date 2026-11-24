USER = {"full_name": "Test User", "email": "Test@Example.com", "password": "Passw0rd123"}


def register(client, **over):
    return client.post("/api/auth/register", json={**USER, **over})


def login(client, password=USER["password"], email=USER["email"]):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def test_register_success(client):
    r = register(client)
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "test@example.com"
    assert "password" not in body and "hashed_password" not in body


def test_register_duplicate_email(client):
    register(client)
    assert register(client, email="test@example.com").status_code == 409


def test_register_validation(client):
    assert register(client, password="short1").status_code == 422
    assert register(client, password="onlyletters").status_code == 422
    assert register(client, password="12345678").status_code == 422
    assert register(client, email="not-an-email").status_code == 422
    assert register(client, full_name=" ").status_code == 422


def test_login_success_and_me(client):
    register(client)
    r = login(client)
    assert r.status_code == 200
    token = r.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["full_name"] == "Test User"


def test_login_wrong_password_and_unknown_email(client):
    register(client)
    assert login(client, password="Wrong12345").status_code == 401
    assert login(client, email="nobody@example.com").status_code == 401


def test_protected_route_without_or_bad_token(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_logout_revokes_token(client):
    register(client)
    token = login(client).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    assert client.post("/api/auth/logout", headers=h).status_code == 200
    assert client.get("/api/auth/me", headers=h).status_code == 401


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}
