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


def test_ambiguous_reference_is_structured() -> None:
    with pytest.raises(AmbiguousReferenceError) as caught:
        TaskCompiler().compile("open that file", {"that file": ["file:1", "file:2"]})
    assert caught.value.reference == "that file"
    assert caught.value.candidates == ["file:1", "file:2"]
