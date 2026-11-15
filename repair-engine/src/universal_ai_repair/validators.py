import ast
from .errors import ValidationFailure
from .models import Diagnostic

def validate_python(source: str, *, max_bytes: int = 1_000_000) -> list[Diagnostic]:
    if len(source.encode("utf-8")) > max_bytes:
        raise ValidationFailure(f"Candidate exceeds the {max_bytes}-byte size limit.")
    if "\x00" in source:
        raise ValidationFailure("Candidate contains a NUL byte.")
    try:
        tree = ast.parse(source)
        compile(tree, "<repair-candidate>", "exec")
    except (SyntaxError, ValueError) as exc:
        raise ValidationFailure(f"Python syntax validation failed: {exc}") from exc
    diagnostics: list[Diagnostic] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and any(alias.name == "*" for alias in node.names):
            diagnostics.append(Diagnostic("warning", "PY_WILDCARD_IMPORT",
                "Wildcard imports make dependencies harder to audit.", getattr(node, "lineno", None)))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and len(node.body) > 50:
            diagnostics.append(Diagnostic("warning", "PY_LONG_FUNCTION",
                f"Function '{node.name}' has more than 50 top-level statements.", node.lineno))
    return diagnostics
