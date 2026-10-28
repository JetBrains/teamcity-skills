"""Resolve and inspect native Maven arguments without publishing parameter data."""

import re
import shlex


REFERENCE = re.compile(r"%([^%\r\n]+)%")
UNRESOLVED = "%unresolved-maven-arguments%"


def resolve_maven_arguments(value, parameters, environment):
    """Expand stored pipeline references, returning a fixed marker on failure."""
    values = {**{f"env.{key}": item for key, item in environment.items()}, **parameters}
    remaining = 100

    def expand(text, active):
        if not isinstance(text, str):
            raise ValueError

        def replace(match):
            nonlocal remaining
            remaining -= 1
            name = match[1]
            if remaining < 0 or name in active or name not in values:
                raise ValueError
            return expand(values[name], active | {name})

        return REFERENCE.sub(replace, text)

    try:
        return expand(value, set())
    except ValueError:
        return UNRESOLVED


def maven_arguments_match(value, pattern):
    """Match forbidden options after unquoting; inconclusive input fails closed.

    argLine has a second quoting layer for the forked JVM. Inspect its arguments
    separately so a flag inside a JVM property's value is not a standalone flag.
    """
    if not isinstance(value, str) or REFERENCE.search(value):
        return True
    try:
        arguments = iter(shlex.split(value))
        for argument in arguments:
            if argument == "-D":
                argument += next(arguments)
                if argument == "-D":
                    return True
            if pattern.match(argument):
                return True
            if argument.startswith("-DargLine="):
                if any(pattern.match("-DargLine=" + item)
                       for item in shlex.split(argument[len("-DargLine="):])):
                    return True
    except (ValueError, StopIteration):
        return True
    return False
