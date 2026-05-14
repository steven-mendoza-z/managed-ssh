from typing import Callable, Optional, TypeVar

from mssh.destination.solve import is_host, is_target
from mssh.messages import error_message

T = TypeVar("T")


def interruptIf_condition(condition: bool, message: str, error_type: str = "Error", exit_code: int = 1) -> None:
    if condition:
        error_message(message, error_type=error_type, exit_code=exit_code)


def interruptIf_none(
    value: Optional[T],
    message: str,
    error_type: str = "Error",
    exit_code: int = 1,
) -> T:
    interruptIf_condition(value is None, message, error_type=error_type, exit_code=exit_code)
    return value


def interruptIf_valueError(
    fn: Callable[..., T],
    *args,
    message: Optional[str] = None,
    **kwargs,
) -> T:
    try:
        return fn(*args, **kwargs)
    except ValueError as exc:
        error_message(message or str(exc))


def interruptIf_not(condition: bool, message: str) -> None:
    interruptIf_condition(not condition, message)


def interruptIf_notHostValue(host: str) -> None:
    interruptIf_condition(not is_host(host), "Host value must not contain '@'.")


def interruptIf_notTargetValue(target: str) -> None:
    interruptIf_condition(not is_target(target), "Target value must be in format user@host.")


def interruptIf_notHostOrTargetValue(value: str) -> None:
    interruptIf_condition(not (is_host(value) or is_target(value)), "Value must be either host or user@host.")


def interruptIf_aliasMissing(alias: str, alias_kind_value: Optional[str]) -> str:
    return interruptIf_none(alias_kind_value, f"Alias '{alias}' was not found.")


def interruptIf_notConfirmed(confirmed: bool) -> None:
    interruptIf_condition(not confirmed, "Operation cancelled.", error_type="Info", exit_code=0)


def interruptIf_invalidImportMergeOptions(replace: bool, overwrite: bool, skip_existing: bool) -> None:
    interruptIf_condition(
        replace and (overwrite or skip_existing),
        "Use either --replace OR merge options (--overwrite/--skip-existing).",
    )
    interruptIf_condition(
        overwrite and skip_existing,
        "Use only one merge strategy: --overwrite or --skip-existing.",
    )
