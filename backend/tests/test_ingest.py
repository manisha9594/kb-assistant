def test_rejects_unsupported_type(client):
    res = client.post("/api/documents", files={"file": ("data.xlsx", b"x")})
    assert res.status_code == 422
    assert "Unsupported" in res.json()["detail"]


def test_rejects_empty_text(client):
    res = client.post("/api/documents", files={"file": ("empty.txt", b"   ")})
    assert res.status_code == 422


def test_indexes_all_formats_and_reupload_replaces(client, indexed):
    docs = {d["filename"]: d for d in client.get("/api/documents").json()}
    assert set(docs) == {"employee_handbook.pdf", "it_security_policy.docx", "expense_policy.md"}
    assert docs["employee_handbook.pdf"]["pages"] == 3

    before = docs["expense_policy.md"]["chunks"]
    client.post("/api/documents", files={"file": ("expense_policy.md", b"Meals: $75 per day.")})
    after = {d["filename"]: d for d in client.get("/api/documents").json()}["expense_policy.md"]
    assert after["chunks"] == 1 and before >= 1
