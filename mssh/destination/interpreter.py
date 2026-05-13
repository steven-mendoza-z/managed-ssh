from mssh.destination.solve import solve_host, solve_target


def has_user(destination: str) -> bool:
    return "@" in destination


def destination_interpreter(destination: str) -> str:
    """
    Resolve a destination that can be:
    - alias
    - user@alias
    - user@host
    """
    if has_user(destination):
        user, host_or_alias = destination.split("@", 1)
        resolved_host = solve_host(host_or_alias)
        return f"{user}@{resolved_host}"

    resolved_target = solve_target(destination)
    if resolved_target != destination:
        return resolved_target

    return solve_host(destination)

