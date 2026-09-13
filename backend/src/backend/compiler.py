from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

from .environment import Condition, Goal, Milestone, TaskAutomaton


class CompileError(ValueError):
    pass


class AmbiguousReferenceError(CompileError):
    def __init__(self, reference: str, candidates: list[str]) -> None:
        self.reference = reference
        self.candidates = candidates
        super().__init__(f"Ambiguous reference {reference!r}: {', '.join(candidates)}")


@dataclass(frozen=True)
class Expression:
    operator: Literal["ATOM", "SEQUENCE", "AND", "OR", "NOT", "UNTIL", "IF", "PRESERVE", "CONFIRM_BEFORE"]
    arguments: tuple["Expression", ...] = ()
    text: str | None = None

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"operator": self.operator}
        if self.text is not None:
            result["text"] = self.text
        if self.arguments:
            result["arguments"] = [item.as_dict() for item in self.arguments]
        return result


@dataclass(frozen=True)
class CompiledInstruction:
    source: str
    expression: Expression
    parameters: dict[str, Any]
    automaton: TaskAutomaton | None
    requires_fallback: bool = False


OPERATORS: dict[str, tuple[int, int | None]] = {
    "SEQUENCE": (2, None),
    "AND": (2, None),
    "OR": (2, None),
    "NOT": (1, 1),
    "UNTIL": (2, 2),
    "IF": (2, 3),
    "PRESERVE": (1, 1),
    "CONFIRM_BEFORE": (1, 1),
}
REFERENCES = {"it", "there", "that file", "current item", "previous result"}


