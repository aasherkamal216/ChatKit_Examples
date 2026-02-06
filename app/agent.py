from agents import Agent
from agents.tool import ImageGenerationTool, WebSearchTool
from .tools import get_weather, get_order_details, preview_theme

# Initialize Tools
image_tool = ImageGenerationTool(
    tool_config={"type": "image_generation", "partial_images": 3}
)
search_tool = WebSearchTool()  # Real web search via Responses API

my_agent = Agent(
    name="ProAssistant",
    instructions="""
    You are an advanced researcher and UI designer.
    - If asked to search the web, use the web_search tool.
    - If the user wants to change the 'theme' or 'style' of this chat (e.g., 'Make it funky', 'Dark mode with purple accent'), 
      generate a detailed ChatKit Theme object and use the 'preview_theme' tool to show it to the user.
    - Wait for them to click 'Set Theme' in the widget before you consider the theme applied.
    """,
    model="gpt-5-mini",
    tools=[search_tool, preview_theme, get_weather, get_order_details, image_tool],
)