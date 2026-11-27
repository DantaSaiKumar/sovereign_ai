import requests
from .config import validate_local_ollama_url, OLLAMA_BASE_URL, GENERAL_MODEL, VISION_MODEL

class ModelUnavailable(RuntimeError):
    pass

class LocalModelClient:
    def __init__(self, base_url=OLLAMA_BASE_URL, timeout=180):
        self.base_url = validate_local_ollama_url(base_url)
        self.timeout = timeout

    def list_models(self):
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            return [m.get("name") for m in response.json().get("models", [])]
        except requests.RequestException:
            return []

    def choose_model(self, task_type="general", available=None):
        available = available if available is not None else self.list_models()
        if task_type == "vision":
            candidates = [VISION_MODEL]
        else:
            candidates = [GENERAL_MODEL, "llama3.2:1b"]
        for candidate in candidates:
            if candidate in available:
                return candidate
            # Ollama tags may include an implicit :latest.
            if candidate + ":latest" in available:
                return candidate + ":latest"
        return None

    def generate(self, prompt, system=None, model=None):
        selected = model or self.choose_model("general")
        if not selected:
            raise ModelUnavailable(f"No local general model found. Run: ollama pull {GENERAL_MODEL}")
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={"model": selected, "messages": messages, "stream": False,
                      "keep_alive": 0, "options": {"temperature": 0.2, "num_ctx": 2048, "num_predict": 768}},
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json().get("message", {}).get("content", ""), selected
        except requests.RequestException as exc:
            raise ModelUnavailable(f"Local model request failed: {exc}") from exc

    def describe_image(self, image_bytes, prompt="Describe this industrial image and distinguish visible facts from uncertainty."):
        selected = self.choose_model("vision")
        if not selected:
            raise ModelUnavailable(f"No local vision model found. Optional: ollama pull {VISION_MODEL}")
        import base64
        encoded = base64.b64encode(image_bytes).decode("ascii")
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={"model": selected, "messages": [{"role": "user", "content": prompt,
                                                       "images": [encoded]}],
                      "stream": False, "keep_alive": 0,
                      "options": {"temperature": 0.1, "num_ctx": 1536, "num_predict": 384}},
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json().get("message", {}).get("content", ""), selected
        except requests.RequestException as exc:
            raise ModelUnavailable(f"Local vision request failed: {exc}") from exc
