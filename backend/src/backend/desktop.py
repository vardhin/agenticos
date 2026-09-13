from __future__ import annotations

from collections.abc import Iterable
from copy import deepcopy
from typing import Any

from .environment import (
    ActionRegistry,
    ActionSpec,
    ArgumentSpec,
    BindingSpec,
    Condition,
    Effect,
    GeneratedSimulator,
    JsonValue,
    Latency,
    Risk,
)


ENVIRONMENT_VERSION = "agentos-desktop-v1"


def desktop_initial_fields() -> dict[str, JsonValue]:
    """A compact, factored observation with stable identifiers for every domain."""
    return {
        "system": {
            "session_active": True,
            "locked": False,
            "desktop_visible": True,
            "power_state": "running",
            "cancel_requested": False,
            "undo_available": False,
            "redo_available": False,
        },
        "task": {
            "id": None,
            "status": "idle",
            "progress": 0,
            "pending_confirmation": None,
            "last_failure": None,
            "clipboard_captured": False,
            "file_captured": False,
            "internet_verified": False,
            "document_created": False,
            "content_pasted": False,
            "document_saved": False,
            "document_closed": False,
            "desktop_returned": False,
        },
        "launcher": {"open": False, "query": "", "result_id": None, "pinned_app_ids": []},
        "application": {
            "ids": ["app:browser", "app:editor", "app:files", "app:settings", "app:software", "app:terminal"],
            "running_ids": [],
            "focused_id": "app:editor",
            "last_recent_id": None,
            "default_mime_type": None,
            "default_app_id": None,
        },
        "window": {
            "ids": ["window:browser", "window:editor", "window:files", "window:settings", "window:software", "window:terminal"],
            "focused_id": "window:editor",
            "open_ids": ["window:editor", "window:files"],
            "minimized_ids": [],
            "maximized_ids": [],
            "fullscreen_ids": [],
            "last_moved_id": None,
            "last_resized_id": None,
            "last_snapped_id": None,
            "snap_side": None,
            "x": 0,
            "y": 0,
            "width": 960,
            "height": 640,
        },
        "workspace": {
            "ids": ["workspace:1"],
            "current": 1,
            "last_created": 1,
            "last_renamed": None,
            "last_removed": None,
            "last_window_id": None,
            "last_window_index": None,
            "overview": False,
            "visited_indices": [1],
        },
        "clipboard": {
            "current": "https://agentos.dev/docs",
            "history": ["https://agentos.dev/docs"],
            "last_read_index": 0,
            "last_target_id": None,
            "last_resource_id": None,
            "pinned_indices": [],
        },
        "filesystem": {
            "ids": ["file:hero", "folder:documents", "folder:downloads", "folder:pictures", "folder:research"],
            "current_path": "/home/agentos",
            "opened_paths": ["/home/agentos"],
            "selection_id": None,
            "active_file_id": None,
            "found_id": None,
            "found_name": None,
            "last_created_id": None,
            "last_created_name": None,
            "last_created_folder": None,
            "last_created_parent": None,
            "last_parent": None,
            "last_operation": None,
            "searched": False,
            "renamed": False,
            "moved": False,
            "last_archive_id": None,
            "last_extracted_id": None,
            "starred_id": None,
            "starred": False,
            "sort_field": "name",
            "sort_direction": "ascending",
            "filter_type": None,
            "mounted_device_ids": [],
        },
        "editor": {
            "open": False,
            "document_open": False,
            "active_file_id": None,
            "active_file_name": None,
            "filename": None,
            "parent": "Documents",
            "content": "",
            "dirty": False,
            "content_matches_clipboard": False,
            "clipboard_appended": False,
            "selection": None,
            "find_query": None,
            "last_replacement": None,
        },
        "terminal": {
            "open": False,
            "running": False,
            "cwd": "/home/agentos",
            "output": [],
            "last_command": None,
            "last_read_range": None,
        },
        "browser": {
            "open": False,
            "tab_ids": ["tab:1"],
            "active_tab_id": "tab:1",
            "url": "https://example.com",
            "history_index": 0,
            "bookmarks": [],
            "last_download_id": None,
            "find_query": None,
        },
        "search": {"query": "", "domains": [], "filter": {}, "result_id": None},
        "notification": {
            "ids": ["notification:1", "notification:2"],
            "open_id": None,
            "dismissed_ids": [],
            "snoozed_id": None,
            "snooze_duration": None,
            "dnd": False,
        },
        "wifi": {
            "enabled": True,
            "connected": False,
            "ssid": None,
            "known_networks": ["StudioNet", "PineHouse"],
            "visible_ssids": ["StudioNet", "PineHouse", "Guest"],
            "internet_available": False,
            "latency_ms": None,
            "throughput_mbps": None,
        },
        "bluetooth": {
            "enabled": False,
            "device_ids": ["device:headphones", "device:keyboard"],
            "visible_ids": [],
            "paired_ids": [],
            "connected_ids": [],
        },
        "audio": {
            "volume": 72,
            "muted": False,
            "output_device_id": "device:speakers",
            "input_device_id": "device:microphone",
            "input_gain": 70,
            "last_test_succeeded": None,
        },
        "display": {
            "ids": ["display:primary"],
            "brightness": 84,
            "theme": "light",
            "night_light": False,
            "scale": 100,
            "last_configured_id": None,
            "resolution": "1920x1080",
            "position": "primary",
        },
        "settings": {"open": False, "section_id": None, "last_key": None, "last_value": None},
        "software": {
            "open": False,
            "query": "",
            "details_app_id": None,
            "installed_ids": ["app:browser", "app:editor", "app:files", "app:settings", "app:terminal"],
            "updated_ids": [],
        },
        "capture": {
            "active": False,
            "kind": None,
            "target": None,
            "last_capture_id": None,
            "saved_name": None,
            "saved_parent": None,
            "copied": False,
        },
        "share": {"last_node_id": None, "last_app_id": None, "last_link": None, "last_target": None},
    }


