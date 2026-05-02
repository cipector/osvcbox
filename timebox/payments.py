from base64 import b64encode
from decimal import Decimal
from io import BytesIO

import qrcode
import qrcode.image.svg


def regular_payment_qr_data_uri(payment):
    image = qrcode.make(_spd_payload(payment), image_factory=qrcode.image.svg.SvgPathImage)
    output = BytesIO()
    image.save(output)
    encoded = b64encode(output.getvalue()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def czech_iban(account_prefix, account_number, bank_code):
    bban = f"{bank_code.zfill(4)}{(account_prefix or '').zfill(6)}{account_number.zfill(10)}"
    check_number = 98 - (int(f"{bban}123500") % 97)
    return f"CZ{check_number:02d}{bban}"


def _spd_payload(payment):
    parts = [
        "SPD",
        "1.0",
        f"ACC:{czech_iban(payment.account_prefix, payment.account_number, payment.bank_code)}",
        f"AM:{_amount(payment.amount_czk)}",
        "CC:CZK",
    ]
    if payment.variable_symbol:
        parts.append(f"X-VS:{payment.variable_symbol}")
    if payment.message:
        parts.append(f"MSG:{_sanitize(payment.message)}")
    return "*".join(parts)


def _amount(value):
    return f"{Decimal(value):.2f}"


def _sanitize(value):
    return str(value).replace("*", " ").strip()
