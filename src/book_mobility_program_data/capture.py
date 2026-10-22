"""Capture the official DiscoverEU call rules through the shared lake runtime."""

import argparse
import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

from .cli import resource, timestamp, validate
from .observability import init_sentry, report_exit

DISCOVEREU_OPENS = "2026-10-01T12:00:00+02:00"
DISCOVEREU_DEADLINE = "2026-10-15T12:00:00+02:00"


class Text(HTMLParser):
    """Extract visible page text while ignoring executable content."""

    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "svg"}:
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg"}:
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, value):
        if not self.hidden:
            self.parts.append(value)


EUROPEAN_YOUTH_COUNTRIES = [
    "AT",
    "BE",
    "BG",
    "HR",
    "CY",
    "CZ",
    "DK",
    "EE",
    "FI",
    "FR",
    "DE",
    "EL",
    "HU",
    "IE",
    "IT",
    "LV",
    "LT",
    "LU",
    "MT",
    "NL",
    "PL",
    "PT",
    "RO",
    "SK",
    "SI",
    "ES",
    "SE",
    "IS",
    "LI",
    "MK",
    "NO",
    "RS",
    "TR",
]


REQUIRED_MARKERS = {
    "discovereu-autumn-2026": (
        "rules of the discovereu call for applications",
        "autumn 2026",
        "around 40 000 young people",
        "travel passes",
        "discount cards",
        "1 october 2026",
        "15 october 2026",
        "1 march 2027",
        "31 may 2028",
        "eligible applicants",
        "18th birthday",
    ),
    "erasmus-youth-exchanges": (
        "mobility projects for young people",
        "youth exchanges",
        "different countries",
    ),
    "european-solidarity-corps-volunteering": (
        "european solidarity corps",
        "volunteering projects",
        "volunteers abroad",
    ),
    "culture-moves-europe-residency-hosts": (
        "call for residency hosts",
        "financial support",
        "residency project",
    ),
    "cost-eu-resolve-conference-grants": (
        "eu-resolve",
        "conference grants 2026",
        "young researchers",
        "travel grant",
    ),
}


GENERIC_SOURCES = {
    "erasmus-youth-exchanges": {
        "value_kind": "access",
        "eligibility_text": "Erasmus+ Youth Exchanges require eligible organisations or informal groups and participants from eligible programme countries; project and age rules must be checked in the current guide.",
        "coverage": "Short non-formal learning exchanges bring young people from different countries together; travel and participation support follows the Erasmus+ project rules.",
    },
    "european-solidarity-corps-volunteering": {
        "value_kind": "access",
        "eligibility_text": "The European Solidarity Corps supports organisations hosting or sending volunteers abroad; age, registration, quality-label and project rules apply.",
        "coverage": "Volunteering projects can place participants in solidarity activities abroad; duration, allowance, travel and insurance terms are project-specific.",
    },
    "culture-moves-europe-residency-hosts": {
        "value_kind": "cash",
        "eligibility_text": "Culture Moves Europe residency hosts must be eligible legal entities based in Creative Europe countries and meet the published sector and hosting requirements.",
        "coverage": "The residency-host call provides financial support to selected legal entities hosting artists and cultural professionals; the current call dates and phase-two terms must be checked.",
    },
    "cost-eu-resolve-conference-grants": {
        "value_kind": "cash",
        "eligibility_text": "The COST EU-RESOLVE call supports eligible young researchers and innovators attending relevant meetings, conferences, workshops and training schools; network and call rules apply.",
        "coverage": "Conference and travel grants contribute to participation costs under the published COST Action call and grant-awarding rules; amount and selection are not inferred.",
    },
}


