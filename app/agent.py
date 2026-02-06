# app/agent.py
from agents import Agent
from agents.tool import ImageGenerationTool
from .tools import get_weather, show_feedback_form, get_order_details

# We use the standard OpenAI ImageGenerationTool provided by the agents library
image_tool = ImageGenerationTool(
    tool_config={"type": "image_generation", "partial_images": 3}
)

my_agent = Agent(
    name="ChatKitDemo",
    instructions="""
    You are a helpful assistant powered by ChatKit.
    - Use widgets for weather and forms.
    - If the user asks for an image, generate it.
    - If the user references an Order (e.g. via @-mention), lookup details.
    """,
    model="gpt-5-mini",
    tools=[get_weather, show_feedback_form, get_order_details, image_tool],
)