"""Itaú-Empresas credit card CSV parser.

Ported from the legacy ``economy/importers/itau_csv_parser.py`` with
the output shape changed to :class:`CreditCardStatementData` so the
importer is format-agnostic.

The legacy CSV is quirky: encoding is Latin-1, separator is ``;``,
currency strings are prefixed with ``RR$`` (the bank's own
formatting glitch), and dates come as ``31/jan.`` — a day-of-month
plus a Portuguese month abbreviation — so the parser has to resolve
the year from the statement's closing date.
"""

from __future__ import annotations

import hashlib
import re

from src.parsers.types import CreditCardStatementData, RawTransaction


_MONTHS = {
    "jan": 1, "fev": 2, "mar": 3, "abr": 4,
    "mai": 5, "jun": 6, "jul": 7, "ago": 8,
    "set": 9, "out": 10, "nov": 11, "dez": 12,
}


def _parse_brl(raw: str) -> float:
    """Convert 'RR$1.545,75' / '-RR$3.339,16' to a float."""
    clean = (
        raw.replace("RR$", "")
        .replace("R$", "")
        .replace(".", "")
        .replace(",", ".")
        .strip()
    )
    return float(clean)


def _resolve_date(day_month: str, closing_date: str) -> str:
    """Resolve '31/jan.' to YYYY-MM-DD using the statement's closing date.

    Transactions usually fall in the months leading up to the closing
    date. When the transaction month is *after* the closing month, the
    transaction belongs to the previous year (an edge case for
    December purchases on a January closing).
    """
    match = re.match(r"(\d{1,2})/(\w+)\.", day_month.strip())
    if not match:
        return ""
    day = int(match.group(1))
    month_str = match.group(2).lower()
    month = _MONTHS.get(month_str)
    if not month:
        return ""

    closing_match = re.search(r"(\d{2})/(\d{2})/(\d{4})", closing_date)
    if closing_match:
        closing_year = int(closing_match.group(3))
        closing_month = int(closing_match.group(2))
    else:
        year_match = re.search(r"(\d{4})", closing_date)
        closing_year = int(year_match.group(1)) if year_match else 2026
        closing_month = 12

    year = closing_year if month <= closing_month else closing_year - 1
    return f"{year}-{month:02d}-{day:02d}"


def _fit_id(date: str, description: str, amount: float) -> str:
    """Stable 16-char hash for dedup; the source CSV ships no native id."""
    raw = f"{date}|{description}|{amount}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def _normalise(s: str) -> str:
    """Lowercase + collapse common encoding glitches so section headers
    can be matched whether the file is decoded as UTF-8 or Latin-1."""
    return (
        s.lower()
        .replace("ã§", "ç")
        .replace("ã£", "ã")
        .replace("ã", "a")
        .replace("ç", "c")
    )


def parse_csv_itau_cc(content: str) -> CreditCardStatementData:
    """Parse an Itaú-Empresas credit card CSV statement."""
    lines = content.splitlines()

    card_number: str | None = None
    closing_date: str | None = None
    total: float | None = None

    # Card number lives in a 'MASTERCARD' / 'VISA' header row.
    for line in lines[:10]:
        if "MASTERCARD" in line or "VISA" in line:
            m = re.search(r"(\d{4}\.\w+\.\w+\.\d{4})", line)
            if m:
                card_number = m.group(1)
                break

    # Closing date lives on the line after the 'vencimento' marker.
    for idx, line in enumerate(lines):
        if "vencimento" in line.lower() and idx + 1 < len(lines):
            m = re.search(r"(\d{2}/\d{2}/\w+)", lines[idx + 1])
            if m:
                closing_date = m.group(1)
                break

    # The year on the 'vencimento' line is sometimes 'YYYY' literally;
    # patch it from any nearby ISO-shaped date.
    real_year: int | None = None
    for line in lines:
        m = re.search(r"PAGAMENTO EFETUADO (\d{4})-(\d{2})-(\d{2})", line)
        if m:
            real_year = int(m.group(1))
            break
    if real_year is None:
        for line in lines:
            m = re.search(r"(\d{2}/\d{2}/(\d{4}))", line)
            if m:
                real_year = int(m.group(2))
                break
    if closing_date and "YYYY" in closing_date and real_year is not None:
        closing_date = closing_date.replace("YYYY", str(real_year))

    # 'Total da fatura' on its own line is the period total.
    for line in lines:
        if line.startswith("Total da fatura") and "RR$" in line:
            cells = [p for p in line.split(";") if "RR$" in p]
            if cells:
                total = _parse_brl(cells[0])
                break

    # Walk the lines section by section. The CSV has two transaction
    # blocks: national and international. The amount column index
    # differs slightly between blocks but both publish the value at
    # position 10 in semicolon-split form.
    transactions: list[RawTransaction] = []
    section: str | None = None
    for line in lines:
        stripped = line.strip().rstrip(";")
        normed = _normalise(stripped)

        if "lancamentos nacionais" in normed and "total" not in normed:
            section = "national"
            continue
        if "lancamentos internacionais" in normed and "total" not in normed:
            section = "international"
            continue
        if "produtos" in normed and "encargos" in normed:
            section = None
            continue
        if normed.startswith("total de ") or normed.startswith("repasse de iof"):
            continue
        if normed.startswith("data;;descri"):
            continue
        if not section:
            continue

        cells = line.split(";")
        if len(cells) < 11:
            continue
        if not re.match(r"\d{1,2}/\w+\.", cells[0].strip()):
            continue
        value_raw = cells[10].strip()
        if not value_raw or "RR$" not in value_raw:
            continue

        date = _resolve_date(cells[0].strip(), closing_date or "")
        description = cells[2].strip()
        if not date or not description:
            continue

        amount = _parse_brl(value_raw)
        transactions.append(
            RawTransaction(
                date=date,
                description=description,
                amount=-amount,  # credit card line = expense
                type="debit",
                fit_id=_fit_id(date, description, amount),
            )
        )

    return CreditCardStatementData(
        card_number=card_number,
        closing_date=closing_date,
        total=total,
        transactions=transactions,
    )
