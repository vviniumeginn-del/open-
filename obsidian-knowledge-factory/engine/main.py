import argparse
import sys
import time
from pathlib import Path

import yaml

from io_utils import append_log, load_env_file
from llm_client import OpenAICompatibleClient
from pipeline import Pipeline, summary_to_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Obsidian knowledge factory")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--once", action="store_true", help="Run once and exit")
    mode.add_argument("--daemon", action="store_true", help="Run forever")
    parser.add_argument("--config", default="engine/config.yaml", help="Path to config yaml")
    parser.add_argument("--env-file", default="engine/.env", help="Path to env file")
    parser.add_argument("--interval", type=int, default=None, help="Daemon interval seconds")
    return parser.parse_args()


def load_config(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Config must be a YAML object")
    if "vault_path" not in raw:
        raise ValueError("Config missing required field: vault_path")
    return raw


def build_client():
    return OpenAICompatibleClient.from_env()


def run_once(config: dict) -> int:
    client = build_client()
    pipe = Pipeline(config, client)
    summary = pipe.process_once()
    print(summary_to_text(summary))
    return 0


def run_daemon(config: dict, interval: int) -> int:
    client = build_client()
    pipe = Pipeline(config, client)
    log_dir = Path(config["vault_path"]) / config.get("log_dir_name", "logs")
    while True:
        try:
            summary = pipe.process_once()
            print(summary_to_text(summary))
        except Exception as exc:  # noqa: BLE001
            append_log(log_dir / "daemon_error.log", str(exc))
        time.sleep(interval)


def main() -> int:
    args = parse_args()
    load_env_file(Path(args.env_file))
    config = load_config(Path(args.config))
    interval = args.interval if args.interval is not None else int(config.get("scan_interval_seconds", 600))

    if args.once:
        return run_once(config)
    return run_daemon(config, interval)


if __name__ == "__main__":
    sys.exit(main())
