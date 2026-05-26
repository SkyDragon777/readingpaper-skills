from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULTS: dict[str, Any] = {
    "backends": {
        "openalex": {"enabled": True, "required": True, "api_key_env": "OPENALEX_API_KEY"},
        "semantic_scholar": {
            "enabled": "auto",
            "required": False,
            "api_key_env": "SEMANTIC_SCHOLAR_API_KEY",
            "allow_unauthenticated": True,
            "fail_soft": True,
        },
        "crossref": {
            "enabled": True,
            "required": False,
            "mailto_env": "CROSSREF_MAILTO",
            "plus_token_env": "CROSSREF_PLUS_API_TOKEN",
            "fail_soft": True,
        },
        "arxiv": {"enabled": True, "required": False, "fail_soft": True},
    },
    "discovery": {
        "include_backward": True,
        "include_forward": True,
        "include_related": True,
        "include_semantic": True,
        "max_candidates": 200,
        "max_per_seed": {"backward": 80, "forward": 80, "related": 80, "semantic": 80},
    },
    "filters": {
        "year_from": None,
        "year_to": None,
        "exclude_retracted": True,
        "exclude_paratext": True,
        "languages": [],
    },
    "download": {"oa_only": True, "max_downloads": 40, "verify_pdf_header": True, "timeout_seconds": 30},
}


@dataclass
class RuntimeConfig:
    project_dir: Path
    data: dict[str, Any]
    env: dict[str, str]
    warnings: list[str]

    @property
    def cache_dir(self) -> Path:
        raw = self.env.get("RELEVANTPAPER_CACHE_DIR") or ".readingpaper/cache"
        path = Path(raw)
        return path if path.is_absolute() else self.project_dir / path

    @property
    def output_dir(self) -> Path:
        return self.project_dir / "outputs" / "relevantpaper"

    def backend_status(self) -> dict[str, dict[str, str | bool]]:
        return {
            "openalex": {
                "enabled": bool(self.data["backends"]["openalex"].get("enabled")),
                "auth": "api_key_present" if self.env.get("OPENALEX_API_KEY") else "missing_api_key",
                "status": "ok" if self.env.get("OPENALEX_API_KEY") else "limited",
            },
            "semantic_scholar": {
                "enabled": bool(self.data["backends"]["semantic_scholar"].get("enabled")),
                "auth": "api_key_present" if self.env.get("SEMANTIC_SCHOLAR_API_KEY") else "no_api_key",
                "status": "ok" if self.env.get("SEMANTIC_SCHOLAR_API_KEY") else "skipped_or_public_only",
            },
            "crossref": {
                "enabled": bool(self.data["backends"]["crossref"].get("enabled")),
                "auth": "mailto_present" if self.env.get("CROSSREF_MAILTO") else "public_pool",
                "status": "ok",
            },
            "arxiv": {"enabled": bool(self.data["backends"]["arxiv"].get("enabled")), "auth": "not_required", "status": "ok"},
        }


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = {k: (v.copy() if isinstance(v, dict) else v) for k, v in base.items()}
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def load_dotenv(project_dir: Path) -> None:
    try:
        from dotenv import load_dotenv as dotenv_load

        dotenv_load(project_dir / ".env", override=False)
        return
    except Exception:
        pass
    path = project_dir / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, value = text.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_yaml_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        import yaml

        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def load_config(project_dir: str | Path, cli_args: dict[str, Any] | None = None) -> RuntimeConfig:
    root = Path(project_dir).resolve()
    load_dotenv(root)
    env = dict(os.environ)
    data = deep_merge(DEFAULTS, load_yaml_config(root / ".readingpaper" / "config.yaml"))
    warnings: list[str] = []
    if env.get("RELEVANTPAPER_MAX_CANDIDATES"):
        data["discovery"]["max_candidates"] = int(env["RELEVANTPAPER_MAX_CANDIDATES"])
    if env.get("RELEVANTPAPER_MAX_DOWNLOADS"):
        data["download"]["max_downloads"] = int(env["RELEVANTPAPER_MAX_DOWNLOADS"])
    for key, value in (cli_args or {}).items():
        if value is None:
            continue
        if key.startswith("include_"):
            data["discovery"][key] = parse_bool(value)
        elif key == "max_candidates":
            data["discovery"]["max_candidates"] = int(value)
        elif key == "max_downloads":
            data["download"]["max_downloads"] = int(value)
        elif key == "oa_only":
            data["download"]["oa_only"] = parse_bool(value)
    if not env.get("OPENALEX_API_KEY"):
        warnings.append("OPENALEX_API_KEY is missing; full live discovery requires OpenAlex access.")
    if not env.get("CROSSREF_MAILTO"):
        warnings.append("CROSSREF_MAILTO is missing; Crossref will use the public pool.")
    return RuntimeConfig(root, data, env, warnings)
