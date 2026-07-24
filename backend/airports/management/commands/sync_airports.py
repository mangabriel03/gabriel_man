from __future__ import annotations

import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from airports.models import Airport


class Command(BaseCommand):
    help = "Seed or refresh the Airport table from airportgap.com or a local fixture."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--from-fixture",
            type=str,
            default=None,
            help="Path to a JSON file with an array of airport objects.",
        )

    def handle(self, *args, **options) -> None:
        fixture_path = options.get("from_fixture")
        if fixture_path:
            records = self._load_fixture(Path(fixture_path))
        else:
            records = self._fetch_from_api()

        created, updated = self._upsert(records)
        self.stdout.write(
            self.style.SUCCESS(f"Airports synced: {created} created, {updated} updated.")
        )

    def _load_fixture(self, path: Path) -> list[dict]:
        if not path.exists():
            raise CommandError(f"Fixture not found: {path}")
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, list):
            raise CommandError("Fixture must be a JSON array of airport objects.")
        return data

    def _fetch_from_api(self) -> list[dict]:
        base = settings.AIRPORTGAP_BASE_URL.rstrip("/")
        url = f"{base}/airports"
        headers = {}
        if settings.AIRPORTGAP_TOKEN:
            headers["Authorization"] = f"Bearer token={settings.AIRPORTGAP_TOKEN}"

        records: list[dict] = []
        while url:
            try:
                resp = requests.get(url, headers=headers, timeout=15)
                resp.raise_for_status()
            except requests.RequestException as exc:
                self.stderr.write(self.style.ERROR(f"airportgap.com request failed: {exc}"))
                sys.exit(2)
            body = resp.json()
            for item in body.get("data", []):
                attrs = item.get("attributes", {})
                records.append(
                    {
                        "iata": attrs.get("iata"),
                        "icao": attrs.get("icao") or None,
                        "name": attrs.get("name", ""),
                        "city": attrs.get("city", ""),
                        "country": attrs.get("country", ""),
                        "latitude": attrs.get("latitude"),
                        "longitude": attrs.get("longitude"),
                    }
                )
            url = (body.get("links") or {}).get("next")
        return records

    @transaction.atomic
    def _upsert(self, records: Iterable[dict]) -> tuple[int, int]:
        created_count = 0
        updated_count = 0
        for rec in records:
            iata = (rec.get("iata") or "").strip().upper()
            if not iata:
                continue
            try:
                lat = Decimal(str(rec["latitude"]))
                lng = Decimal(str(rec["longitude"]))
            except (InvalidOperation, KeyError, TypeError):
                continue
            defaults = {
                "icao": (rec.get("icao") or None),
                "name": rec.get("name") or "",
                "city": rec.get("city") or "",
                "country": rec.get("country") or "",
                "latitude": lat,
                "longitude": lng,
            }
            _, created = Airport.objects.update_or_create(iata=iata, defaults=defaults)
            if created:
                created_count += 1
            else:
                updated_count += 1
        return created_count, updated_count
