from __future__ import annotations

from copy import deepcopy
from typing import Any

from .compiler import TaskCompiler
from .desktop import build_desktop_registry, desktop_initial_fields
from .planning import search_plan


BENCHMARKS = {
    "clipboard_note": 'First take the clipboard content, make a new text file, paste it there, then save it with name "hero".',
    "find_append": "Find the file named hero, open it, add the current clipboard content at the end, and save it.",
    "organize_note": "Create a Projects folder in Documents, make a note from the clipboard, save it as brief, and move it into Projects.",
    "research_handoff": "Copy the browser address, create a source note, paste the address, save it as source, then reveal it in Files.",
    "workspace_setup": "Create a second workspace, open the browser there, open the editor beside it, create a new note, paste the clipboard, and save it as research.",
    "download_archive": "Open the browser, download the current page, find the download, rename it report, create an Archive folder, move it there, compress it, and open the archive location.",
    "clipboard_report": "Read the clipboard, create a Reports folder, make a new document, paste the clipboard, save it as hero, close the editor, open Files, find hero, move it into Reports, and star it.",
    "recovery": "Connect to StudioNet, verify internet access, open the browser, visit the project page, copy its address, make a note from it, save it as online, move it to Research, and star it.",
    "cross_workspace": "Open workspace two, launch Files, find hero, copy its contents, switch to workspace one, open the editor, create a document, paste it, save it as hero-copy, and close it.",
    "settings_evidence": "Turn on dark mode, set brightness to 60%, enable Do Not Disturb, take a screenshot, save it as setup, open Files, find setup, move it to Pictures, star it, and return to the desktop.",
}


def benchmark_initial_states() -> list[dict[str, Any]]:
    default = desktop_initial_fields()
    alternate = deepcopy(default)
    alternate["application"]["running_ids"] = ["app:browser", "app:terminal"]
    alternate["application"]["focused_id"] = "app:terminal"
    alternate["workspace"]["ids"] = ["workspace:1", "workspace:2"]
    alternate["workspace"]["current"] = 2
    alternate["workspace"]["visited_indices"] = [2]
    alternate["wifi"]["connected"] = True
    alternate["wifi"]["ssid"] = "PineHouse"
    alternate["display"]["theme"] = "dark"
    return [default, alternate]


def evaluate_ten_action_benchmarks() -> dict[str, Any]:
    compiler = TaskCompiler()
    registry = build_desktop_registry()
    results: list[dict[str, Any]] = []
    for name, prompt in BENCHMARKS.items():
        task = compiler.compile(prompt).automaton
        if task is None:
            results.append({"name": name, "success": False, "states": []})
            continue
        states = []
        for index, fields in enumerate(benchmark_initial_states()):
            bfs = search_plan(registry, task, fields, algorithm="bfs", max_steps=40)
            astar = search_plan(registry, task, fields, algorithm="astar", max_steps=40)
            states.append({
                "initial_state": index,
                "success": bfs is not None and astar is not None,
                "bfs_steps": len(bfs) if bfs else None,
                "astar_steps": len(astar) if astar else None,
            })
        results.append({"name": name, "success": all(item["success"] for item in states), "states": states})
    return {
        "benchmarks": results,
        "multiple_initial_states": len(benchmark_initial_states()),
        "passing": sum(item["success"] for item in results),
        "total": len(results),
    }
