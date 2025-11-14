"""Patch httpx to use mock proxy server for eval scenarios.

This module patches httpx at import time to route requests through the mock server.
It should be imported before httpx is used.
"""

import os
import sys

# Only patch if we're in an eval scenario (workspace path contains kurt_eval_)
if "kurt_eval_" in os.getcwd():
    # Patch httpx before it's imported by Kurt
    import httpx as _httpx_module

    PROXY_URL = "http://127.0.0.1:8765"

    # Store originals
    _original_get = _httpx_module.get
    _original_Client = _httpx_module.Client  # noqa: N816
    _original_AsyncClient = _httpx_module.AsyncClient  # noqa: N816

    # Patched functions
    def _patched_get(*args, **kwargs):
        if "proxies" not in kwargs:
            kwargs["proxies"] = PROXY_URL
        return _original_get(*args, **kwargs)

    class _PatchedClient(_httpx_module.Client):
        def __init__(self, *args, **kwargs):
            if "proxies" not in kwargs:
                kwargs["proxies"] = PROXY_URL
            super().__init__(*args, **kwargs)

    class _PatchedAsyncClient(_httpx_module.AsyncClient):
        def __init__(self, *args, **kwargs):
            if "proxies" not in kwargs:
                kwargs["proxies"] = PROXY_URL
            super().__init__(*args, **kwargs)

    # Apply patches
    _httpx_module.get = _patched_get
    _httpx_module.Client = _PatchedClient
    _httpx_module.AsyncClient = _PatchedAsyncClient

    print(f"[httpx_mock_patch] Patched httpx to use proxy: {PROXY_URL}", file=sys.stderr)
