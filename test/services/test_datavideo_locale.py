from datetime import date
from decimal import Decimal

import pytest

from app.datavideo.locale import (
    ENGLISH_US,
    SPANISH_SPAIN,
    format_decimal,
    format_long_date,
    format_month,
    format_percent,
)


def test_spanish_decimals_use_a_comma_and_round_half_up():
    assert format_decimal(Decimal("0.0825"), 3, SPANISH_SPAIN) == "0,083"


def test_spanish_four_digit_numbers_have_no_thousands_separator():
    assert format_decimal(Decimal("1234.5"), 1, SPANISH_SPAIN) == "1234,5"


def test_spanish_large_numbers_group_thousands_with_a_dot():
    assert format_decimal(Decimal("1234567.891"), 2, SPANISH_SPAIN) == "1.234.567,89"


def test_english_numbers_group_thousands_with_a_comma():
    assert format_decimal(Decimal("1234.5"), 1, ENGLISH_US) == "1,234.5"


def test_negative_values_keep_their_sign():
    assert format_decimal(Decimal("-12345.6"), 1, SPANISH_SPAIN) == "-12.345,6"


def test_percent_spacing_follows_each_language():
    assert format_percent(Decimal("180.58"), 0, SPANISH_SPAIN) == "181 %"
    assert format_percent(Decimal("180.58"), 0, ENGLISH_US) == "181%"


def test_long_dates_are_written_out_in_each_language():
    day = date(2026, 11, 4)

    assert format_long_date(day, SPANISH_SPAIN) == "miércoles 4 de noviembre de 2026"
    assert format_long_date(day, ENGLISH_US) == "Wednesday, November 4, 2026"


def test_unsupported_language_is_rejected():
    with pytest.raises(ValueError, match="unsupported locale"):
        format_decimal(Decimal("1"), 0, "fr-FR")


@pytest.mark.parametrize(
    "locale, expected", [(SPANISH_SPAIN, "septiembre de 2026"), (ENGLISH_US, "September 2026")]
)
def test_months_are_written_with_their_year(locale, expected):
    assert format_month(2026, 9, locale) == expected
