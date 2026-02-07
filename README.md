# ChatKit Assistant

This project is a demonstration of the **OpenAI ChatKit** framework. It features a FastAPI backend and a vanilla JavaScript frontend, showcasing advanced agentic behaviors including multi-modal reasoning, visual workflows, and dynamic UI manipulation.

<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; margin: 24px 0;">
  <img src="assets/img-1.png" alt="ChatKit Assistant" style="max-width: 100%; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
  <img src="assets/img-2.png" alt="Weather Widget" style="max-width: 100%; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
  <img src="assets/img-3.png" alt="Theme Suggestions" style="max-width: 100%; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
  <img src="assets/img-4.png" alt="Chart Widget" style="max-width: 100%; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
  <img src="assets/img-5.png" alt="Image Generation" style="max-width: 100%; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
  <img src="assets/img-6.png" alt="Web Search" style="max-width: 100%; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
</div>

## ✨ Key Features

- **🎨 Dynamic UI Theming**: The agent can propose and instantly apply new UI themes (colors, border radii, density, and custom font pairings) using ChatKit `Client Effects`.
- **📊 Visual Workflows**: Real-time visualization of the agent's internal "thinking" process. See database connections and data aggregation steps using the `Workflow` and `Task` components.
- **📈 Rich Data Visualization**: Automated generation of interactive Bar and Line charts for sales data analysis.
- **🔍 Deep Entity Integration**: Automatic context injection. When a user `@-mentions` an order or document, the system retrieves the full record from a mock database and injects it into the LLM's context.
- **🖼️ Progressive Image Generation**: Utilizes the `ImageGenerationTool` with support for partial image previews (streaming images as they are generated).
- **📝 Deep Research & Progress Updates**: Uses `ProgressUpdateEvent` to keep the user informed during long-running reasoning tasks.
- **📎 Multi-modal Attachments**: Seamlessly handle image and file uploads with local storage and Base64-powered UI previews.
- **🎤 Dictation & Citations**: Integrated speech-to-text transcription and interactive web citations (annotations).

## 🚀 Quick Start

### Prerequisites

- [uv](https://github.com/astral-sh/uv) (The extremely fast Python package manager)
- An OpenAI API Key

### 1. Clone and Setup
```bash
git clone https://github.com/aasherkamal216/ChatKit_Powered_Assistant
cd ChatKit_Powered_Assistant
```

### 2. Configure Environment
Create a `.env` file in the root directory:
```bash
cp .env.example .env
```
Add your `OPENAI_API_KEY` to the `.env` file.

### 3. Install Dependencies
Using `uv`, all dependencies (FastAPI, ChatKit SDK, etc.) are handled automatically:
```bash
uv sync
```

### 4. Run the Application
```bash
uv run main.py
```
The server will start at `http://localhost:8000`. Open this URL in your browser to start chatting.

## 🛠️ Project Structure

```text
├── app/
│   ├── agent.py    # Agent definitions & system instructions
│   ├── server.py   # ChatKitServer implementation (Logic & Action handlers)
│   ├── store.py    # SQLite implementation for persistent threads/items
│   ├── tools.py    # Agent tools (Weather, Theme Preview, etc.)
│   ├── types.py    # Request and Context models
│   └── widgets.py  # UI component builders (Weather, Charts, Themes)
├── static/
│   └── index.html  # Frontend ChatKit Web Component configuration
├── main.py         # FastAPI entry point & File upload handlers
└── pyproject.toml  # Modern Python dependency management
```

## 🧠 How It Works

### The Action Loop
When the agent calls a tool like `preview_theme`, it streams a `WidgetItem` to the UI. The user clicks "Apply Theme," which sends a `ThreadsCustomActionReq` back to `app/server.py`. The server then yields a `ClientEffectEvent`, which the frontend listens for to update the ChatKit `options` object in real-time.

### Deep Entity Lookup
Unlike basic bots, this system uses a `LocalConverter` (subclassing `ThreadItemConverter`). It intercepts tags in user messages:
1. User types: "What is the status of @order_123?"
2. `tag_to_message_content` triggers.
3. The server looks up `order_123` in `MOCK_ENTITIES`.
4. The actual data is wrapped in a `<ORDER_CONTEXT>` block and sent to the LLM.

## 🧪 Example Prompts to Try

- **Theming**: "Customize the UI. Make it dark mode with Lora font and sharp corners."
- **Data**: "Analyze sales performance for North America."
- **Entities**: "Tell me about @order_123."
- **Research**: "Generate a deep research report on the future of renewable energy."
- **Weather**: "What's the weather like in New York?"