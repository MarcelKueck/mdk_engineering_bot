"""EU VIES VAT validation — qualified queries with a consultation number.

A qualified query (where the operator's own VAT ID is sent as the
requester) returns a consultation number, which is the legal proof that
the validation happened. Result is persisted as :class:`VatValidation`
and a PDF proof is generated and stored.
"""

from mdk_bot.capabilities.vies.client import VIESClient, VIESError
from mdk_bot.capabilities.vies.engine import is_enabled, validate_vat

__all__ = ["VIESClient", "VIESError", "is_enabled", "validate_vat"]
