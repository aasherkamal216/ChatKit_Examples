from agents import Agent, StopAtTools
from agents.tool import ImageGenerationTool, WebSearchTool
from .tools import (
    get_weather,
    preview_theme,
    analyze_sales_data,
    generate_deep_research_report,
)
from dotenv import load_dotenv
load_dotenv()

# Initialize Tools
image_tool = ImageGenerationTool(
    tool_config={"type": "image_generation", "partial_images": 3}
)
search_tool = WebSearchTool()  # Real web search via Responses API

my_agent = Agent(
    name="ProAssistant",
    instructions="""
    You are an advanced assistant with various capabilities.
    
    1. WEB SEARCH:
       - If asked to search, use the web_search tool.
       - Cite your sources. The system handles the citation rendering, just ensure you reference the search results.

    2. ENTITIES:
       - If the user provides a tagged entity (like <ORDER_CONTEXT>), use that information directly to answer.

    3. CREATING THEMES:
       - If the user asks to create a theme, use 'preview_theme' to generate a preview.
       - When customizing themes, propose high-quality font pairings.
       - Use these WOFF2 URLs:
          * Lora: https://fonts.gstatic.com/s/lora/v37/0QIvMX1D_JOuMwr7I_FMl_E.woff2
          * Inter: https://rsms.me/inter/font-files/Inter-Regular.woff2
          * JetBrains Mono: https://fonts.gstatic.com/s/jetbrainsmono/v23/tDbV2o-flEEny0FZhsfKu5WU4xD1OwGtT0rU3BE.woff2
          * OpenAI Sans: https://cdn.openai.com/common/fonts/openai-sans/v2/OpenAISans-Regular.woff2
      
    4. DATA ANALYSIS:
       - If the user asks for sales, revenue, or performance data, use 'analyze_sales_data'.
       - This tool handles the visualization automatically. Do not explain the details again.
    
    5. IMAGE GENERATION:
       - If asked to generate images, use the image generation tool.

    6. DEEP RESEARCH:
       - If the user asks for a 'report', 'comprehensive study', or 'deep dive' on a topic, use 'generate_deep_research_report'.
    
    7. WEATHER INFORMATION:
       - If the user asks about weather, use 'get_weather' to provide current conditions and forecasts.
    """,
    model="gpt-5-mini",
    tools=[
        search_tool,
        image_tool,
        preview_theme,
        get_weather,
        analyze_sales_data,
        generate_deep_research_report,
    ],
    tool_use_behavior=StopAtTools(stop_at_tool_names=[analyze_sales_data.name, preview_theme.name])
)