def _split_top_level(value: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    quote: str | None = None
    start = 0
    for index, character in enumerate(value):
        if quote:
            if character == quote and (index == 0 or value[index - 1] != "\\"):
                quote = None
        elif character in {'"', "'"}:
            quote = character
        elif character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            if depth < 0:
                raise CompileError("Unbalanced closing parenthesis")
        elif character == "," and depth == 0:
            parts.append(value[start:index].strip())
            start = index + 1
    if quote or depth:
        raise CompileError("Unbalanced expression")
    parts.append(value[start:].strip())
    return parts


def parse_expression(source: str) -> Expression:
    value = source.strip()
    if not value:
        raise CompileError("Expression cannot be empty")
    match = re.fullmatch(r"([A-Z_]+)\((.*)\)", value, flags=re.DOTALL)
    if not match or match.group(1) not in OPERATORS:
        return Expression(operator="ATOM", text=value)
    operator = match.group(1)
    parts = _split_top_level(match.group(2))
    minimum, maximum = OPERATORS[operator]
    if len(parts) < minimum or (maximum is not None and len(parts) > maximum):
        expected = str(minimum) if minimum == maximum else f"{minimum}..{maximum or 'n'}"
        raise CompileError(f"{operator} expects {expected} arguments")
    return Expression(operator=operator, arguments=tuple(parse_expression(part) for part in parts))  # type: ignore[arg-type]


def extract_parameters(source: str) -> dict[str, Any]:
    quoted = [left or right for left, right in re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"|\'([^\'\\]*(?:\\.[^\'\\]*)*)\'', source)]
    paths = re.findall(r"(?<!\w)(/(?:[^\s,()]+))", source)
    percentages = [int(value) for value in re.findall(r"\b(100|[1-9]?\d)\s*%", source)]
    durations = [
        {"value": int(value), "unit": unit.lower()}
        for value, unit in re.findall(r"\b(\d+)\s*(seconds?|minutes?|hours?|days?)\b", source, re.I)
    ]
    network = re.search(r"\bconnect(?:\s+to)?\s+(?:wifi\s+)?[\"']?([^\"',]+?)[\"']?(?:\s+then|\s*$)", source, re.I)
    app = re.search(r"\b(?:launch|open|focus|quit)\s+(?:the\s+)?([A-Za-z][\w .-]*?)(?:\s+app)?(?:\s+then|[,.;]|$)", source, re.I)
    result: dict[str, Any] = {}
    if quoted:
        result["quoted"] = quoted
    if paths:
        result["paths"] = paths
    if percentages:
        result["percentages"] = percentages
    if durations:
        result["durations"] = durations
    if network:
        result["ssid"] = network.group(1).strip()
    if app:
        result["app_name"] = app.group(1).strip()
    return result


class ReferenceResolver:
    def __init__(self, candidates: dict[str, list[str]] | None = None) -> None:
        self.candidates = candidates or {}

    def resolve(self, expression: Expression) -> Expression:
        if expression.operator == "ATOM" and expression.text:
            text = expression.text
            for reference in REFERENCES:
                if re.search(rf"\b{re.escape(reference)}\b", text, re.I):
                    matches = self.candidates.get(reference, [])
                    if len(matches) > 1:
                        raise AmbiguousReferenceError(reference, matches)
                    if len(matches) == 1:
                        text = re.sub(rf"\b{re.escape(reference)}\b", matches[0], text, flags=re.I)
            return Expression(operator="ATOM", text=text)
        return Expression(expression.operator, tuple(self.resolve(item) for item in expression.arguments), expression.text)


class TaskCompiler:
    """Compiles constrained language to predicates and ordered milestones, never actions."""

    def compile(self, source: str, references: dict[str, list[str]] | None = None) -> CompiledInstruction:
        normalized = " ".join(source.strip().split())
        if not normalized:
            raise CompileError("Instruction cannot be empty")
        if re.match(r"^[A-Z_]+\(", normalized):
            expression = parse_expression(normalized)
        else:
            clauses = [part.strip(" ,.") for part in re.split(r"\b(?:and then|then|first)\b", normalized, flags=re.I) if part.strip(" ,.")]
            expression = Expression("SEQUENCE", tuple(Expression("ATOM", text=part) for part in clauses)) if len(clauses) > 1 else Expression("ATOM", text=normalized)
        expression = ReferenceResolver(references).resolve(expression)
        parameters = extract_parameters(normalized)
        automaton = self._known_automaton(normalized, parameters)
        return CompiledInstruction(normalized, expression, parameters, automaton, automaton is None)

    @staticmethod
    def _known_automaton(source: str, parameters: dict[str, Any]) -> TaskAutomaton | None:
        lowered = source.casefold()
        if "wifi" in lowered or lowered.startswith("connect"):
            if "disconnect" in lowered:
                predicate = Condition(field="wifi.connected", value=False)
                goal_id = "wifi-disconnected"
            elif re.search(r"\b(?:off|disable)\b", lowered):
                predicate = Condition(field="wifi.enabled", value=False)
                goal_id = "wifi-disabled"
            elif "ssid" in parameters:
                predicate = Condition(field="wifi.ssid", value=parameters["ssid"])
                goal_id = "wifi-connected"
            else:
                predicate = Condition(field="wifi.enabled", value=True)
                goal_id = "wifi-enabled"
            return TaskAutomaton(
                id=f"compiled-{goal_id}",
                milestones=[Milestone(id=goal_id, goals=[Goal(id=goal_id, predicate=predicate)])],
            )
        if (
            "clipboard" in lowered
            and re.search(r"\bfind\b", lowered)
            and re.search(r"\b(?:append|add)\b", lowered)
            and "save" in lowered
        ):
            match = re.search(r"\bfile\s+(?:named|called)\s+[\"']?([\w.-]+)[\"']?", source, re.I)
            name = match.group(1) if match else None
            if not name:
                raise CompileError("A filename is required")
            return TaskAutomaton(
                id="compiled-find-append",
                milestones=[
                    Milestone(
                        id="file-found",
                        goals=[Goal(id="found", predicate=Condition(field="filesystem.found_name", value=name))],
                    ),
                    Milestone(
                        id="file-opened",
                        goals=[Goal(id="opened", predicate=Condition(field="editor.active_file_name", value=name))],
                    ),
                    Milestone(
                        id="clipboard-captured",
                        goals=[Goal(id="captured", predicate=Condition(field="task.clipboard_captured", value=True))],
                    ),
                    Milestone(
                        id="content-appended",
                        goals=[Goal(id="appended", predicate=Condition(field="editor.clipboard_appended", value=True))],
                    ),
                    Milestone(
                        id="document-saved",
                        goals=[Goal(id="saved", predicate=Condition(field="editor.dirty", value=False))],
                    ),
                ],
            )
        if "clipboard" in lowered and re.search(r"\b(?:file|document|note)\b", lowered) and "save" in lowered:
            names = parameters.get("quoted", [])
            name = names[-1] if names else None
            if not name:
                match = re.search(r"\bsave(?:\s+it)?\s+(?:as|with (?:the )?name)\s+([\w.-]+)", source, re.I)
                name = match.group(1) if match else None
            if not name:
                raise CompileError("A filename is required")
            return TaskAutomaton(
                id="compiled-clipboard-file",
                milestones=[
                    Milestone(id="clipboard-captured", goals=[Goal(id="captured", predicate=Condition(field="task.clipboard_captured", value=True))]),
                    Milestone(id="document-created", goals=[Goal(id="created", predicate=Condition(field="editor.document_open", value=True))]),
                    Milestone(id="content-pasted", goals=[Goal(id="pasted", predicate=Condition(field="editor.content_matches_clipboard", value=True))]),
                    Milestone(id="document-saved", goals=[Goal(id="saved", predicate=Condition(field="editor.filename", value=name))]),
                ],
            )
        return None
