{
  "name": "Tessl",
  "mode": "vendored",
  "dependencies": {
    "tessl-labs/spec-driven-development": {
      "version": "2.0.1"
    }
  },
  "agents": [
    "gemini",
    "codex",
    "copilot",
    "copilot-vscode"
  ]
}


{
  "mcpServers": {
    "tessl": {
      "type": "stdio",
      "command": "tessl",
      "args": [
        "mcp",
        "start"
      ]
    }
  }
}