def normalize(raw, source, checked_at):
    """Turn the public call rules into one conservative mobility record."""
    if source["id"] not in REQUIRED_MARKERS:
        raise ValueError("unknown mobility source")
    parser = Text()
    parser.feed(raw.decode("utf-8"))
    text = " ".join(" ".join(parser.parts).split())
    folded = text.casefold()
    required = REQUIRED_MARKERS[source["id"]]
    if not all(marker.casefold() in folded for marker in required):
        raise ValueError("mobility source drift or challenge page")

    if source["id"] == "discovereu-autumn-2026":
        # Applications are accepted only from the published opening time (1 October
        # 2026, 12:00 Brussels) until the fixed deadline. Before opening and after the
        # deadline the call is not accepting applications, so it must not be "open".
        observed = timestamp(checked_at)
        closed = not (timestamp(DISCOVEREU_OPENS) <= observed < timestamp(DISCOVEREU_DEADLINE))
        item = {
            "id": source["id"],
            "title": "DiscoverEU autumn 2026 travel pass",
            "category": source["category"],
            "source_url": source["source_url"],
            "provider": source["provider"],
            "status": "closed" if closed else "open",
            "deadline": {
                "kind": "fixed",
                "at": DISCOVEREU_DEADLINE,
            },
            "eligible_countries": EUROPEAN_YOUTH_COUNTRIES,
            "eligibility_text": (
                "Applicants must be 18 during 2026 and citizens or residents of an "
                "EU Member State, an EU-associated overseas territory, or an "
                "Erasmus+ associated country. A valid identity, passport or residence "
                "permit document is required by the official application; no identity "
                "number is stored here."
            ),
            "value": {
                "kind": "access",
                "amount": None,
                "currency": None,
                "guaranteed": False,
            },
            "cost": {
                "fee_amount": None,
                "currency": None,
                "auto_renewal": None,
                "notes": (
                    "The call describes a travel pass and discount card; participants "
                    "must plan accommodation, subsistence and basic insurance costs. "
                    "No application-fee claim is inferred."
                ),
            },
            "terms": {
                "destination_country": "MULTI",
                "travel_start": "2027-03-01",
                "coverage": (
                    "A successful participant receives a travel pass for seven train "
                    "days during a chosen period of up to 30 days between 1 March 2027 "
                    "and 31 May 2028, plus a DiscoverEU discount card."
                ),
                "visa_support": "unknown",
            },
            "related_records": [],
            "provenance": {
                "evidence_kind": "captured",
                "source_id": source["id"],
                "source_record_id": source["id"],
                "checked_at": checked_at,
                "raw_object_key": None,
                "bronze_manifest_key": None,
            },
        }
    else:
        metadata = GENERIC_SOURCES[source["id"]]
        item = {
            "id": source["id"],
            "title": source["title"],
            "category": source["category"],
            "source_url": source["source_url"],
            "provider": source["provider"],
            "status": "unknown",
            "deadline": {"kind": "unknown", "at": None},
            "eligible_countries": [],
            "eligibility_text": metadata["eligibility_text"],
            "value": {
                "kind": metadata["value_kind"],
                "amount": None,
                "currency": None,
                "guaranteed": False,
            },
            "cost": {
                "fee_amount": None,
                "currency": None,
                "auto_renewal": None,
                "notes": source["cost_notes"],
            },
            "terms": {
                "destination_country": "MULTI",
                "travel_start": None,
                "coverage": metadata["coverage"],
                "visa_support": "unknown",
            },
            "related_records": [],
            "provenance": {
                "evidence_kind": "captured",
                "source_id": source["id"],
                "source_record_id": source["id"],
                "checked_at": checked_at,
                "raw_object_key": None,
                "bronze_manifest_key": None,
            },
        }
    return {
        "schema_version": source["schema_version"],
        "source": source["product"],
        "retrieved_at": checked_at,
        "data_status": "live",
        "items": [item],
    }


def source_config(source_id=None):
    if source_id is None:
        return resource("source.json")
    if not re.fullmatch(r"[a-z0-9-]+", source_id):
        raise ValueError("invalid source id")
    base = resource("source.json")
    if base["id"] == source_id:
        return base
    try:
        return resource("source-" + source_id + ".json")
    except FileNotFoundError:
        raise ValueError("unknown source id") from None


def main(argv=None):
    selector = argparse.ArgumentParser(add_help=False)
    selector.add_argument("--source-id")
    selected, remaining = selector.parse_known_args(argv)
    root = os.environ.get("SOLO_DATA_LAKE_ROOT")
    if not root:
        print("Set SOLO_DATA_LAKE_ROOT to the local shared capture/lake runtime.", file=sys.stderr)
        return 2
    runtime = Path(root).resolve() / "infra/scripts"
    if not (runtime / "discovery/capture_runtime.py").is_file():
        print("Shared discovery runtime is unavailable.", file=sys.stderr)
        return 2
    sys.path.insert(0, str(runtime))
    from discovery.capture_runtime import VERSION, run

    if VERSION != 1:
        raise RuntimeError("unsupported shared capture runtime")
    source = source_config(selected.source_id)
    sentry = init_sentry(source["id"])
    return report_exit(sentry, source["id"], run(source, normalize, validate, remaining))


if __name__ == "__main__":
    raise SystemExit(main())
