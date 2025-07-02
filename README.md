# OpenAI Agentic Workflow System

A sophisticated multi-agent AI system that coordinates specialized agents to handle complex queries involving web search, file analysis, and intelligent workflow orchestration.

## 🎯 Overview

This system implements four specialized AI agents that work together to provide comprehensive responses to user queries:

1. **Input Interpreter Agent** - Analyzes user input to understand intent and requirements
2. **Web Search Agent** - Searches the internet for relevant information
3. **File Search Agent** - Searches and analyzes local files and code
4. **Handoff Agent** - Coordinates workflow between agents and synthesizes final responses

## 🚀 Features

- **Natural Language Processing**: Understands complex queries and determines the best approach
- **Multi-Source Intelligence**: Combines web search and local file analysis
- **Intelligent Orchestration**: Automatically coordinates between agents based on query requirements
- **Parallel & Sequential Execution**: Optimizes workflow execution for efficiency
- **Interactive Sessions**: Supports both single queries and interactive conversations
- **Rich Console Output**: Beautiful, informative displays with progress tracking
- **Extensible Architecture**: Easy to add new agents or modify existing ones

## 📋 Prerequisites

- Python 3.13+
- OpenAI API key
- Internet connection (for web search functionality)

## 🛠️ Installation

1. **Clone or download the project**
   ```bash
   git clone <repository-url>
   cd knowledge-gains-ai
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and add your OpenAI API key:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

3. **Install dependencies**
   ```bash
   pip install openai python-dotenv requests beautifulsoup4 pydantic aiohttp rich
   ```

## 📖 Usage

### Interactive Mode

Start an interactive session where you can ask multiple questions:

```bash
python main.py
```

Example interaction:
```
🔍 Your query: What is machine learning and find any Python ML files in this project

🚀 Processing query: What is machine learning and find any Python ML files in this project

📝 Step 1: Interpreting user input...
🔄 Step 2: Planning and executing workflow...
✅ Step 3: Presenting results...
```

### Single Query Mode

Run a single query from the command line:

```bash
python main.py "Search for recent AI developments and analyze any AI-related files in this project"
```

### Example Queries Mode

Run predefined example queries to see the system in action:

```bash
python main.py --examples
```

## 🤖 Agent Capabilities

### Input Interpreter Agent
- Intent recognition and classification
- Entity extraction from user queries
- Scope determination (web vs local search)
- Query refinement and optimization
- Agent recommendation based on analysis

### Web Search Agent
- Internet search using DuckDuckGo API
- Content summarization and analysis
- Source verification and credibility assessment
- Real-time information retrieval
- Fallback search mechanisms

### File Search Agent
- Local file content search
- Filename pattern matching
- Code structure analysis
- Multiple file format support
- Context-aware snippet extraction

### Handoff Agent
- Workflow coordination and orchestration
- Parallel and sequential execution planning
- Result synthesis from multiple agents
- Dependency management
- Real-time workflow monitoring

## 🔧 Configuration

### Environment Variables

Create a `.env` file with the following configuration:

```bash
# Required
OPENAI_API_KEY=your_openai_api_key_here

# Optional
OPENAI_MODEL=gpt-4                    # AI model to use
OPENAI_TEMPERATURE=0.7                # Response creativity (0.0-1.0)
DEFAULT_SEARCH_DIRECTORIES=./,~/docs  # Default search paths
```

### Search Directories

You can configure which directories the File Search Agent searches by:

1. **Environment variable**: Set `DEFAULT_SEARCH_DIRECTORIES` in `.env`
2. **Code configuration**: Modify `search_directories` in `main.py`
3. **Runtime**: Use the coordinator's `add_search_directory()` method

## 📚 Interactive Commands

During interactive sessions, use these special commands:

- `/help` - Show available commands and usage tips
- `/history` - Display your query history
- `/agents` - Show detailed agent capabilities
- `/clear` - Clear session history
- `quit`, `exit`, `bye` - End the session

## 🔍 Example Use Cases

### Research and Analysis
```
"Research the latest developments in quantum computing and find any quantum-related code in this project"
```

### Code Discovery
```
"Find all Python files related to data processing and explain what they do"
```

### Combined Intelligence
```
"What are best practices for API security and check if this project follows them"
```

### Local File Analysis
```
"Analyze all configuration files and summarize the project setup"
```

### Web Research
```
"Search for recent AI breakthroughs in 2024"
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Workflow Coordinator                     │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ Input Interpreter│  │  Web Search     │  │ File Search  │ │
│  │     Agent       │  │     Agent       │  │    Agent     │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
│                           │                                  │
│                    ┌─────────────────┐                      │
│                    │  Handoff Agent  │                      │
│                    │  (Coordinator)  │                      │
│                    └─────────────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

## 🧩 Extending the System

### Adding New Agents

1. Create a new agent class inheriting from `BaseAgent`
2. Implement the required `process()` method
3. Register the agent with the `HandoffAgent`
4. Update the `WorkflowCoordinator` to include your agent

Example:
```python
class CustomAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="CustomAgent", model="gpt-4")
    
    async def process(self, input_data):
        # Your agent logic here
        return {"result": "custom processing complete"}
```

### Customizing Workflows

Modify the `HandoffAgent`'s planning logic to create custom execution strategies for specific use cases.

## 🚨 Error Handling

The system includes comprehensive error handling:

- **API Failures**: Graceful fallbacks for OpenAI API issues
- **Network Issues**: Robust retry mechanisms for web searches
- **File Access**: Safe file handling with permission checks
- **Invalid Input**: Clear error messages for malformed queries

## 🔒 Security Considerations

- API keys are loaded from environment variables
- File search is restricted to configured directories
- Web search results are sanitized before processing
- No sensitive information is logged

## 🎨 Customization

### Modifying Agent Behavior

Each agent can be customized by:
- Adjusting temperature settings for different response styles
- Modifying system prompts for specialized domains
- Adding custom processing logic for specific use cases

### UI Customization

The Rich console interface can be customized:
- Colors and themes in the `WorkflowCoordinator`
- Table layouts and formatting
- Progress indicators and status messages

## 📈 Performance

- **Parallel Execution**: Agents run simultaneously when possible
- **Caching**: Conversation history is managed efficiently
- **Rate Limiting**: Built-in protections for API usage
- **Memory Management**: Automatic cleanup of large datasets

## 🐛 Troubleshooting

### Common Issues

1. **Missing API Key**
   ```
   ❌ Error: OPENAI_API_KEY environment variable is not set.
   ```
   Solution: Create `.env` file with your OpenAI API key

2. **Import Errors**
   ```
   ImportError: No module named 'openai'
   ```
   Solution: Install required dependencies

3. **Permission Denied**
   ```
   PermissionError: [Errno 13] Permission denied
   ```
   Solution: Check file permissions for search directories

### Debug Mode

For detailed debugging, modify the agents to include more verbose logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📝 License

This project is open source. Feel free to modify and distribute according to your needs.

## 🤝 Contributing

Contributions are welcome! Areas for improvement:
- Additional search engines for web search
- More file format support
- Enhanced natural language understanding
- Performance optimizations
- New agent types

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review error messages carefully
3. Ensure all dependencies are installed
4. Verify your OpenAI API key is valid

---

Built with ❤️ using OpenAI GPT-4, Python, and modern async architecture.