import pytest
from sovereign.config import validate_local_ollama_url
from sovereign.models import LocalModelClient

def test_remote_ollama_url_rejected():
    with pytest.raises(ValueError):
        validate_local_ollama_url("https://api.example.com")

def test_model_router_uses_small_general_model():
    client = LocalModelClient()
    assert client.choose_model("general", ["qwen2.5:1.5b"]) == "qwen2.5:1.5b"
    assert client.choose_model("vision", ["moondream"]) == "moondream"
