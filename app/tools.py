from typing import Literal, List
import random
import asyncio
from datetime import datetime
from pydantic import BaseModel, Field
from agents import function_tool, RunContextWrapper
from chatkit.agents import AgentContext
from chatkit.types import (
    Workflow,
    CustomTask,
    CustomSummary,
    ProgressUpdateEvent,
    AssistantMessageContent,
    AssistantMessageItem,
    ProgressUpdateEvent,
    ThreadItemDoneEvent,
)
from .widgets import (
    build_vibrant_weather_widget,
    build_clean_theme_widget,
    build_sales_dashboard,
)

# Shared Mock Data (Used by Server for Deep Entity Integration)
MOCK_ENTITIES = {
    "order_123": {
        "title": "Order #123",
        "status": "Shipped",
        "items": ["Laptop", "Mouse"],
    },
    "order_456": {"title": "Order #456", "status": "Processing", "items": ["Monitor"]},
    "doc_policy": {"title": "Return Policy", "description": "Return Policy details..."},
    "doc_shipping": {
        "title": "Shipping Rates",
        "description": "Shipping Rates details...",
    },
}


class FontSource(BaseModel):
    family: str = Field(description="The name of the font family")
    src: str = Field(description="The URL to the .woff2 font file")
    weight: int = Field(default=400, description="Font weight (e.g. 400, 700)")
    style: str = Field(default="normal", description="Font style (normal or italic)")
    display: str = Field(default="swap", description="CSS font-display property")


@function_tool
async def preview_theme(
    ctx: RunContextWrapper[AgentContext],
    reasoning: str,
    color_scheme: Literal["light", "dark"],
    radius: Literal["pill", "round", "soft", "sharp"],
    density: Literal["compact", "normal", "spacious"],
    accent_color: str,
    font_family: str,
    font_family_mono: str,
    font_sources: List[FontSource],
    accent_level: Literal[0, 1, 2, 3] = 2,
    base_font_size: Literal[14, 15, 16, 17, 18] = 16,
    grayscale_hue: int = 210,
    tint: int = 8,
):
    """
    Propose a fully customized UI theme. This theme will be applied to the entire chat interface.
    """
    theme_data = {
        "colorScheme": color_scheme,
        "radius": radius,
        "density": density,
        "typography": {
            "baseSize": base_font_size,
            "fontFamily": font_family,
            "fontFamilyMono": font_family_mono,
            "fontSources": font_sources,
        },
        "color": {
            "grayscale": {"hue": grayscale_hue, "tint": tint},
            "accent": {"primary": accent_color, "level": accent_level},
        },
    }
    # 4. Stream Summary Message
    summary = "The theme I suggest would suggest is:"
    await ctx.context.stream(
        ThreadItemDoneEvent(
            item=AssistantMessageItem(
                thread_id=ctx.context.thread.id,
                id=ctx.context.generate_id("message"),
                created_at=datetime.now(),
                content=[AssistantMessageContent(text=summary)],
            ),
        )
    )
    widget = build_clean_theme_widget(reasoning, theme_data)
    await ctx.context.stream_widget(widget)

    return "Theme proposal displayed."


@function_tool
async def get_weather(ctx: RunContextWrapper[AgentContext], location: str):
    """Get the current weather with a vibrant UI card."""
    # Realistically you'd call a weather API here
    widget = build_vibrant_weather_widget(
        location=location,
        temperature="72",
        condition_desc="Sunny sky and warm temperatures are expected for the rest of the afternoon.",
    )
    await ctx.context.stream_widget(widget)
    return f"Showed weather card for {location}."


