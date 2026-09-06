import inspect

from w2_pipeline.evaluation.combined_employer_name_signals import (
    AgreementState,
    SignalRow,
    agreement_state_counts,
    classify_agreement,
    combine_and,
    combine_or,
    confusion_matrix,
)


def test_classify_agreement_covers_all_four_states() -> None:
    assert classify_agreement(True, True) == AgreementState.BOTH
    assert classify_agreement(True, False) == AgreementState.ADDRESS_ONLY
    assert classify_agreement(False, True) == AgreementState.LAYOUT_ONLY
    assert classify_agreement(False, False) == AgreementState.NEITHER


def test_combine_or_flags_when_either_signal_fires() -> None:
    assert combine_or(True, False)
    assert combine_or(False, True)
    assert combine_or(True, True)
    assert not combine_or(False, False)


def test_combine_and_requires_both_signals() -> None:
    assert combine_and(True, True)
    assert not combine_and(True, False)
    assert not combine_and(False, True)
    assert not combine_and(False, False)


def _row(doc_id: str, *, address: bool, layout: bool, correct: bool) -> SignalRow:
    return SignalRow(document_id=doc_id, variant_id="rotated_png", address_signal=address, layout_signal=layout, correct=correct)


def test_agreement_state_counts_tallies_all_four_buckets() -> None:
    rows = [
        _row("a", address=True, layout=True, correct=False),
        _row("b", address=True, layout=False, correct=True),
        _row("c", address=False, layout=True, correct=True),
        _row("d", address=False, layout=False, correct=True),
    ]

    counts = agreement_state_counts(rows)

    assert counts == {"both": 1, "address_only": 1, "layout_only": 1, "neither": 1}


def test_address_only_disagreement_case_is_a_false_positive_for_address_alone() -> None:
    """Synthetic/adversarial fixture forcing a disagreement the real
    600-document dataset never produced: a correct employer name that
    happens to look address-shaped (address fires) but has normal,
    single-observation layout (layout does not fire)."""

    rows = [_row("x", address=True, layout=False, correct=True)]

    address_matrix = confusion_matrix(rows, flag_key="address")
    layout_matrix = confusion_matrix(rows, flag_key="layout")

    assert address_matrix["false_positives"] == 1
    assert layout_matrix["false_positives"] == 0
    assert layout_matrix["true_negatives"] == 1


def test_layout_only_disagreement_case_is_a_false_positive_for_layout_alone() -> None:
    """The mirror case: a correct name spuriously split into two OCR
    observations (layout fires) with no address-shaped text (address does
    not fire)."""

    rows = [_row("y", address=False, layout=True, correct=True)]

    address_matrix = confusion_matrix(rows, flag_key="address")
    layout_matrix = confusion_matrix(rows, flag_key="layout")

    assert layout_matrix["false_positives"] == 1
    assert address_matrix["false_positives"] == 0


def test_or_strategy_maximizes_recall_across_disagreeing_true_positives() -> None:
    """Two erroneous documents, each caught by only one signal: OR catches
    both, AND catches neither."""

    rows = [
        _row("addr-only-error", address=True, layout=False, correct=False),
        _row("layout-only-error", address=False, layout=True, correct=False),
    ]

    or_matrix = confusion_matrix(rows, flag_key="or")
    and_matrix = confusion_matrix(rows, flag_key="and")

    assert or_matrix["true_positives"] == 2
    assert or_matrix["recall"] == 1.0
    assert and_matrix["true_positives"] == 0
    assert and_matrix["recall"] == 0.0


def test_and_strategy_minimizes_false_positives_across_disagreeing_correct_documents() -> None:
    """Two correct documents, each spuriously flagged by only one signal:
    AND flags neither (0% false-review rate); OR flags both."""

    rows = [
        _row("addr-only-fp", address=True, layout=False, correct=True),
        _row("layout-only-fp", address=False, layout=True, correct=True),
    ]

    or_matrix = confusion_matrix(rows, flag_key="or")
    and_matrix = confusion_matrix(rows, flag_key="and")

    assert or_matrix["false_positives"] == 2
    assert or_matrix["false_review_rate"] == 1.0
    assert and_matrix["false_positives"] == 0
    assert and_matrix["false_review_rate"] == 0.0


def test_confusion_matrix_both_fire_true_positive_scored_identically_by_or_and_and() -> None:
    rows = [_row("both-error", address=True, layout=True, correct=False)]

    assert confusion_matrix(rows, flag_key="or")["true_positives"] == 1
    assert confusion_matrix(rows, flag_key="and")["true_positives"] == 1


def test_confusion_matrix_neither_fires_true_negative() -> None:
    rows = [_row("neither-correct", address=False, layout=False, correct=True)]

    matrix = confusion_matrix(rows, flag_key="or")

    assert matrix["true_negatives"] == 1
    assert matrix["false_positives"] == 0


def test_signal_functions_take_only_booleans_no_ground_truth_leakage() -> None:
    """Structural safeguard: neither `classify_agreement`, `combine_or`,
    nor `combine_and` accepts a ground-truth/expected-value parameter --
    they can only ever see the two already-computed signal booleans."""

    for fn in (classify_agreement, combine_or, combine_and):
        signature = inspect.signature(fn)
        param_names = list(signature.parameters)
        assert param_names == ["address_signal", "layout_signal"]


def test_module_has_no_validation_or_routing_dependency() -> None:
    import ast
    from pathlib import Path

    import w2_pipeline.evaluation.combined_employer_name_signals as module

    source = Path(module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)

    assert not any(module_name.startswith("w2_pipeline.validation") for module_name in imported)
