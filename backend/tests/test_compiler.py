import pytest

from backend.compiler import (
    AmbiguousReferenceError,
    CompileError,
    TaskCompiler,
    extract_parameters,
    parse_expression,
)


def test_compositional_operators_are_parsed_recursively() -> None:
    expression = parse_expression(
        "SEQUENCE(AND(wifi enabled, NOT(dnd enabled)), IF(file exists, open it, search hero))"
    )
    assert expression.operator == "SEQUENCE"
    assert expression.arguments[0].operator == "AND"
    assert expression.arguments[0].arguments[1].operator == "NOT"
    assert expression.arguments[1].operator == "IF"
    assert expression.as_dict()["arguments"][1]["arguments"][2]["text"] == "search hero"


def test_operator_arity_and_balancing_are_validated() -> None:
    with pytest.raises(CompileError, match="NOT expects"):
        parse_expression("NOT(one, two)")
    with pytest.raises(CompileError, match="Unbalanced"):
        parse_expression("SEQUENCE(one, AND(two, three)")


def test_parameter_extraction() -> None:
    result = extract_parameters('connect to "StudioNet" then set brightness 60% for 10 minutes at /home/agentos')
    assert result["quoted"] == ["StudioNet"]
    assert result["percentages"] == [60]
    assert result["durations"] == [{"value": 10, "unit": "minutes"}]
    assert result["paths"] == ["/home/agentos"]


def test_compiler_emits_semantic_milestones_not_actions() -> None:
    compiled = TaskCompiler().compile(
        'First take the clipboard content, make a new text file, paste it there, then save it with name "hero".'
    )
    assert compiled.automaton is not None
    assert [item.id for item in compiled.automaton.milestones] == [
        "clipboard-captured",
        "document-created",
        "content-pasted",
        "document-saved",
    ]
    assert compiled.automaton.milestones[-1].goals[0].predicate.value == "hero"
    serialized = str(compiled.automaton.model_dump())
    assert "clipboard.read" not in serialized
    assert "editor.save" not in serialized


def test_find_and_append_compiles_to_five_ordered_semantic_milestones() -> None:
    compiled = TaskCompiler().compile(
        "Find the file named hero, open it, add the current clipboard content at the end, and save it."
    )

    assert compiled.automaton is not None
    assert compiled.automaton.id == "compiled-find-append"
    assert [item.id for item in compiled.automaton.milestones] == [
        "file-found",
        "file-opened",
        "clipboard-captured",
        "content-appended",
        "document-saved",
    ]
    assert compiled.automaton.milestones[0].goals[0].predicate.field == "filesystem.found_name"
    assert compiled.automaton.milestones[0].goals[0].predicate.value == "hero"
    serialized = str(compiled.automaton.model_dump())
    assert "filesystem.search" not in serialized
    assert "editor.insert" not in serialized


def test_clipboard_report_compiles_to_ten_semantic_milestones() -> None:
    compiled = TaskCompiler().compile(
        "Read the clipboard, create a Reports folder, make a new document, paste the clipboard, "
        "save it as hero, close the editor, open Files, find hero, move it into Reports, and star it."
    )

    assert compiled.automaton is not None
    assert compiled.automaton.id == "compiled-clipboard-report"
    assert len(compiled.automaton.milestones) == 10
    assert compiled.automaton.constraints == {
        "filename": "hero",
        "folder": "Reports",
        "save_parent": "Documents",
    }
    serialized = str(compiled.automaton.model_dump())
    assert "clipboard.read_current" not in serialized
    assert "'action':" not in serialized


def test_recovery_workflow_compiles_failure_constraints_not_an_action_route() -> None:
    compiled = TaskCompiler().compile(
        "Connect to StudioNet, verify internet access, open the browser, visit the project page, "
        "copy its address, make a note from it, save it as online, move it to Research, and star it."
    )

    assert compiled.automaton is not None
    assert compiled.automaton.id == "compiled-recovery-online-note"
    assert len(compiled.automaton.milestones) == 10
    assert compiled.automaton.constraints["inject_failures"] == {"wifi.connect": 1}
    assert compiled.automaton.constraints["stochastic_failures"] == {"wifi.connect": 0.2}
    serialized_milestones = str(
        [milestone.model_dump() for milestone in compiled.automaton.milestones]
    )
    assert "wifi.connect" not in serialized_milestones
    assert "'action':" not in serialized_milestones


def test_cross_workspace_writing_compiles_to_ten_semantic_milestones() -> None:
    compiled = TaskCompiler().compile(
        "Open workspace two, launch Files, find hero, copy its contents, switch to workspace one, "
        "open the editor, create a document, paste it, save it as hero-copy, and close it."
    )

    assert compiled.automaton is not None
    assert compiled.automaton.id == "compiled-cross-workspace-writing"
    assert len(compiled.automaton.milestones) == 10
    assert compiled.automaton.constraints == {
        "filename": "hero-copy",
        "source": "hero",
        "save_parent": "Documents",
    }
    serialized_milestones = str(
        [milestone.model_dump() for milestone in compiled.automaton.milestones]
    )
    assert "workspace.switch" not in serialized_milestones
    assert "filesystem.read" not in serialized_milestones
    assert "'action':" not in serialized_milestones


def test_settings_evidence_compiles_to_ten_semantic_milestones() -> None:
    compiled = TaskCompiler().compile(
        "Turn on dark mode, set brightness to 60%, enable Do Not Disturb, take a screenshot, "
        "save it as setup, open Files, find setup, move it to Pictures, star it, and return to the desktop."
    )

    assert compiled.automaton is not None
    assert compiled.automaton.id == "compiled-settings-evidence"
    assert len(compiled.automaton.milestones) == 10
    assert compiled.automaton.constraints == {
        "filename": "setup",
        "folder": "Pictures",
        "brightness": 60,
        "save_parent": "Pictures",
    }
    assert compiled.automaton.milestones[1].goals[0].predicate.value == 60
    serialized_milestones = str(
        [milestone.model_dump() for milestone in compiled.automaton.milestones]
    )
    assert "display.set_theme" not in serialized_milestones
    assert "capture.fullscreen" not in serialized_milestones
    assert "'action':" not in serialized_milestones


def test_ambiguous_reference_is_structured() -> None:
    with pytest.raises(AmbiguousReferenceError) as caught:
        TaskCompiler().compile("open that file", {"that file": ["file:1", "file:2"]})
    assert caught.value.reference == "that file"
    assert caught.value.candidates == ["file:1", "file:2"]
