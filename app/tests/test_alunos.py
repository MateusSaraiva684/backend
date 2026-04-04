def headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_listar_alunos_vazio(client, usuario_e_token):
    resp = client.get("/api/alunos/", headers=headers(usuario_e_token))
    assert resp.status_code == 200
    assert resp.json() == []


def test_criar_aluno(client, usuario_e_token):
    resp = client.post("/api/alunos/", headers=headers(usuario_e_token),
                       data={"nome": "Ana Silva", "telefone": "88999990000"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["nome"] == "Ana Silva"
    assert data["telefone"] == "88999990000"
    assert data["foto"] is None


def test_listar_alunos_apos_criar(client, usuario_e_token):
    client.post("/api/alunos/", headers=headers(usuario_e_token),
                data={"nome": "Ana", "telefone": "88999990000"})
    resp = client.get("/api/alunos/", headers=headers(usuario_e_token))
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_buscar_aluno(client, usuario_e_token):
    criado = client.post("/api/alunos/", headers=headers(usuario_e_token),
                         data={"nome": "Ana", "telefone": "88999990000"}).json()
    resp = client.get(f"/api/alunos/{criado['id']}", headers=headers(usuario_e_token))
    assert resp.status_code == 200
    assert resp.json()["nome"] == "Ana"


def test_buscar_aluno_nao_encontrado(client, usuario_e_token):
    resp = client.get("/api/alunos/9999", headers=headers(usuario_e_token))
    assert resp.status_code == 404


def test_atualizar_aluno(client, usuario_e_token):
    criado = client.post("/api/alunos/", headers=headers(usuario_e_token),
                         data={"nome": "Ana", "telefone": "88999990000"}).json()
    resp = client.put(f"/api/alunos/{criado['id']}", headers=headers(usuario_e_token),
                      data={"nome": "Ana Souza", "telefone": "88888880000"})
    assert resp.status_code == 200
    assert resp.json()["nome"] == "Ana Souza"


def test_deletar_aluno(client, usuario_e_token):
    criado = client.post("/api/alunos/", headers=headers(usuario_e_token),
                         data={"nome": "Ana", "telefone": "88999990000"}).json()
    resp = client.delete(f"/api/alunos/{criado['id']}", headers=headers(usuario_e_token))
    assert resp.status_code == 204

    resp = client.get(f"/api/alunos/{criado['id']}", headers=headers(usuario_e_token))
    assert resp.status_code == 404


def test_isolamento_entre_usuarios(client):
    """Usuário B não pode ver alunos do usuário A."""
    for email in ["a@test.com", "b@test.com"]:
        client.post("/api/auth/registrar", json={"nome": "N", "email": email, "senha": "senha123"})

    token_a = client.post("/api/auth/login", json={"email": "a@test.com", "senha": "senha123"}).json()["access_token"]
    token_b = client.post("/api/auth/login", json={"email": "b@test.com", "senha": "senha123"}).json()["access_token"]

    criado = client.post("/api/alunos/", headers=headers(token_a),
                         data={"nome": "Aluno de A", "telefone": "88000000000"}).json()

    resp = client.get(f"/api/alunos/{criado['id']}", headers=headers(token_b))
    assert resp.status_code == 404


def test_sem_autenticacao(client):
    resp = client.get("/api/alunos/")
    assert resp.status_code == 401
