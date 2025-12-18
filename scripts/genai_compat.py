"""Compatibility shim for Google GenAI client.

Provides a minimal compatibility layer so existing code using the old
`google.generativeai` package (configure + GenerativeModel.generate_content)
works with the new `google.genai` package.

This shim is intentionally small — it maps `configure(api_key=...)` and
`GenerativeModel(model_name)` to the new client API `google.genai.Client`.
"""
from __future__ import annotations
import logging
from typing import Any

try:
    import google.genai as genai_mod
    GENAI_NEW = True
except Exception:
    genai_mod = None
    GENAI_NEW = False


logger = logging.getLogger("genai_compat")


class _GenaiWrapper:
    """Wrapper exposing `configure(api_key=...)` and `GenerativeModel` class."""

    def __init__(self):
        self._api_key = None
        self._client = None

    def configure(self, api_key: str = None, **kwargs):
        self._api_key = api_key or self._api_key
        if GENAI_NEW and self._api_key:
            try:
                self._client = genai_mod.Client(api_key=self._api_key, **(kwargs or {}))
            except Exception as e:
                logger.debug(f"genai Client init failed: {e}")


    class GenerativeModel:
        def __init__(self, model_name: str):
            self.model_name = model_name

        def generate_content(self, prompt: str) -> Any:
            # Use the client if available
            parent = _genai
            if GENAI_NEW and parent._client:
                try:
                    # Use models.generate_content for a broad compatibility
                    resp = parent._client.models.generate_content(model=self.model_name, input=prompt)

                    # Try to extract a simple textual result in a few common patterns
                    text = None
                    if hasattr(resp, "text") and resp.text:
                        text = resp.text
                    # some responses provide 'output' or 'generations'
                    if not text:
                        if hasattr(resp, "output") and resp.output:
                            try:
                                text = resp.output[0].content
                            except Exception:
                                pass
                    if not text and hasattr(resp, "generations") and resp.generations:
                        try:
                            text = resp.generations[0].text
                        except Exception:
                            pass

                    class R:
                        pass

                    r = R()
                    r.text = text or str(resp)
                    return r
                except Exception as e:
                    raise

            raise RuntimeError("No genai client available to generate content")


# Singleton wrapper instance
_genai = _GenaiWrapper()

# Expose the compatibility surface
configure = _genai.configure
GenerativeModel = _genai.GenerativeModel
