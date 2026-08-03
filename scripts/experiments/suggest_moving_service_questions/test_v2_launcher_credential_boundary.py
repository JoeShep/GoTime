"""Container-only, network-free proof of explicit credential construction."""

from __future__ import annotations

import os

from openai_client_factory import (
    EVALUATION_CREDENTIAL_NAME,
    OPENAI_API_BASE_URL,
    OPENAI_SDK_VERSION,
    _construct_openai_client,
    _read_evaluation_credential,
)


class FakeHttp:
    def __init__(self, **kwargs):
        assert kwargs == {"trust_env": False}
        self.closed = False

    def close(self):
        self.closed = True


class FakeClient:
    max_retries = 0

    def __init__(self, **kwargs):
        assert kwargs["api_key"] == os.environ[EVALUATION_CREDENTIAL_NAME]
        assert kwargs["base_url"] == OPENAI_API_BASE_URL
        assert kwargs["max_retries"] == 0
        self.closed = False

    def close(self):
        self.closed = True


def main() -> int:
    credential = _read_evaluation_credential(os.environ)
    owner = _construct_openai_client(
        credential,
        sdk_version=OPENAI_SDK_VERSION,
        client_constructor=FakeClient,
        http_client_constructor=FakeHttp,
    )
    owner.close()
    assert owner.client.closed and owner._http_client.closed
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
