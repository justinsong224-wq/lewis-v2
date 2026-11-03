import importlib.util
import json
import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

@pytest.fixture(scope="module")
def client():
    directory = os.environ.get("LEWIS_DEMO_APP_DIR")
    if not directory:
        pytest.skip("需要任务目录")
    spec = importlib.util.spec_from_file_location("sms_generated_app", Path(directory) / "app.py")
    module = importlib.util.module_from_spec(spec); sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    with TestClient(module.app) as value:
        yield value
    sys.modules.pop(spec.name, None)

def test_page(client):
    r = client.get("/"); assert r.status_code == 200 and "短信垃圾信息分类" in r.text

@pytest.mark.parametrize("text", ["Are we still meeting for dinner tonight?", "Congratulations! You have won a free prize. Call now!"])
def test_real_prediction(client, text):
    from src.inference import Predictor
    expected = Predictor(Path(os.environ["SMS_ASSET_DIR"]) / "outputs/transformer.pt").predict(text)
    r = client.post("/predict", json={"text": text}); assert r.status_code == 200
    result = r.json(); assert result["label"] == expected["label"]
    assert result["spam_probability"] == pytest.approx(expected["spam_probability"], abs=1e-5)
    assert 0 <= result["spam_probability"] <= 1
    assert result["spam_probability"] + result["ham_probability"] == pytest.approx(1, abs=1e-5)

def test_validation(client):
    for text in ("", "   ", "a" * 5001):
        assert client.post("/predict", json={"text": text}).status_code == 422

def test_metrics(client):
    r = client.get("/metrics"); assert r.status_code == 200
    assets = Path(os.environ["SMS_ASSET_DIR"]) / "outputs"
    assert r.json() == {"metrics": json.loads((assets / "metrics.json").read_text()), "dataset": json.loads((assets / "dataset_stats.json").read_text())}
