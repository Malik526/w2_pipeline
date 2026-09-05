from w2_pipeline.validation.models import ValidationIssue, ValidationSeverity, ValidationStatus
from w2_pipeline.validation.routing import RoutingPolicy, decide_status


def _issue(severity: ValidationSeverity) -> ValidationIssue:
    return ValidationIssue(code="test_code", severity=severity, message="test message")


def test_no_issues_accepted() -> None:
    assert decide_status([]) == ValidationStatus.ACCEPTED


def test_info_only_accepted() -> None:
    assert decide_status([_issue(ValidationSeverity.INFO)]) == ValidationStatus.ACCEPTED


def test_warning_only_accepted_by_default() -> None:
    assert decide_status([_issue(ValidationSeverity.WARNING)]) == ValidationStatus.ACCEPTED


def test_error_always_needs_review() -> None:
    assert decide_status([_issue(ValidationSeverity.ERROR)]) == ValidationStatus.NEEDS_REVIEW


def test_error_plus_warning_needs_review() -> None:
    issues = [_issue(ValidationSeverity.WARNING), _issue(ValidationSeverity.ERROR)]
    assert decide_status(issues) == ValidationStatus.NEEDS_REVIEW


def test_conservative_policy_escalates_warning_to_review() -> None:
    policy = RoutingPolicy(escalate_warnings=True)
    assert decide_status([_issue(ValidationSeverity.WARNING)], policy) == ValidationStatus.NEEDS_REVIEW


def test_conservative_policy_still_accepts_info_only() -> None:
    policy = RoutingPolicy(escalate_warnings=True)
    assert decide_status([_issue(ValidationSeverity.INFO)], policy) == ValidationStatus.ACCEPTED


def test_conservative_policy_does_not_change_error_outcome() -> None:
    policy = RoutingPolicy(escalate_warnings=True)
    assert decide_status([_issue(ValidationSeverity.ERROR)], policy) == ValidationStatus.NEEDS_REVIEW
