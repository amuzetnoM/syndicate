import types


def test_generate_raises_when_no_client(monkeypatch):
    import scripts.genai_compat as compat

    # Ensure no client is available
    monkeypatch.setattr(compat, "GENAI_NEW", False)
    monkeypatch.setattr(compat, "genai_mod", None)

    compat.configure(api_key=None)

    model = compat.GenerativeModel("models/gemini-lite")

    try:
        model.generate_content("Hello")
    except RuntimeError as e:
        assert "No genai client available" in str(e)
    else:
        raise AssertionError("Expected RuntimeError when no client present")


def test_generate_uses_client(monkeypatch):
    import scripts.genai_compat as compat

    # Create a fake genai module with Client that returns predictable responses
    fake_genai = types.SimpleNamespace()

    class FakeModel:
        def __init__(self, text):
            self.text = text

    class FakeModelsAPI:
        def generate_content(self, model, input):
            return FakeModel(text=f"ECHO:{input}")

    class FakeClient:
        def __init__(self, api_key=None, **kwargs):
            self.api_key = api_key
            self.models = FakeModelsAPI()

    fake_genai.Client = FakeClient

    monkeypatch.setattr(compat, "GENAI_NEW", True)
    monkeypatch.setattr(compat, "genai_mod", fake_genai)

    compat.configure(api_key="abc")

    model = compat.GenerativeModel("models/gemini-lite")
    r = model.generate_content("Ping")
    assert hasattr(r, "text")
    assert r.text.startswith("ECHO:Ping")
