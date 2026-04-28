def headers(token):
    return {"Authorization": f"Bearer {token}"}


def aluno_payload(**overrides):
    data = {
        "nome": "Ana Silva",
        "numero_inscricao": "2026-0001",
        "telefone": "88999990000",
    }
    data.update(overrides)
    return data


def test_listar_alunos_vazio(client, usuario_e_token):
    resp = client.get("/api/alunos/", headers=headers(usuario_e_token))
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert "paginacao" in data
    assert len(data["data"]) == 0
    assert data["paginacao"]["total"] == 0


def test_criar_aluno(client, usuario_e_token):
    resp = client.post("/api/alunos/", headers=headers(usuario_e_token), data=aluno_payload())
    assert resp.status_code == 201
    data = resp.json()
    assert data["nome"] == "Ana Silva"
    assert data["numero_inscricao"] == "2026-0001"
    assert data["telefone"] == "88999990000"
    assert data["foto"] is None


def test_criar_aluno_rejeita_campos_em_branco(client, usuario_e_token):
    resp = client.post(
        "/api/alunos/",
        headers=headers(usuario_e_token),
        data=aluno_payload(nome="   ", telefone="   "),
    )
    assert resp.status_code == 422


def test_listar_alunos_apos_criar(client, usuario_e_token):
    client.post(
        "/api/alunos/",
        headers=headers(usuario_e_token),
        data=aluno_payload(nome="Ana"),
    )
    resp = client.get("/api/alunos/", headers=headers(usuario_e_token))
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert "paginacao" in data
    assert len(data["data"]) == 1
    assert data["data"][0]["nome"] == "Ana"


def test_buscar_aluno(client, usuario_e_token):
    criado = client.post(
        "/api/alunos/",
        headers=headers(usuario_e_token),
        data=aluno_payload(nome="Ana"),
    ).json()
    resp = client.get(f"/api/alunos/{criado['id']}", headers=headers(usuario_e_token))
    assert resp.status_code == 200
    assert resp.json()["nome"] == "Ana"


def test_buscar_aluno_nao_encontrado(client, usuario_e_token):
    resp = client.get("/api/alunos/9999", headers=headers(usuario_e_token))
    assert resp.status_code == 404


def test_atualizar_aluno(client, usuario_e_token):
    criado = client.post(
        "/api/alunos/",
        headers=headers(usuario_e_token),
        data=aluno_payload(nome="Ana"),
    ).json()
    resp = client.put(
        f"/api/alunos/{criado['id']}",
        headers=headers(usuario_e_token),
        data=aluno_payload(nome="Ana Souza", numero_inscricao="2026-0099", telefone="88888880000"),
    )
    assert resp.status_code == 200
    assert resp.json()["nome"] == "Ana Souza"
    assert resp.json()["numero_inscricao"] == "2026-0099"


def test_atualizar_aluno_rejeita_campos_em_branco(client, usuario_e_token):
    criado = client.post(
        "/api/alunos/",
        headers=headers(usuario_e_token),
        data=aluno_payload(nome="Ana"),
    ).json()
    resp = client.put(
        f"/api/alunos/{criado['id']}",
        headers=headers(usuario_e_token),
        data=aluno_payload(nome="   "),
    )
    assert resp.status_code == 422


def test_deletar_aluno(client, usuario_e_token):
    criado = client.post(
        "/api/alunos/",
        headers=headers(usuario_e_token),
        data=aluno_payload(nome="Ana"),
    ).json()
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

    criado = client.post(
        "/api/alunos/",
        headers=headers(token_a),
        data=aluno_payload(nome="Aluno de A", numero_inscricao="A-001", telefone="88000000000"),
    ).json()

    resp = client.get(f"/api/alunos/{criado['id']}", headers=headers(token_b))
    assert resp.status_code == 404


def test_numero_inscricao_duplicado_na_mesma_escola(client, usuario_e_token):
    primeiro = client.post(
        "/api/alunos/",
        headers=headers(usuario_e_token),
        data=aluno_payload(nome="Ana", numero_inscricao="MAT-100"),
    )
    assert primeiro.status_code == 201

    duplicado = client.post(
        "/api/alunos/",
        headers=headers(usuario_e_token),
        data=aluno_payload(nome="Bruno", numero_inscricao="MAT-100", telefone="88999991111"),
    )
    assert duplicado.status_code == 400
    assert duplicado.json()["erro"] == "Numero de inscricao ja cadastrado para esta escola"


def test_numero_inscricao_pode_repetir_em_escolas_diferentes(client):
    for email in ["a@test.com", "b@test.com"]:
        client.post("/api/auth/registrar", json={"nome": "N", "email": email, "senha": "senha123"})

    token_a = client.post("/api/auth/login", json={"email": "a@test.com", "senha": "senha123"}).json()["access_token"]
    token_b = client.post("/api/auth/login", json={"email": "b@test.com", "senha": "senha123"}).json()["access_token"]

    resp_a = client.post(
        "/api/alunos/",
        headers=headers(token_a),
        data=aluno_payload(nome="Aluno A", numero_inscricao="MAT-200"),
    )
    resp_b = client.post(
        "/api/alunos/",
        headers=headers(token_b),
        data=aluno_payload(nome="Aluno B", numero_inscricao="MAT-200", telefone="88999992222"),
    )

    assert resp_a.status_code == 201
    assert resp_b.status_code == 201


def test_sem_autenticacao(client):
    resp = client.get("/api/alunos/")
    assert resp.status_code == 401
