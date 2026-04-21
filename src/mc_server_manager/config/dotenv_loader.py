from __future__ import annotations

from pathlib import Path
from typing import Iterable

from mc_server_manager.config.settings import AppSettings, RconSettings, SftpSettings


class DotEnvLoader:
    required_keys = (
        "SFTP_HOST",
        "SFTP_PORT",
        "SFTP_USERNAME",
        "SFTP_PASSWORD",
        "SFTP_SERVER_ROOT",
    )

    def default_paths(self) -> list[Path]:
        candidates = [Path.cwd() / ".env", Path(__file__).resolve().parents[3] / ".env"]
        unique_paths: list[Path] = []
        seen: set[Path] = set()
        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved not in seen:
                unique_paths.append(resolved)
                seen.add(resolved)
        return unique_paths

    def load(self, candidate_paths: Iterable[Path] | None = None) -> AppSettings:
        candidate_paths = list(candidate_paths or self.default_paths())
        env_path = next((path for path in candidate_paths if path.is_file()), None)
        if env_path is None:
            checked = ", ".join(str(path) for path in candidate_paths)
            raise FileNotFoundError(f"Expected a .env file. Checked: {checked}")

        values: dict[str, str] = {}
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"')

        missing = [key for key in self.required_keys if not values.get(key)]
        if missing:
            raise ValueError(f"Missing required .env keys: {', '.join(missing)}")

        try:
            port = int(values["SFTP_PORT"])
        except ValueError as exc:
            raise ValueError("SFTP_PORT must be a valid integer.") from exc

        sftp_settings = SftpSettings(
            host=values["SFTP_HOST"],
            port=port,
            username=values["SFTP_USERNAME"],
            password=values["SFTP_PASSWORD"],
            server_root=values["SFTP_SERVER_ROOT"],
        )
        rcon_settings, rcon_reason = self._load_optional_rcon_settings(values)
        return AppSettings(
            sftp=sftp_settings,
            rcon=rcon_settings,
            rcon_unavailable_reason=rcon_reason,
        )

    def _load_optional_rcon_settings(
        self,
        values: dict[str, str],
    ) -> tuple[RconSettings | None, str | None]:
        rcon_keys = ("RCON_HOST", "RCON_PORT", "RCON_PASSWORD")
        present_keys = [key for key in rcon_keys if values.get(key)]

        if not present_keys:
            return None, (
                "RCON is not configured. Set RCON_HOST, RCON_PORT, and RCON_PASSWORD in .env "
                "to enable console access."
            )

        missing_keys = [key for key in rcon_keys if not values.get(key)]
        if missing_keys:
            return None, (
                "RCON is disabled because the .env file is incomplete. Missing: "
                f"{', '.join(missing_keys)}"
            )

        try:
            rcon_port = int(values["RCON_PORT"])
        except ValueError:
            return None, "RCON is disabled because RCON_PORT must be a valid integer."

        return (
            RconSettings(
                host=values["RCON_HOST"],
                port=rcon_port,
                password=values["RCON_PASSWORD"],
            ),
            None,
        )
