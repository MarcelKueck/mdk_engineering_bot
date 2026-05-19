"""Minimal SOAP client for the EU VIES checkVatService endpoint.

VIES exposes SOAP-only (no JSON). We hand-construct the SOAP envelope
rather than pulling in zeep — a single endpoint with a known shape.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

from mdk_bot.config import get_settings


class VIESError(RuntimeError):
    """Any error talking to VIES."""


@dataclass(frozen=True)
class VIESResult:
    """Parsed VIES response for a qualified query."""

    valid: bool
    name_match: str | None
    address_match: str | None
    consultation_number: str | None
    raw: str


_SOAP_TMPL = """\
<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:urn="urn:ec.europa.eu:taxud:vies:services:checkVat:types">
  <soapenv:Header/>
  <soapenv:Body>
    <urn:checkVatApprox>
      <urn:countryCode>{country}</urn:countryCode>
      <urn:vatNumber>{number}</urn:vatNumber>
      <urn:requesterCountryCode>{req_country}</urn:requesterCountryCode>
      <urn:requesterVatNumber>{req_number}</urn:requesterVatNumber>
    </urn:checkVatApprox>
  </soapenv:Body>
</soapenv:Envelope>
"""


def _split(vat_id: str) -> tuple[str, str]:
    vat_id = vat_id.strip().upper().replace(" ", "")
    if len(vat_id) < 3 or not vat_id[:2].isalpha():
        raise VIESError(f"Invalid VAT-ID format: {vat_id!r}")
    return vat_id[:2], vat_id[2:]


def _extract(tag: str, body: str) -> str | None:
    match = re.search(rf"<(?:\w+:)?{tag}>([^<]*)</(?:\w+:)?{tag}>", body)
    if match is None:
        return None
    return match.group(1)


class VIESClient:
    """Single-method SOAP client over httpx."""

    def __init__(self, *, url: str | None = None) -> None:
        settings = get_settings()
        self._url = url or settings.VIES_API_URL
        self._requester = settings.VIES_REQUESTER_VAT_ID
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> VIESClient:
        if not self._requester:
            raise VIESError("VIES_REQUESTER_VAT_ID is not configured.")
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0))
        return self

    async def __aexit__(self, *_exc: object) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def check(self, vat_id: str) -> VIESResult:
        if self._client is None:
            raise RuntimeError("VIESClient used outside its async context.")
        country, number = _split(vat_id)
        req_country, req_number = _split(self._requester)
        body = _SOAP_TMPL.format(
            country=country,
            number=number,
            req_country=req_country,
            req_number=req_number,
        )
        response = await self._client.post(
            self._url,
            content=body,
            headers={"Content-Type": "text/xml; charset=utf-8"},
        )
        if response.status_code != 200:
            raise VIESError(f"VIES returned {response.status_code}: {response.text[:200]}")
        text = response.text
        valid_raw = _extract("valid", text)
        return VIESResult(
            valid=valid_raw == "true",
            name_match=_extract("traderNameMatch", text),
            address_match=_extract("traderStreetMatch", text)
            or _extract("traderAddressMatch", text),
            consultation_number=_extract("requestIdentifier", text),
            raw=text,
        )
