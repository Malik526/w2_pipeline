from w2_pipeline.contracts.employee_name import (
    parse_employee_name,
    split_first_name_and_initial,
)


def test_split_first_name_and_initial_keeps_box_e_fields_distinct() -> None:
    assert split_first_name_and_initial("Jordan Q") == ("Jordan", "Q")
    assert split_first_name_and_initial("Jesús D") == ("Jesús", "D")
    assert split_first_name_and_initial("Óliver") == ("Óliver", None)
    assert split_first_name_and_initial("") == (None, None)


def test_split_first_name_and_initial_requires_single_uppercase_initial() -> None:
    assert split_first_name_and_initial("Mary Ann") == ("Mary Ann", None)
    assert split_first_name_and_initial("Nicole h") == ("Nicole h", None)


def test_parse_employee_name_preserves_middle_initial_and_suffix() -> None:
    parsed = parse_employee_name("SyntheticFirst F SyntheticLast Jr.")

    assert parsed.first_name == "SyntheticFirst"
    assert parsed.middle_initial == "F"
    assert parsed.last_name == "SyntheticLast"
    assert parsed.suffix == "Jr."
