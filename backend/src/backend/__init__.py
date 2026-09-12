def main() -> None:
    """Run the AgentOS API using the project's console script."""
    import uvicorn

    uvicorn.run("backend.app:app", host="127.0.0.1", port=8000, reload=True)