@function_tool
async def analyze_sales_data(
    ctx: RunContextWrapper[AgentContext], region: str = "Global"
):
    """
    Fetches and analyzes sales data. Displays a a chart widget with the results.
    """

    # 1. Initialize the Visual Workflow
    # This creates a box in the chat that will list the steps
    workflow = Workflow(
        type="custom",
        tasks=[
            CustomTask(
                title="Initializing Database Connection...", status_indicator="loading"
            )
        ],
        expanded=True,  # Start with the workflow expanded to show the steps in real-time
    )
    await ctx.context.start_workflow(workflow)

    # --- Step 1: Simulated Database Query ---
    await asyncio.sleep(2)  # Fake latency

    # Update first task to complete
    task_1 = workflow.tasks[0]
    task_1.title = "Connected to Sales DB"
    task_1.status_indicator = "complete"
    await ctx.context.update_workflow_task(task_1, 0)

    # --- Step 2: Aggregation ---
    # Add a new task dynamically
    task_2 = CustomTask(
        title=f"Aggregating records for {region}...", status_indicator="loading"
    )
    await ctx.context.add_workflow_task(task_2)

    await asyncio.sleep(2.5)  # Fake heavy computation

    task_2.title = f"Aggregated 14,203 records for {region}"
    task_2.status_indicator = "complete"
    # We have to fetch the index, usually it's len(tasks)-1
    await ctx.context.update_workflow_task(task_2, 1)

    # --- Step 3: Finalizing ---
    task_3 = CustomTask(title="Generating Visualization...", status_indicator="loading")
    await ctx.context.add_workflow_task(task_3)

    await asyncio.sleep(1.5)

    task_3.title = "Report Generated"
    task_3.status_indicator = "complete"
    await ctx.context.update_workflow_task(task_3, 2)

    # 2. Close the Workflow UI
    # Passing a summary collapses the steps into a nice header
    await ctx.context.end_workflow(
        summary=CustomSummary(
            title="Analysis Complete", icon="lucide:bar-chart"
        )  # "Completed in 3s"
    )

    # 3. Generate Mock Data
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
    data = []
    for m in months:
        rev = random.randint(4000, 9000)
        data.append(
            {"month": m, "revenue": rev, "profit": int(rev * 0.25)}  # 25% margin
        )

    # 4. Stream Summary Message
    summary = "Here is the sales analysis chart for the last 6 months. Revenue has been steadily increasing with a healthy profit margin."
    await ctx.context.stream(
        ThreadItemDoneEvent(
            item=AssistantMessageItem(
                thread_id=ctx.context.thread.id,
                id=ctx.context.generate_id("message"),
                created_at=datetime.now(),
                content=[AssistantMessageContent(text=summary)],
            ),
        )
    )
    # 5. Stream the Chart Widget
    widget = build_sales_dashboard(data, region)
    await ctx.context.stream_widget(widget)



@function_tool
async def generate_deep_research_report(
    ctx: RunContextWrapper[AgentContext], topic: str
):
    """
    Conducts a deep-dive research session on a complex topic.
    Use this when the user asks for a 'report', 'comprehensive study', or 'deep dive'.
    """

    # Stage 1: Planning
    await ctx.context.stream(ProgressUpdateEvent(text=f"Structuring research plan..."))
    await asyncio.sleep(1.5)

    # Stage 2: Broad Search
    await ctx.context.stream(ProgressUpdateEvent(text="Scanning academic journals..."))
    await asyncio.sleep(2.0)

    # Stage 3: Cross-referencing
    await ctx.context.stream(
        ProgressUpdateEvent(text="Cross-referencing data points...")
    )
    await asyncio.sleep(1.5)

    # Stage 4: Writing
    await ctx.context.stream(
        ProgressUpdateEvent(text="Drafting final executive summary...")
    )
    await asyncio.sleep(1.0)

    # Return the "result" which the LLM will then present to the user
    return f"""
    [RESEARCH REPORT: {topic}]
    
    EXECUTIVE SUMMARY:
    Comprehensive analysis confirms significant trends in {topic}. 
    Primary drivers include technological shifts and market adoption rates.
    
    KEY FINDINGS:
    1. Adoption has increased by 40% YoY.
    2. Regulatory frameworks are tightening globally.
    3. Key innovators are pivoting toward sustainable models.
    
    CONCLUSION:
    The outlook is positive, though short-term volatility is expected.
    """
