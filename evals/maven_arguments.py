"""Resolve and inspect native Maven arguments without publishing parameter data."""

import re


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


def _split_arguments(value, *, unescape_quotes=False):
    """Honor quotes without treating backslashes as shell escape characters.

    Remove quote escapes only at the runner layer. Surefire's argLine parser
    keeps backslashes, including those before quotes, in the JVM arguments.
    """
    arguments, current, quote, started = [], [], None, False
    for char in value:
        if char in "\"'" and (quote is None or char == quote):
            if current and current[-1] == "\\":
                if unescape_quotes:
                    current.pop()
                current.append(char)
            else:
                quote = None if quote else char
            started = True
        elif char.isspace() and quote is None:
            if started:
                arguments.append("".join(current))
                current, started = [], False
        else:
            current.append(char)
            started = True
    if quote is not None:
        raise ValueError
    if started:
        arguments.append("".join(current))
    return arguments


def maven_arguments_match(value, pattern):
    """Match forbidden options after unquoting; inconclusive input fails closed.

    argLine has a second quoting layer for the forked JVM. Inspect its arguments
    separately so a flag inside a JVM property's value is not a standalone flag.
    """
    if not isinstance(value, str) or REFERENCE.search(value):
        return True
    try:
        arguments = iter(_split_arguments(value, unescape_quotes=True))
        for argument in arguments:
            option, separator, definition = argument.partition("=")
            if argument == "-D" or option in ("--define", "-define"):
                definition = definition if separator else next(arguments)
                if not definition:
                    return True
                argument = "-D" + definition
            if argument.startswith("-DargLine="):
                if any(pattern.match("-DargLine=" + item)
                       for item in _split_arguments(argument[len("-DargLine="):])):
                    return True
            elif pattern.match(argument):
                return True
    except (ValueError, StopIteration):
        return True
    return False
