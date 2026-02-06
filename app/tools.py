# app/tools.py
from agents import function_tool, RunContextWrapper
from chatkit.agents import AgentContext
from .widgets import build_weather_widget, build_feedback_form

# We define a global mapping of mock data for entity lookup
MOCK_ENTITIES = {
    "order_123": {"title": "Order #123", "status": "Shipped", "items": ["Laptop", "Mouse"]},
    "order_456": {"title": "Order #456", "status": "Processing", "items": ["Monitor"]},
}

@function_tool
async def get_weather(ctx: RunContextWrapper[AgentContext], location: str):
    """Get the current weather for a location."""
    # Simulate data fetching
    temp = 72
    condition = "Sunny"
    
    # Stream a widget to the user immediately
    widget = build_weather_widget(location, temp, condition)
    await ctx.context.stream_widget(widget)
    
    return {"temperature": temp, "condition": condition}

@function_tool
async def show_feedback_form(ctx: RunContextWrapper[AgentContext]):
    """Display a feedback form to the user."""
    widget = build_feedback_form()
    await ctx.context.stream_widget(widget)
    return "Feedback form displayed."

@function_tool
async def get_order_details(ctx: RunContextWrapper[AgentContext], order_id: str):
    """Fetch details for a specific order ID (e.g. order_123)."""
    order = MOCK_ENTITIES.get(order_id)
    if order:
        return order
    return {"error": "Order not found"}