def _arg(type_: str, description: str = "", *, required: bool = True) -> ArgumentSpec:
    return ArgumentSpec(type=type_, description=description, required=required)  # type: ignore[arg-type]


def _condition(field: str, value: JsonValue = None, *, operator: str = "eq", arg: str | None = None) -> Condition:
    return Condition(field=field, value=value, operator=operator, value_from_argument=arg)  # type: ignore[arg-type]


def _effect(field: str, value: JsonValue = None, *, operation: str = "set", arg: str | None = None) -> Effect:
    return Effect(field=field, value=value, operation=operation, value_from_argument=arg)  # type: ignore[arg-type]


def _verified_effects(effects: Iterable[Effect]) -> list[Condition]:
    result: list[Condition] = []
    for item in effects:
        if item.operation == "add":
            result.append(_condition(item.field, operator="contains", arg=item.value_from_argument, value=item.value))
        elif item.operation == "remove":
            result.append(_condition(item.field, operator="not_contains", arg=item.value_from_argument, value=item.value))
        else:
            result.append(_condition(item.field, arg=item.value_from_argument, value=item.value))
    return result


def build_desktop_registry() -> ActionRegistry:
    registry = ActionRegistry(ENVIRONMENT_VERSION)
    binding = BindingSpec(simulator="generated", live="frontend-runtime")

    def add(
        action_id: str,
        description: str,
        *,
        arguments: dict[str, ArgumentSpec] | None = None,
        preconditions: list[Condition] | None = None,
        effects: list[Effect] | None = None,
        postconditions: list[Condition] | None = None,
        cost: float = 1,
        latency: Latency = Latency.LOW,
        risk: Risk = Risk.LOW,
        reversible: bool = True,
        confirmation: bool = False,
    ) -> None:
        action_effects = effects or []
        registry.register(ActionSpec(
            id=action_id,
            description=description,
            arguments=arguments or {},
            preconditions=preconditions or [],
            effects=action_effects,
            postconditions=postconditions if postconditions is not None else _verified_effects(action_effects),
            cost=cost,
            latency=latency,
            risk=risk,
            reversible=reversible,
            confirmation_required=confirmation,
            binding=binding,
        ))

    # System and shell.
    add(
        "system.begin_task",
        "Initialize scoped task progress without replacing desktop state",
        arguments={"task_id": _arg("string")},
        effects=[
            _effect("task.id", arg="task_id"),
            _effect("task.status", "running"),
            _effect("task.progress", 0),
            _effect("task.pending_confirmation", None),
            _effect("task.last_failure", None),
            _effect("task.clipboard_captured", False),
            _effect("task.internet_verified", False),
            _effect("task.document_created", False),
            _effect("task.content_pasted", False),
            _effect("task.document_saved", False),
            _effect("task.document_closed", False),
            _effect("task.desktop_returned", False),
            _effect("task.file_captured", False),
            _effect("filesystem.searched", False),
            _effect("filesystem.renamed", False),
            _effect("filesystem.moved", False),
            _effect("browser.url_copied", False),
        ],
    )
    add("system.observe", "Refresh the complete factored observation", postconditions=[_condition("system.session_active", operator="exists")])
    add("system.wait", "Wait between actions", arguments={"duration": _arg("number")}, effects=[_effect("task.status", "waiting")], latency=Latency.MEDIUM)
    add("system.cancel_task", "Cancel the running task", effects=[_effect("system.cancel_requested", True), _effect("task.status", "cancelled")])
    add("system.undo_last", "Undo the last reversible action", preconditions=[_condition("system.undo_available", True)], effects=[_effect("system.undo_available", False), _effect("system.redo_available", True)])
    add("system.redo_last", "Redo the last undone action", preconditions=[_condition("system.redo_available", True)], effects=[_effect("system.redo_available", False), _effect("system.undo_available", True)])
    add("system.show_desktop", "Reveal the desktop", effects=[_effect("system.desktop_visible", True), _effect("task.desktop_returned", True)])
    add("system.lock", "Lock the current session", effects=[_effect("system.locked", True)])
    for action_id, state in (("system.logout", "logged_out"), ("system.restart", "restarting"), ("system.shutdown", "shutdown")):
        add(action_id, f"Request {action_id.split('.')[1]}", effects=[_effect("system.power_state", state)], risk=Risk.HIGH, reversible=False, confirmation=True)

    add("launcher.open", "Open the launcher", effects=[_effect("launcher.open", True)])
    add("launcher.close", "Close the launcher", effects=[_effect("launcher.open", False)])
    add("launcher.search", "Search launcher content", arguments={"query": _arg("string")}, effects=[_effect("launcher.query", arg="query")])
    add("launcher.clear_query", "Clear launcher search", effects=[_effect("launcher.query", "")])
    add("launcher.open_result", "Open a launcher result", arguments={"result_id": _arg("string")}, effects=[_effect("launcher.result_id", arg="result_id"), _effect("launcher.open", False)])
    add("launcher.open_recent", "Open a recent item", arguments={"item_id": _arg("string")}, effects=[_effect("launcher.result_id", arg="item_id"), _effect("launcher.open", False)])
    add("launcher.pin", "Pin an application", arguments={"app_id": _arg("string")}, effects=[_effect("launcher.pinned_app_ids", operation="add", arg="app_id")])
    add("launcher.unpin", "Unpin an application", arguments={"app_id": _arg("string")}, effects=[_effect("launcher.pinned_app_ids", operation="remove", arg="app_id")])

    add("application.launch", "Launch an application", arguments={"app_id": _arg("string")}, effects=[_effect("application.running_ids", operation="add", arg="app_id"), _effect("application.focused_id", arg="app_id")])
    add("application.focus", "Focus a running application", arguments={"app_id": _arg("string")}, preconditions=[_condition("application.running_ids", operator="contains", arg="app_id")], effects=[_effect("application.focused_id", arg="app_id")])
    add("application.quit", "Quit an application", arguments={"app_id": _arg("string")}, preconditions=[_condition("application.running_ids", operator="contains", arg="app_id")], effects=[_effect("application.running_ids", operation="remove", arg="app_id")])
    add("application.force_quit", "Force quit an application", arguments={"app_id": _arg("string")}, effects=[_effect("application.running_ids", operation="remove", arg="app_id")], risk=Risk.HIGH, reversible=False, confirmation=True)
    add("application.open_recent", "Open an app recent item", arguments={"app_id": _arg("string"), "item_id": _arg("string")}, effects=[_effect("application.focused_id", arg="app_id"), _effect("application.last_recent_id", arg="item_id")])
    add("application.set_default", "Set a MIME default application", arguments={"mime_type": _arg("string"), "app_id": _arg("string")}, effects=[_effect("application.default_mime_type", arg="mime_type"), _effect("application.default_app_id", arg="app_id")])

    add("window.focus", "Focus a window", arguments={"window_id": _arg("string")}, preconditions=[_condition("window.open_ids", operator="contains", arg="window_id")], effects=[_effect("window.focused_id", arg="window_id")])
    add("window.minimize", "Minimize a window", arguments={"window_id": _arg("string")}, preconditions=[_condition("window.open_ids", operator="contains", arg="window_id")], effects=[_effect("window.minimized_ids", operation="add", arg="window_id")])
    add("window.restore", "Restore a minimized window", arguments={"window_id": _arg("string")}, effects=[_effect("window.minimized_ids", operation="remove", arg="window_id"), _effect("window.open_ids", operation="add", arg="window_id")])
    add("window.maximize", "Maximize a window", arguments={"window_id": _arg("string")}, effects=[_effect("window.maximized_ids", operation="add", arg="window_id")])
    add("window.unmaximize", "Unmaximize a window", arguments={"window_id": _arg("string")}, effects=[_effect("window.maximized_ids", operation="remove", arg="window_id")])
    add("window.close", "Close a window", arguments={"window_id": _arg("string")}, effects=[_effect("window.open_ids", operation="remove", arg="window_id")])
    add("window.move", "Move a window", arguments={"window_id": _arg("string"), "x": _arg("integer"), "y": _arg("integer")}, effects=[_effect("window.last_moved_id", arg="window_id"), _effect("window.x", arg="x"), _effect("window.y", arg="y")])
    add("window.resize", "Resize a window", arguments={"window_id": _arg("string"), "width": _arg("integer"), "height": _arg("integer")}, effects=[_effect("window.last_resized_id", arg="window_id"), _effect("window.width", arg="width"), _effect("window.height", arg="height")])
    add("window.snap", "Snap a window to a side", arguments={"window_id": _arg("string"), "side": _arg("string")}, effects=[_effect("window.last_snapped_id", arg="window_id"), _effect("window.snap_side", arg="side")])
    add("window.fullscreen", "Set window fullscreen state", arguments={"window_id": _arg("string"), "enabled": _arg("boolean")}, effects=[_effect("window.last_moved_id", arg="window_id"), _effect("window.fullscreen_enabled", arg="enabled")])
    add("window.cycle", "Cycle focused windows", arguments={"direction": _arg("string")}, effects=[_effect("window.cycle_direction", arg="direction")])

    add("workspace.create", "Create a workspace", arguments={"index": _arg("integer")}, effects=[_effect("workspace.last_created", arg="index"), _effect("workspace.ids", operation="add", arg="index")])
    add("workspace.switch", "Switch workspaces", arguments={"index": _arg("integer")}, effects=[_effect("workspace.current", arg="index"), _effect("workspace.visited_indices", operation="add", arg="index")])
    add("workspace.rename", "Rename a workspace", arguments={"index": _arg("integer"), "name": _arg("string")}, effects=[_effect("workspace.last_renamed", arg="index"), _effect("workspace.name", arg="name")])
    add("workspace.move_window", "Move a window to a workspace", arguments={"window_id": _arg("string"), "index": _arg("integer")}, effects=[_effect("workspace.last_window_id", arg="window_id"), _effect("workspace.last_window_index", arg="index")])
    add("workspace.remove", "Remove a workspace", arguments={"index": _arg("integer")}, effects=[_effect("workspace.last_removed", arg="index"), _effect("workspace.ids", operation="remove", arg="index")])
    add("workspace.show_overview", "Show workspace overview", effects=[_effect("workspace.overview", True)])

    # Clipboard and files.
    add("clipboard.read_current", "Read current clipboard item", effects=[_effect("task.clipboard_captured", True)], postconditions=[_condition("clipboard.current", operator="exists"), _condition("task.clipboard_captured", True)])
    add("clipboard.read_history", "Read clipboard history", arguments={"index": _arg("integer")}, effects=[_effect("clipboard.last_read_index", arg="index")])
    add("clipboard.copy", "Copy content", arguments={"content": _arg("string")}, effects=[_effect("clipboard.current", arg="content"), _effect("clipboard.history", operation="add", arg="content")])
    add("clipboard.cut", "Cut a resource", arguments={"resource_id": _arg("string")}, effects=[_effect("clipboard.last_resource_id", arg="resource_id"), _effect("filesystem.last_operation", "cut")])
    add("clipboard.paste", "Paste to a target", arguments={"target_id": _arg("string")}, preconditions=[_condition("clipboard.current", operator="exists")], effects=[_effect("clipboard.last_target_id", arg="target_id")])
    add("clipboard.pin", "Pin a history entry", arguments={"index": _arg("integer")}, effects=[_effect("clipboard.pinned_indices", operation="add", arg="index")])
    add("clipboard.unpin", "Unpin a history entry", arguments={"index": _arg("integer")}, effects=[_effect("clipboard.pinned_indices", operation="remove", arg="index")])
    add("clipboard.delete", "Delete a history entry", arguments={"index": _arg("integer")}, effects=[_effect("clipboard.last_deleted_index", arg="index")])
    add("clipboard.clear", "Clear clipboard history", effects=[_effect("clipboard.current", None), _effect("clipboard.history", [])], risk=Risk.HIGH, reversible=False, confirmation=True)

    add("filesystem.open", "Open a path", arguments={"path": _arg("string")}, effects=[_effect("filesystem.current_path", arg="path"), _effect("filesystem.opened_paths", operation="add", arg="path")])
    add("filesystem.open_file", "Open a file", arguments={"file_id": _arg("string")}, effects=[_effect("filesystem.active_file_id", arg="file_id"), _effect("editor.active_file_id", arg="file_id"), _effect("editor.document_open", True)])
    add("filesystem.reveal", "Reveal a node", arguments={"node_id": _arg("string")}, effects=[_effect("filesystem.selection_id", arg="node_id")])
    add("filesystem.list", "List a path", arguments={"path": _arg("string")}, effects=[_effect("filesystem.current_path", arg="path")])
    add("filesystem.search", "Search the filesystem", arguments={"query": _arg("string")}, effects=[_effect("filesystem.found_name", arg="query"), _effect("filesystem.found_id", "file:search-result"), _effect("filesystem.last_operation", "search"), _effect("filesystem.searched", True)])
    add("filesystem.read", "Read a file", arguments={"file_id": _arg("string")}, effects=[_effect("filesystem.active_file_id", arg="file_id"), _effect("task.file_captured", True)])
    add("filesystem.create_file", "Create a file", arguments={"parent": _arg("string"), "name": _arg("string"), "content": _arg("string")}, effects=[_effect("filesystem.last_created_parent", arg="parent"), _effect("filesystem.last_created_name", arg="name"), _effect("filesystem.last_created_id", "file:created")])
    add("filesystem.create_folder", "Create a folder", arguments={"parent": _arg("string"), "name": _arg("string")}, effects=[_effect("filesystem.last_created_parent", arg="parent"), _effect("filesystem.last_created_folder", arg="name"), _effect("filesystem.last_created_id", "folder:created")])
    add("filesystem.write", "Write file content", arguments={"file_id": _arg("string"), "content": _arg("string")}, effects=[_effect("filesystem.active_file_id", arg="file_id"), _effect("filesystem.last_operation", "write")])
    add("filesystem.rename", "Rename a node", arguments={"node_id": _arg("string"), "name": _arg("string")}, effects=[_effect("filesystem.selection_id", arg="node_id"), _effect("filesystem.found_name", arg="name"), _effect("filesystem.last_operation", "rename"), _effect("filesystem.renamed", True)])
    add("filesystem.move", "Move a node", arguments={"node_id": _arg("string"), "parent": _arg("string")}, effects=[_effect("filesystem.selection_id", arg="node_id"), _effect("filesystem.last_parent", arg="parent"), _effect("filesystem.last_operation", "move"), _effect("filesystem.moved", True)])
    add("filesystem.copy", "Copy a node", arguments={"node_id": _arg("string"), "parent": _arg("string")}, effects=[_effect("filesystem.selection_id", arg="node_id"), _effect("filesystem.last_parent", arg="parent"), _effect("filesystem.last_operation", "copy")])
    add("filesystem.trash", "Move a node to trash", arguments={"node_id": _arg("string")}, effects=[_effect("filesystem.selection_id", arg="node_id"), _effect("filesystem.last_operation", "trash")])
    add("filesystem.restore", "Restore a trashed node", arguments={"node_id": _arg("string")}, effects=[_effect("filesystem.selection_id", arg="node_id"), _effect("filesystem.last_operation", "restore")])
    add("filesystem.delete_permanently", "Delete a node permanently", arguments={"node_id": _arg("string")}, effects=[_effect("filesystem.selection_id", arg="node_id"), _effect("filesystem.last_operation", "delete")], risk=Risk.HIGH, reversible=False, confirmation=True)
    add("filesystem.empty_trash", "Empty trash", effects=[_effect("filesystem.last_operation", "empty_trash")], risk=Risk.HIGH, reversible=False, confirmation=True)
    add("filesystem.star", "Set starred state", arguments={"node_id": _arg("string"), "enabled": _arg("boolean")}, effects=[_effect("filesystem.starred_id", arg="node_id"), _effect("filesystem.starred", arg="enabled")])
    add("filesystem.sort", "Sort a folder", arguments={"path": _arg("string"), "field": _arg("string"), "direction": _arg("string")}, effects=[_effect("filesystem.current_path", arg="path"), _effect("filesystem.sort_field", arg="field"), _effect("filesystem.sort_direction", arg="direction")])
    add("filesystem.filter", "Filter a folder", arguments={"path": _arg("string"), "type": _arg("string")}, effects=[_effect("filesystem.current_path", arg="path"), _effect("filesystem.filter_type", arg="type")])
    add("filesystem.compress", "Create an archive", arguments={"node_ids": _arg("array"), "archive_name": _arg("string")}, effects=[_effect("filesystem.last_archive_id", "archive:created"), _effect("filesystem.last_created_name", arg="archive_name")])
    add("filesystem.extract", "Extract an archive", arguments={"archive_id": _arg("string"), "destination": _arg("string")}, effects=[_effect("filesystem.last_extracted_id", arg="archive_id"), _effect("filesystem.last_parent", arg="destination")])
    add("filesystem.mount", "Mount a device", arguments={"device_id": _arg("string")}, effects=[_effect("filesystem.mounted_device_ids", operation="add", arg="device_id")])
    add("filesystem.unmount", "Unmount a device", arguments={"device_id": _arg("string")}, effects=[_effect("filesystem.mounted_device_ids", operation="remove", arg="device_id")])

    # Editor, terminal, and browser.
    add("editor.open", "Open the editor", effects=[_effect("editor.open", True), _effect("application.running_ids", operation="add", value="app:editor")])
    add("editor.new_document", "Create a new document", effects=[_effect("editor.document_open", True), _effect("editor.active_file_id", None), _effect("editor.filename", None), _effect("editor.content", ""), _effect("editor.dirty", False), _effect("task.document_created", True), _effect("task.document_closed", False)])
    add("editor.open_file", "Open a file in the editor", arguments={"file_id": _arg("string")}, effects=[_effect("editor.active_file_id", arg="file_id"), _effect("editor.document_open", True), _effect("editor.dirty", False)])
    add("editor.replace_content", "Replace document content", arguments={"content": _arg("string")}, preconditions=[_condition("editor.document_open", True)], effects=[_effect("editor.content", arg="content"), _effect("editor.dirty", True)])
    add("editor.paste_content", "Paste clipboard content", preconditions=[_condition("editor.document_open", True), _condition("clipboard.current", operator="exists")], effects=[_effect("editor.content_matches_clipboard", True), _effect("editor.dirty", True), _effect("task.content_pasted", True)])
    add("editor.insert", "Insert document content", arguments={"position": _arg("integer"), "content": _arg("string")}, preconditions=[_condition("editor.document_open", True)], effects=[_effect("editor.clipboard_appended", True), _effect("editor.dirty", True)])
    add("editor.select", "Select a text range", arguments={"range": _arg("object")}, effects=[_effect("editor.selection", arg="range")])
    add("editor.copy_selection", "Copy selected text", preconditions=[_condition("editor.selection", operator="exists")], effects=[_effect("editor.last_selection_action", "copy")])
    add("editor.cut_selection", "Cut selected text", preconditions=[_condition("editor.selection", operator="exists")], effects=[_effect("editor.last_selection_action", "cut"), _effect("editor.dirty", True)])
    add("editor.delete_selection", "Delete selected text", preconditions=[_condition("editor.selection", operator="exists")], effects=[_effect("editor.last_selection_action", "delete"), _effect("editor.dirty", True)])
    add("editor.find", "Find in document", arguments={"query": _arg("string")}, effects=[_effect("editor.find_query", arg="query")])
    add("editor.replace", "Replace in document", arguments={"query": _arg("string"), "replacement": _arg("string")}, effects=[_effect("editor.find_query", arg="query"), _effect("editor.last_replacement", arg="replacement"), _effect("editor.dirty", True)])
    add("editor.save", "Save the active document", preconditions=[_condition("editor.document_open", True)], effects=[_effect("editor.dirty", False), _effect("task.document_saved", True)])
    add("editor.save_as", "Save the document with a name", arguments={"name": _arg("string"), "parent": _arg("string")}, preconditions=[_condition("editor.document_open", True)], effects=[_effect("editor.filename", arg="name"), _effect("editor.active_file_name", arg="name"), _effect("editor.parent", arg="parent"), _effect("editor.active_file_id", "file:saved"), _effect("editor.dirty", False), _effect("task.document_saved", True)])
    add("editor.close_document", "Close the active document", preconditions=[_condition("editor.dirty", False)], effects=[_effect("editor.document_open", False), _effect("editor.active_file_id", None), _effect("task.document_closed", True)])

    add("terminal.open", "Open a terminal", effects=[_effect("terminal.open", True)])
    add("terminal.execute", "Execute a terminal command", arguments={"command": _arg("string")}, preconditions=[_condition("terminal.open", True)], effects=[_effect("terminal.last_command", arg="command"), _effect("terminal.running", True)])
    add("terminal.interrupt", "Interrupt the running command", preconditions=[_condition("terminal.running", True)], effects=[_effect("terminal.running", False)])
    add("terminal.clear", "Clear terminal output", effects=[_effect("terminal.output", [])])
    add("terminal.change_directory", "Change terminal directory", arguments={"path": _arg("string")}, effects=[_effect("terminal.cwd", arg="path")])
    add("terminal.read_output", "Read terminal output", arguments={"range": _arg("object")}, effects=[_effect("terminal.last_read_range", arg="range")])
    add("terminal.copy_output", "Copy terminal output", arguments={"range": _arg("object")}, effects=[_effect("terminal.last_read_range", arg="range"), _effect("terminal.last_output_action", "copy")])

    add("browser.open", "Open the browser", effects=[_effect("browser.open", True), _effect("application.running_ids", operation="add", value="app:browser")])
    add("browser.navigate", "Navigate to a URL or query", arguments={"url_or_query": _arg("string")}, preconditions=[_condition("browser.open", True)], effects=[_effect("browser.url", arg="url_or_query")])
    add("browser.back", "Go back", preconditions=[_condition("browser.open", True)], effects=[_effect("browser.last_navigation", "back")])
    add("browser.forward", "Go forward", preconditions=[_condition("browser.open", True)], effects=[_effect("browser.last_navigation", "forward")])
    add("browser.reload", "Reload the page", preconditions=[_condition("browser.open", True)], effects=[_effect("browser.last_navigation", "reload")])
    add("browser.new_tab", "Open a browser tab", effects=[_effect("browser.tab_ids", operation="add", value="tab:new"), _effect("browser.active_tab_id", "tab:new")])
    add("browser.close_tab", "Close a browser tab", arguments={"tab_id": _arg("string")}, effects=[_effect("browser.tab_ids", operation="remove", arg="tab_id")])
    add("browser.switch_tab", "Switch browser tabs", arguments={"tab_id": _arg("string")}, preconditions=[_condition("browser.tab_ids", operator="contains", arg="tab_id")], effects=[_effect("browser.active_tab_id", arg="tab_id")])
    add("browser.bookmark", "Bookmark a URL", arguments={"url": _arg("string")}, effects=[_effect("browser.bookmarks", operation="add", arg="url")])
    add("browser.download", "Download a browser resource", arguments={"resource": _arg("string")}, preconditions=[_condition("browser.open", True)], effects=[_effect("browser.last_download_id", "file:download")])
    add("browser.find_on_page", "Find text on the page", arguments={"query": _arg("string")}, effects=[_effect("browser.find_query", arg="query")])
    add("browser.copy_url", "Copy the current browser URL", preconditions=[_condition("browser.open", True)], effects=[_effect("task.clipboard_captured", True), _effect("browser.url_copied", True)])

    # Search, notifications, connectivity, hardware and settings.
    add("search.query", "Search across domains", arguments={"text": _arg("string"), "domains": _arg("array")}, effects=[_effect("search.query", arg="text"), _effect("search.domains", arg="domains"), _effect("search.result_id", "result:1")])
    add("search.filter", "Filter search results", arguments={"type": _arg("string"), "date": _arg("string"), "owner": _arg("string")}, effects=[_effect("search.filter_type", arg="type"), _effect("search.filter_date", arg="date"), _effect("search.filter_owner", arg="owner")])
    add("search.open_result", "Open a search result", arguments={"result_id": _arg("string")}, effects=[_effect("search.result_id", arg="result_id"), _effect("search.last_action", "open")])
    add("search.reveal_result", "Reveal a search result", arguments={"result_id": _arg("string")}, effects=[_effect("search.result_id", arg="result_id"), _effect("search.last_action", "reveal")])
    add("search.clear", "Clear global search", effects=[_effect("search.query", ""), _effect("search.result_id", None)])

    add("notification.list", "List notifications", postconditions=[_condition("notification.ids", operator="exists")])
    add("notification.open", "Open a notification", arguments={"notification_id": _arg("string")}, effects=[_effect("notification.open_id", arg="notification_id")])
    add("notification.dismiss", "Dismiss a notification", arguments={"notification_id": _arg("string")}, effects=[_effect("notification.dismissed_ids", operation="add", arg="notification_id")])
    add("notification.clear_all", "Clear notifications", effects=[_effect("notification.ids", [])])
    add("notification.snooze", "Snooze a notification", arguments={"notification_id": _arg("string"), "duration": _arg("string")}, effects=[_effect("notification.snoozed_id", arg="notification_id"), _effect("notification.snooze_duration", arg="duration")])
    add("notification.set_dnd", "Set Do Not Disturb", arguments={"enabled": _arg("boolean")}, effects=[_effect("notification.dnd", arg="enabled")])

    add("wifi.observe", "Observe Wi-Fi state", postconditions=[_condition("wifi.enabled", operator="exists")])
    add("wifi.enable", "Enable Wi-Fi", effects=[_effect("wifi.enabled", True)])
    add("wifi.disable", "Disable Wi-Fi", effects=[_effect("wifi.enabled", False), _effect("wifi.connected", False), _effect("wifi.ssid", None), _effect("wifi.internet_available", False)])
    add("wifi.scan", "Scan for Wi-Fi networks", preconditions=[_condition("wifi.enabled", True)], effects=[_effect("wifi.visible_ssids", ["StudioNet", "PineHouse", "Guest"])], latency=Latency.MEDIUM)
    add("wifi.connect", "Connect to Wi-Fi", arguments={"ssid": _arg("string")}, preconditions=[_condition("wifi.enabled", True), _condition("wifi.visible_ssids", operator="contains", arg="ssid")], effects=[_effect("wifi.connected", True), _effect("wifi.ssid", arg="ssid"), _effect("wifi.known_networks", operation="add", arg="ssid"), _effect("wifi.internet_available", True)], latency=Latency.MEDIUM)
    add("wifi.disconnect", "Disconnect Wi-Fi", preconditions=[_condition("wifi.connected", True)], effects=[_effect("wifi.connected", False), _effect("wifi.ssid", None), _effect("wifi.internet_available", False)])
    add("wifi.forget", "Forget a Wi-Fi network", arguments={"ssid": _arg("string")}, effects=[_effect("wifi.known_networks", operation="remove", arg="ssid")], risk=Risk.MEDIUM, reversible=False, confirmation=True)
    add("wifi.test_internet", "Verify internet connectivity", preconditions=[_condition("wifi.connected", True)], effects=[_effect("task.internet_verified", True)], latency=Latency.MEDIUM)
    add("wifi.measure_latency", "Measure Wi-Fi latency", preconditions=[_condition("wifi.connected", True)], effects=[_effect("wifi.latency_ms", 24)], latency=Latency.MEDIUM)
    add("wifi.measure_throughput", "Measure Wi-Fi throughput", preconditions=[_condition("wifi.connected", True)], effects=[_effect("wifi.throughput_mbps", 180)], latency=Latency.HIGH)

    add("bluetooth.enable", "Enable Bluetooth", effects=[_effect("bluetooth.enabled", True)])
    add("bluetooth.disable", "Disable Bluetooth", effects=[_effect("bluetooth.enabled", False), _effect("bluetooth.connected_ids", [])])
    add("bluetooth.scan", "Scan for Bluetooth devices", preconditions=[_condition("bluetooth.enabled", True)], effects=[_effect("bluetooth.visible_ids", ["device:headphones", "device:keyboard"])], latency=Latency.MEDIUM)
    add("bluetooth.pair", "Pair a Bluetooth device", arguments={"device_id": _arg("string")}, effects=[_effect("bluetooth.paired_ids", operation="add", arg="device_id")], risk=Risk.MEDIUM, confirmation=True)
    add("bluetooth.connect", "Connect a Bluetooth device", arguments={"device_id": _arg("string")}, preconditions=[_condition("bluetooth.paired_ids", operator="contains", arg="device_id")], effects=[_effect("bluetooth.connected_ids", operation="add", arg="device_id")])
    add("bluetooth.disconnect", "Disconnect a Bluetooth device", arguments={"device_id": _arg("string")}, effects=[_effect("bluetooth.connected_ids", operation="remove", arg="device_id")])
    add("bluetooth.forget", "Forget a Bluetooth device", arguments={"device_id": _arg("string")}, effects=[_effect("bluetooth.paired_ids", operation="remove", arg="device_id")], risk=Risk.MEDIUM, reversible=False, confirmation=True)

    add("audio.set_volume", "Set output volume", arguments={"percent": _arg("integer")}, effects=[_effect("audio.volume", arg="percent")])
    add("audio.adjust_volume", "Adjust output volume", arguments={"delta": _arg("integer")}, effects=[_effect("audio.last_volume_delta", arg="delta")])
    add("audio.set_muted", "Set output mute", arguments={"enabled": _arg("boolean")}, effects=[_effect("audio.muted", arg="enabled")])
    add("audio.select_output", "Select audio output", arguments={"device_id": _arg("string")}, effects=[_effect("audio.output_device_id", arg="device_id")])
    add("audio.select_input", "Select audio input", arguments={"device_id": _arg("string")}, effects=[_effect("audio.input_device_id", arg="device_id")])
    add("audio.set_input_gain", "Set input gain", arguments={"percent": _arg("integer")}, effects=[_effect("audio.input_gain", arg="percent")])
    add("audio.test_output", "Test audio output", effects=[_effect("audio.last_test_succeeded", True)])

    add("display.set_brightness", "Set display brightness", arguments={"percent": _arg("integer")}, effects=[_effect("display.brightness", arg="percent")])
    add("display.adjust_brightness", "Adjust brightness", arguments={"delta": _arg("integer")}, effects=[_effect("display.last_brightness_delta", arg="delta")])
    add("display.set_theme", "Set color theme", arguments={"theme": _arg("string")}, effects=[_effect("display.theme", arg="theme")])
    add("display.set_night_light", "Set night light", arguments={"enabled": _arg("boolean")}, effects=[_effect("display.night_light", arg="enabled")])
    add("display.set_scale", "Set display scale", arguments={"percent": _arg("integer")}, effects=[_effect("display.scale", arg="percent")])
    add("display.set_resolution", "Set display resolution", arguments={"display_id": _arg("string"), "resolution": _arg("string")}, effects=[_effect("display.last_configured_id", arg="display_id"), _effect("display.resolution", arg="resolution")])
    add("display.arrange", "Arrange a display", arguments={"display_id": _arg("string"), "position": _arg("string")}, effects=[_effect("display.last_configured_id", arg="display_id"), _effect("display.position", arg="position")])

    add("settings.open", "Open Settings", effects=[_effect("settings.open", True)])
    add("settings.open_section", "Open a Settings section", arguments={"section_id": _arg("string")}, effects=[_effect("settings.open", True), _effect("settings.section_id", arg="section_id")])
    add("settings.read", "Read a setting", arguments={"key": _arg("string")}, effects=[_effect("settings.last_key", arg="key")])
    add("settings.set", "Set a setting", arguments={"key": _arg("string"), "value": _arg("object")}, effects=[_effect("settings.last_key", arg="key"), _effect("settings.last_value", arg="value")])
    add("settings.reset", "Reset a setting", arguments={"key": _arg("string")}, effects=[_effect("settings.last_key", arg="key"), _effect("settings.last_value", None)], risk=Risk.MEDIUM, confirmation=True)

    add("software.open", "Open Software", effects=[_effect("software.open", True)])
    add("software.search", "Search software", arguments={"query": _arg("string")}, effects=[_effect("software.query", arg="query")])
    add("software.show_details", "Show application details", arguments={"app_id": _arg("string")}, effects=[_effect("software.details_app_id", arg="app_id")])
    add("software.install", "Install software", arguments={"app_id": _arg("string")}, effects=[_effect("software.installed_ids", operation="add", arg="app_id")], risk=Risk.MEDIUM, confirmation=True)
    add("software.uninstall", "Uninstall software", arguments={"app_id": _arg("string")}, effects=[_effect("software.installed_ids", operation="remove", arg="app_id")], risk=Risk.HIGH, reversible=False, confirmation=True)
    add("software.update", "Update software", arguments={"app_id": _arg("string")}, effects=[_effect("software.updated_ids", operation="add", arg="app_id")], risk=Risk.MEDIUM)
    add("software.update_all", "Update all software", effects=[_effect("software.last_operation", "update_all")], risk=Risk.HIGH, confirmation=True)

    add("capture.fullscreen", "Capture the full screen", effects=[_effect("capture.kind", "fullscreen"), _effect("capture.last_capture_id", "capture:latest")])
    add("capture.window", "Capture a window", arguments={"window_id": _arg("string")}, effects=[_effect("capture.kind", "window"), _effect("capture.target", arg="window_id"), _effect("capture.last_capture_id", "capture:latest")])
    add("capture.region", "Capture a region", arguments={"rect": _arg("object")}, effects=[_effect("capture.kind", "region"), _effect("capture.target", arg="rect"), _effect("capture.last_capture_id", "capture:latest")])
    add("capture.record_start", "Start screen recording", arguments={"target": _arg("object")}, effects=[_effect("capture.active", True), _effect("capture.target", arg="target")])
    add("capture.record_stop", "Stop screen recording", preconditions=[_condition("capture.active", True)], effects=[_effect("capture.active", False), _effect("capture.last_capture_id", "capture:latest")])
    add("capture.save", "Save a capture", arguments={"name": _arg("string"), "parent": _arg("string")}, preconditions=[_condition("capture.last_capture_id", operator="exists")], effects=[_effect("capture.saved_name", arg="name"), _effect("capture.saved_parent", arg="parent")])
    add("capture.copy_to_clipboard", "Copy capture to clipboard", preconditions=[_condition("capture.last_capture_id", operator="exists")], effects=[_effect("capture.copied", True)])

    add("open_with.open", "Open a node with an application", arguments={"node_id": _arg("string"), "app_id": _arg("string")}, effects=[_effect("share.last_node_id", arg="node_id"), _effect("share.last_app_id", arg="app_id")])
    add("share.copy_link", "Copy a share link", arguments={"node_id": _arg("string")}, effects=[_effect("share.last_node_id", arg="node_id"), _effect("share.last_link", "agentos://shared")])
    add("share.send", "Send a node to a target", arguments={"node_id": _arg("string"), "target": _arg("string")}, effects=[_effect("share.last_node_id", arg="node_id"), _effect("share.last_target", arg="target")], risk=Risk.MEDIUM, confirmation=True)
    return registry


class DesktopEnvironment(GeneratedSimulator):
    """Live simulation binding generated from the same action effects used for training."""

    def __init__(self, registry: ActionRegistry | None = None, initial_fields: dict[str, JsonValue] | None = None) -> None:
        super().__init__(registry or build_desktop_registry(), initial_fields or desktop_initial_fields())
        self._initial_fields = deepcopy(initial_fields or desktop_initial_fields())
        self.failure_schedule: dict[str, int] = {}

    def inject_failures(self, schedule: dict[str, int]) -> None:
        self.failure_schedule = {key: max(0, int(value)) for key, value in schedule.items()}

    def execute(self, action_id: str, args: dict[str, JsonValue] | Any) -> str:
        remaining = self.failure_schedule.get(action_id, 0)
        if remaining > 0:
            self.failure_schedule[action_id] = remaining - 1
            raise RuntimeError(f"Injected live timeout: {action_id}")
        return super().execute(action_id, args)

    def reset(self, fields: dict[str, JsonValue] | None = None) -> None:
        with self._lock:
            self._fields = deepcopy(fields or self._initial_fields)
            self._revision += 1
            self.failure_schedule = {}


DESKTOP_ACTION_IDS = tuple(spec.id for spec in build_desktop_registry().discover())
