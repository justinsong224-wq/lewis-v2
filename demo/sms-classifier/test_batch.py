from test_acceptance import client

def test_batch(client):
    r = client.post("/predict-batch", content="text\nHello there\nCall now to win a free prize", headers={"Content-Type": "text/csv"})
    assert r.status_code == 200
    rows = r.json()["results"]; assert len(rows) == 2
    for row in rows:
        single = client.post("/predict", json={"text": row["text"]}).json()
        assert row["label"] == single["label"]
        assert abs(row["spam_probability"] - single["spam_probability"]) < 1e-5

def test_batch_invalid(client):
    for content in ["wrong\nx", "text\n", 'text\n""', "text\n" + "hello\n" * 101, "text\n" + "a" * 5001, b"text\n\xff"]:
        assert client.post("/predict-batch", content=content, headers={"Content-Type": "text/csv"}).status_code == 422

def test_batch_size(client):
    assert client.post("/predict-batch", content=b"x" * (1024*1024+1), headers={"Content-Type": "text/csv"}).status_code == 413
