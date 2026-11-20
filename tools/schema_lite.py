#!/usr/bin/env python3
"""Minimal dependency-free JSON Schema subset validator.

Enforces exactly the keyword subset the Project Map schemas use, so the
schemas stop being decorative (audit D4) without adding a runtime
dependency. Supported keywords:

    type, enum, pattern, required, properties, items,
    additionalProperties (bool or schema), minItems, maxItems,
    $ref (local "#/$defs/..."), plus ignored $schema/$id/title/description.

Anything else in a schema is ignored (never crashes). Errors are returned
as a list of human-readable strings with JSON-path style locations.
"""
from __future__ import annotations

import re
from typing import Any

_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "null": type(None),
}

_IGNORED_KEYS = {"$schema", "$id", "title", "description", "definitions"}


def _type_ok(value: Any, expected: str) -> bool:
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected in _TYPES:
        cls = _TYPES[expected]
        if cls is bool:
            return isinstance(value, bool)
        return isinstance(value, cls)
    return True  # unknown type keyword: do not reject


def validate(instance: Any, schema: dict, root: dict | None = None, path: str = "$") -> list[str]:
    """Return a list of schema-violation error strings (empty list = valid)."""
    if root is None:
        root = schema
    errors: list[str] = []
    if not isinstance(schema, dict):
        return errors

    if "$ref" in schema:
        ref = schema["$ref"]
        if isinstance(ref, str) and ref.startswith("#/"):
            target: Any = root
            ok = True
            for part in ref[2:].split("/"):
                if isinstance(target, dict) and part in target:
                    target = target[part]
                else:
                    ok = False
                    break
            if ok:
                return validate(instance, target, root, path)
            errors.append(f"{path}: unresolvable $ref '{ref}'")
            return errors
        errors.append(f"{path}: unsupported $ref '{ref}' (only local '#/$defs/...' refs)")
        return errors

    expected_type = schema.get("type")
    if isinstance(expected_type, str) and not _type_ok(instance, expected_type):
        errors.append(f"{path}: expected {expected_type}, got {type(instance).__name__}")
        return errors  # further checks would cascade
    if isinstance(expected_type, list) and not any(_type_ok(instance, t) for t in expected_type):
        errors.append(f"{path}: expected one of {expected_type}, got {type(instance).__name__}")
        return errors

    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: value {instance!r} not in enum {schema['enum']!r}")

    if "pattern" in schema and isinstance(instance, str):
        try:
            # JSON Schema patterns use ECMA-262 semantics, where `$` matches
            # ONLY at the very end of the string. Python's `$` also matches
            # just before a trailing newline, making patterns like
            # `^[a-z0-9._-]*$` accept "evil-id\n" (re-audit finding L1).
            # Re-anchor a trailing `$` to Python's true end-of-string `\Z`.
            pattern = schema["pattern"]
            if pattern.endswith("$") and not pattern.endswith("\\$") and not pattern.endswith(r"\Z"):
                pattern = pattern[:-1] + r"\Z"
            if re.search(pattern, instance) is None:
                errors.append(f"{path}: {instance!r} does not match pattern {schema['pattern']!r}")
        except re.error as exc:
            errors.append(f"{path}: invalid pattern in schema ({exc})")

    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{path}: missing required field '{key}'")
        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        for key, value in instance.items():
            if key in properties:
                errors.extend(validate(value, properties[key], root, f"{path}.{key}"))
            elif isinstance(additional, dict):
                errors.extend(validate(value, additional, root, f"{path}.{key}"))
            elif additional is False:
                errors.append(f"{path}: unexpected field '{key}'")

    if isinstance(instance, list):
        items = schema.get("items")
        min_items = schema.get("minItems")
        max_items = schema.get("maxItems")
        if min_items is not None and len(instance) < min_items:
            errors.append(f"{path}: expected at least {min_items} items, got {len(instance)}")
        if max_items is not None and len(instance) > max_items:
            errors.append(f"{path}: expected at most {max_items} items, got {len(instance)}")
        if isinstance(items, dict):
            for index, element in enumerate(instance):
                errors.extend(validate(element, items, root, f"{path}[{index}]"))

    return errors
