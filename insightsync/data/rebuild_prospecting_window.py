from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class CommandSpec:
    label: str
    args: tuple[str, ...]


def build_commands(*, start_date: str, end_date: str) -> list[CommandSpec]:
    commands: list[CommandSpec] = [
        CommandSpec("company", ("-m", "insightsync.data", "--sources", "company", "--company-enable-enrichment", "--once")),
        CommandSpec(
            "hkgov",
            (
                "-m",
                "insightsync.data",
                "--sources",
                "hkgov",
                "--hkgov-start-date",
                start_date,
                "--hkgov-end-date",
                end_date,
                "--once",
            ),
        ),
        CommandSpec(
            "szse",
            (
                "-m",
                "insightsync.data",
                "--sources",
                "szse",
                "--szse-start-date",
                start_date,
                "--szse-end-date",
                end_date,
                "--once",
            ),
        ),
        CommandSpec(
            "investhk",
            ("-m", "insightsync.data", "--sources", "investhk", "--investhk-include-article-text", "--once"),
        ),
        CommandSpec("dongfang", ("-m", "insightsync.data", "--sources", "dongfang", "--dongfang-fetch", "--once")),
        CommandSpec("market", ("-m", "insightsync.data", "--sources", "censtatd,guangdong,hkma,adb,kpmg", "--once")),
    ]
    for year, month in (("2025", "11"), ("2025", "12"), ("2026", "01"), ("2026", "02"), ("2026", "03"), ("2026", "04"), ("2026", "05")):
        commands.append(
            CommandSpec(
                f"hkex-{year}-{month}",
                (
                    "-m",
                    "insightsync.data",
                    "--sources",
                    "hkex",
                    "--hkex-target-year",
                    year,
                    "--hkex-target-month",
                    month,
                    "--once",
                ),
            )
        )
    commands.extend(
        [
            CommandSpec(
                "company-mapping",
                (
                    "-m",
                    "insightsync.data",
                    "--skip-ingestion",
                    "--sync-market-companies",
                    "--backfill-company-ids",
                ),
            ),
            CommandSpec("parsing", ("-m", "insightsync.data", "--skip-ingestion", "--run-parsing")),
        ]
    )
    return commands


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rebuild the prospecting data window.")
    parser.add_argument("--start-date", default="2025-11-05")
    parser.add_argument("--end-date", default="2026-05-05")
    parser.add_argument("--execute", action="store_true", help="Run commands instead of printing them.")
    parser.add_argument("--stop-on-error", action="store_true", help="Stop after the first failed source.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    commands = build_commands(start_date=args.start_date, end_date=args.end_date)
    for command in commands:
        full = (sys.executable, *command.args)
        print(f"[{command.label}] " + " ".join(full), flush=True)
        if args.execute:
            result = subprocess.run(full, check=False)
            if result.returncode != 0:
                print(f"[{command.label}] failed with exit code {result.returncode}", flush=True)
                if args.stop_on_error:
                    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
