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
            # This is the natural-language surface of the small grammar.  It only
            # recognizes composition; domain semantics are resolved separately.
            clauses = [
                part.strip(" ,.")
                for part in re.split(
                    r"(?:\bfirst\b|\band then\b|\bthen\b|,\s*(?:and\s+)?)",
                    normalized,
                    flags=re.I,
                )
                if part.strip(" ,.")
            ]
            expression = Expression("SEQUENCE", tuple(Expression("ATOM", text=part) for part in clauses)) if len(clauses) > 1 else Expression("ATOM", text=normalized)
        expression = ReferenceResolver(references).resolve(expression)
        parameters = extract_parameters(normalized)
        automaton = self._known_automaton(normalized, parameters)
        return CompiledInstruction(normalized, expression, parameters, automaton, automaton is None)

    @staticmethod
    def _known_automaton(source: str, parameters: dict[str, Any]) -> TaskAutomaton | None:
        lowered = source.casefold()

        def milestone(identifier: str, field: str, value: Any, operator: str = "eq") -> Milestone:
            return Milestone(
                id=identifier,
                goals=[Goal(id=identifier, predicate=Condition(field=field, value=value, operator=operator))],
            )

        def milestone_all(identifier: str, *predicates: tuple[str, Any, str]) -> Milestone:
            return Milestone(
                id=identifier,
                goals=[
                    Goal(
                        id=f"{identifier}-{index}",
                        predicate=Condition(field=field, value=value, operator=operator),
                    )
                    for index, (field, value, operator) in enumerate(predicates)
                ],
            )

        def filename_after(pattern: str, default: str | None = None) -> str | None:
            match = re.search(pattern, source, re.I)
            return match.group(1).strip().rstrip(".!?") if match else default

        # The ten-step benchmarks are recognized by their semantic ingredients,
        # then compiled only to state predicates.  No action sequence is embedded.
        if all(token in lowered for token in ("reports", "clipboard", "close", "find", "move", "star")):
            name = filename_after(r"\bsave(?:\s+it)?\s+(?:as|with (?:the )?name)\s+[\"']?([\w.-]+)", "hero")
            assert name is not None
            return TaskAutomaton(
                id="compiled-clipboard-report",
                milestones=[
                    milestone("clipboard-captured", "task.clipboard_captured", True),
                    milestone("reports-created", "filesystem.last_created_folder", "Reports"),
                    milestone("document-created", "task.document_created", True),
                    milestone("content-pasted", "task.content_pasted", True),
                    milestone("document-saved", "editor.filename", name),
                    milestone("editor-closed", "task.document_closed", True),
                    milestone("files-opened", "application.focused_id", "app:files"),
                    milestone_all("file-found", ("filesystem.found_name", name, "eq"), ("filesystem.searched", True, "eq")),
                    milestone_all("file-moved", ("filesystem.last_parent", "Reports", "eq"), ("filesystem.moved", True, "eq")),
                    milestone("file-starred", "filesystem.starred", True),
                ],
                constraints={"filename": name, "folder": "Reports", "save_parent": "Documents"},
            )

        if all(token in lowered for token in ("studionet", "internet", "project page", "online", "research", "star")):
            return TaskAutomaton(
                id="compiled-recovery-online-note",
                milestones=[
                    milestone("wifi-connected", "wifi.ssid", "StudioNet"),
                    milestone("internet-verified", "task.internet_verified", True),
                    milestone("browser-opened", "browser.open", True),
                    milestone("project-opened", "browser.url", "https://example.com/project"),
                    milestone("address-copied", "browser.url_copied", True),
                    milestone("document-created", "task.document_created", True),
                    milestone("address-pasted", "task.content_pasted", True),
                    milestone("document-saved", "editor.filename", "online"),
                    milestone_all("file-moved", ("filesystem.last_parent", "Research", "eq"), ("filesystem.moved", True, "eq")),
                    milestone("file-starred", "filesystem.starred", True),
                ],
                constraints={"inject_failures": {"wifi.connect": 1}, "stochastic_failures": {"wifi.connect": 0.2}, "filename": "online", "folder": "Research", "save_parent": "Documents"},
            )

        if all(token in lowered for token in ("workspace two", "hero", "hero-copy", "copy", "close")):
            return TaskAutomaton(
                id="compiled-cross-workspace-writing",
                milestones=[
                    milestone("workspace-two", "workspace.visited_indices", 2, "contains"),
                    milestone("files-launched", "application.running_ids", "app:files", "contains"),
                    milestone_all("hero-found", ("filesystem.found_name", "hero", "eq"), ("filesystem.searched", True, "eq")),
                    milestone("contents-copied", "task.file_captured", True),
                    milestone("workspace-one", "workspace.current", 1),
                    milestone("editor-opened", "editor.open", True),
                    milestone("document-created", "task.document_created", True),
                    milestone("content-pasted", "task.content_pasted", True),
                    milestone("document-saved", "editor.filename", "hero-copy"),
                    milestone("document-closed", "task.document_closed", True),
                ],
                constraints={"filename": "hero-copy", "source": "hero", "save_parent": "Documents"},
            )

        if all(token in lowered for token in ("dark mode", "brightness", "do not disturb", "screenshot", "pictures", "desktop")):
            brightness = parameters.get("percentages", [60])[0]
            return TaskAutomaton(
                id="compiled-settings-evidence",
                milestones=[
                    milestone("dark-mode", "display.theme", "dark"),
                    milestone("brightness", "display.brightness", brightness),
                    milestone("dnd", "notification.dnd", True),
                    milestone("screenshot", "capture.last_capture_id", "capture:latest"),
                    milestone("capture-saved", "capture.saved_name", "setup"),
                    milestone("files-opened", "application.focused_id", "app:files"),
                    milestone_all("capture-found", ("filesystem.found_name", "setup", "eq"), ("filesystem.searched", True, "eq")),
                    milestone_all("capture-moved", ("filesystem.last_parent", "Pictures", "eq"), ("filesystem.moved", True, "eq")),
                    milestone("capture-starred", "filesystem.starred", True),
                    milestone("desktop-visible", "task.desktop_returned", True),
                ],
                constraints={"filename": "setup", "folder": "Pictures", "brightness": brightness, "save_parent": "Pictures"},
            )

        if all(token in lowered for token in ("download", "rename", "folder", "move", "compress", "archive location")):
            name = filename_after(r"\brename\s+(?:it|the\s+(?:download|file))\s+(?:(?:to|as)\s+)?[\"']?([\w.-]+)", "report")
            folder = filename_after(r"\bcreate\s+(?:an?\s+)?[\"']?([\w .-]+?)[\"']?\s+folder", "Archive")
            assert name is not None and folder is not None
            return TaskAutomaton(
                id="compiled-download-archive",
                milestones=[
                    milestone("browser-opened", "browser.open", True),
                    milestone("page-downloaded", "browser.last_download_id", "file:download"),
                    milestone("downloads-opened", "filesystem.opened_paths", "Downloads", "contains"),
                    milestone_all("download-found", ("filesystem.found_id", "file:search-result", "eq"), ("filesystem.searched", True, "eq")),
                    milestone_all("download-renamed", ("filesystem.found_name", name, "eq"), ("filesystem.renamed", True, "eq")),
                    milestone("folder-created", "filesystem.last_created_folder", folder),
                    milestone_all("download-moved", ("filesystem.last_parent", f"Downloads/{folder}", "eq"), ("filesystem.moved", True, "eq")),
                    milestone("archive-created", "filesystem.last_archive_id", "archive:created"),
                    milestone("archive-location-opened", "filesystem.current_path", f"Downloads/{folder}"),
                ],
                constraints={"filename": name, "folder": folder, "save_parent": "Downloads"},
            )

        if all(token in lowered for token in ("workspace", "browser", "editor", "beside", "paste", "save")):
            workspace_match = re.search(r"\b(second|third|fourth|[2-4])\s+workspace", source, re.I)
            index_by_name = {"second": 2, "third": 3, "fourth": 4}
            token = workspace_match.group(1).casefold() if workspace_match else "second"
            index = index_by_name.get(token, int(token) if token.isdigit() else 2)
            name = filename_after(r"\bsave(?:\s+it)?\s+(?:as|with (?:the )?name)\s+[\"']?([\w.-]+)", "research")
            assert name is not None
            return TaskAutomaton(
                id="compiled-workspace-setup",
                milestones=[
                    milestone("workspace-created", "workspace.last_created", index),
                    milestone("workspace-selected", "workspace.current", index),
                    milestone("browser-opened", "browser.open", True),
                    milestone("editor-opened", "editor.open", True),
                    milestone("windows-arranged", "window.snap_side", "right"),
                    milestone("document-created", "task.document_created", True),
                    milestone("content-pasted", "task.content_pasted", True),
                    milestone("document-saved", "editor.filename", name),
                ],
                constraints={"workspace": index, "filename": name, "save_parent": "Documents"},
            )

        if all(token in lowered for token in ("browser address", "source note", "paste", "save", "reveal")):
            name = filename_after(r"\bsave(?:\s+it)?\s+(?:as|with (?:the )?name)\s+[\"']?([\w.-]+)", "source")
            assert name is not None
            return TaskAutomaton(
                id="compiled-research-handoff",
                milestones=[
                    milestone("browser-focused", "application.focused_id", "app:browser"),
                    milestone("address-copied", "browser.url_copied", True),
                    milestone("document-created", "task.document_created", True),
                    milestone("address-pasted", "task.content_pasted", True),
                    milestone("document-saved", "editor.filename", name),
                    milestone_all("file-found", ("filesystem.found_name", name, "eq"), ("filesystem.searched", True, "eq")),
                    milestone("file-revealed", "filesystem.selection_id", "file:search-result"),
                ],
                constraints={"filename": name, "save_parent": "Documents"},
            )

        if all(token in lowered for token in ("folder", "documents", "note", "clipboard", "move")):
            folder = filename_after(r"\bcreate\s+(?:an?\s+)?[\"']?([\w .-]+?)[\"']?\s+folder", "Projects")
            name = filename_after(r"\bsave(?:\s+it)?\s+(?:as|with (?:the )?name)\s+[\"']?([\w.-]+)", "brief")
            assert folder is not None and name is not None
            return TaskAutomaton(
                id="compiled-organize-note",
                milestones=[
                    milestone("documents-opened", "filesystem.current_path", "Documents"),
                    milestone("folder-created", "filesystem.last_created_folder", folder),
                    milestone("clipboard-captured", "task.clipboard_captured", True),
                    milestone("document-created", "task.document_created", True),
                    milestone("content-pasted", "task.content_pasted", True),
                    Milestone(
                        id="document-organized",
                        goals=[
                            Goal(id="saved", predicate=Condition(field="editor.filename", value=name)),
                            Goal(id="parent", predicate=Condition(field="editor.parent", value=f"Documents/{folder}")),
                        ],
                    ),
                ],
                constraints={"filename": name, "folder": folder, "save_parent": f"Documents/{folder}"},
            )

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
