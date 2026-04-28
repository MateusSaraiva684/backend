from app.services.face_recognition_service import FaceRecognitionResult, FaceRecognitionService


def headers(token):
    return {"Authorization": f"Bearer {token}"}


def aluno_payload(**overrides):
    data = {
        "nome": "Ana Silva",
        "numero_inscricao": "2026-1000",
        "telefone": "88999990000",
    }
    data.update(overrides)
    return data


def criar_aluno(client, token):
    return client.post(
        "/api/alunos/",
        headers=headers(token),
        data=aluno_payload(),
    ).json()


def test_registrar_presenca_manual(client, usuario_e_token):
    aluno = criar_aluno(client, usuario_e_token)

    resp = client.post(
        "/api/presencas/manual",
        headers=headers(usuario_e_token),
        json={"aluno_id": aluno["id"]},
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["aluno_id"] == aluno["id"]
    assert data["origem"] == "manual"
    assert data["status"] == "confirmado"


def test_listar_historico_presencas(client, usuario_e_token):
    aluno = criar_aluno(client, usuario_e_token)
    client.post(
        "/api/presencas/manual",
        headers=headers(usuario_e_token),
        json={"aluno_id": aluno["id"]},
    )

    resp = client.get(
        f"/api/presencas/aluno/{aluno['id']}",
        headers=headers(usuario_e_token),
    )

    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_reconhecimento_facial_cria_presenca(client, usuario_e_token, monkeypatch):
    aluno = criar_aluno(client, usuario_e_token)

    async def reconhecer_fake(self, payload):
        assert payload.base64_image == "imagem-em-base64"
        return FaceRecognitionResult(aluno_id=aluno["id"], confianca=0.97)

    monkeypatch.setattr(FaceRecognitionService, "reconhecer", reconhecer_fake)

    resp = client.post(
        "/api/reconhecimento/facial",
        headers=headers(usuario_e_token),
        json={"imagem_base64": "imagem-em-base64"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["aluno_id"] == aluno["id"]
    assert data["confianca"] == 0.97
    assert data["presenca"]["origem"] == "facial"
    assert data["presenca"]["status"] == "confirmado"


def test_reconhecimento_facial_exige_imagem(client, usuario_e_token):
    resp = client.post(
        "/api/reconhecimento/facial",
        headers=headers(usuario_e_token),
        json={},
    )

    assert resp.status_code == 400


def test_reconhecimento_facial_rejeita_imagem_muito_grande(
    client,
    usuario_e_token,
    monkeypatch,
):
    from app.core.config import settings

    monkeypatch.setattr(settings, "MAX_IMAGE_UPLOAD_BYTES", 4)
    resp = client.post(
        "/api/reconhecimento/facial",
        headers={**headers(usuario_e_token), "content-type": "image/jpeg"},
        content=b"12345",
    )

    assert resp.status_code == 400
