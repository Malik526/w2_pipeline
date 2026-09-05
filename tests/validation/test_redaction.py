from w2_pipeline.validation.redaction import is_sensitive_field, redact_value


def test_redact_ssn_masks_all_but_last_four_digits() -> None:
    assert redact_value("employee.ssn", "123-45-6789") == "***-**-6789"


def test_redact_ein_masks_all_but_last_four_digits() -> None:
    # 9 digits total ("123456789"); the last 4 ("6789") survive, the
    # preceding 5 ("12345") are masked, separators preserved.
    assert redact_value("employer.ein", "12-3456789") == "**-***6789"


def test_redact_name_fields_fully_redacted() -> None:
    assert redact_value("employee.first_name", "Ada") == "[REDACTED]"
    assert redact_value("employee.last_name", "Lovelace") == "[REDACTED]"
    assert redact_value("employer.name", "Acme Corp") == "[REDACTED]"


def test_redact_address_fields_fully_redacted() -> None:
    assert redact_value("employee.address.address_line_1", "1 Main St") == "[REDACTED]"
    assert redact_value("employer.address.city", "Springfield") == "[REDACTED]"


def test_redact_none_value_stays_none() -> None:
    assert redact_value("employee.ssn", None) is None
    assert redact_value("employee.first_name", None) is None


def test_redact_non_sensitive_field_passthrough() -> None:
    assert redact_value("federal_wages_and_taxes.box_1_wages_tips_other_compensation", "1234.56") == "1234.56"
    assert redact_value("box_13.retirement_plan", True) is True


def test_is_sensitive_field_matches_known_pii_paths() -> None:
    assert is_sensitive_field("employee.ssn") is True
    assert is_sensitive_field("employer.ein") is True
    assert is_sensitive_field("employee.first_name") is True
    assert is_sensitive_field("employer.control_number") is True


def test_is_sensitive_field_excludes_non_pii_paths() -> None:
    assert is_sensitive_field("federal_wages_and_taxes.box_1_wages_tips_other_compensation") is False
    assert is_sensitive_field("box_13.retirement_plan") is False
    assert is_sensitive_field("employee.address.state") is False


def test_redact_malformed_ssn_still_masks_digits() -> None:
    # Even a malformed value (the exact case `invalid_ssn_format` reports)
    # should never leak more than the last 4 digits.
    assert redact_value("employee.ssn", "0000000005") == "******0005"
