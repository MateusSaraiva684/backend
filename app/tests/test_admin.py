def headers(token):
    return {"Authorization": f"Bearer {token}"}


def login_admin(client) -> str:
    resp = client.post(
        "/api/auth/login",
        json={"email": "admin@admin.com", "senha": "Mateusqwe123"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_admin_deleta_usuario_com_alunos(client):
    client.post(
        "/api/auth/registrar",
        json={"nome": "Usuario", "email": "usuario@test.com", "senha": "senha123"},
    )
    login_resp = client.post(
        "/api/auth/login",
        json={"email": "usuario@test.com", "senha": "senha123"},
    )
    user_data = login_resp.json()
    user_id = user_data["usuario"]["id"]

    aluno_resp = client.post(
        "/api/alunos/",
        headers=headers(user_data["access_token"]),
        data={
            "nome": "Aluno",
            "numero_inscricao": "MAT-900",
            "telefone": "88999990000",
        },
    )
    assert aluno_resp.status_code == 201

    admin_token = login_admin(client)
    resp = client.delete(
        f"/api/admin/usuarios/{user_id}",
        headers=headers(admin_token),
    )

    assert resp.status_code == 200
    assert resp.json()["mensagem"] == "Usuario removido com sucesso"


def test_admin_listar_alunos_rejeita_limit_invalido(client):
    admin_token = login_admin(client)
    resp = client.get(
        "/api/admin/alunos?limit=-1&page=1",
        headers=headers(admin_token),
    )

    assert resp.status_code == 422
