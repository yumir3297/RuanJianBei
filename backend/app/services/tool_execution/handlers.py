from app.services.tool_execution.registry import ToolRegistry


def build_registry() -> ToolRegistry:
    """Return only production handlers explicitly approved and implemented in this repository."""
    return ToolRegistry()
