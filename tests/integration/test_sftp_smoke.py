from __future__ import annotations

import os


def test_sftp_smoke_is_opt_in() -> None:
    env_path = os.getenv("MC_SERVER_MANAGER_INTEGRATION_ENV")
    if not env_path:
        return

    assert os.path.exists(env_path)
