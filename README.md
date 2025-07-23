# MSSQL MCP Server

This project provides a Model Context Protocol (MCP) server for Microsoft SQL Server, allowing you to interact with SQL Server databases via the MCP protocol.

## Features
- List tables in a SQL Server database
- Read table data
- Execute SQL queries, stored procedures, and functions

## Requirements
- Python 3.10 or higher
- Microsoft SQL Server (local or remote)
- ODBC Driver 17 for SQL Server

## Installation

### Option 1: Direct Installation
1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/mssql-mcp-server.git
   cd mssql-mcp-server
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install ODBC Driver 17 for SQL Server (if not already installed):
   - **Windows**: [Download ODBC Driver](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)
   - **Linux**: Follow [Microsoft's Linux installation guide](https://learn.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server)
   - **macOS**: Use Homebrew: `brew install msodbcsql17 mssql-tools`

### Option 2: Development Installation
1. Clone and install in development mode:
   ```bash
   git clone https://github.com/yourusername/mssql-mcp-server.git
   cd mssql-mcp-server
   pip install -e .
   ```

## Configuration
Create a `.env` file in the project root with the following content:

### Basic Configuration (Windows Authentication)
```
MSSQL_SERVER=localhost
MSSQL_DATABASE=master
TrustServerCertificate=yes
Trusted_Connection=yes
```

### SQL Server Authentication
```
MSSQL_SERVER=localhost
MSSQL_DATABASE=master
MSSQL_USERNAME=your_username
MSSQL_PASSWORD=your_password
TrustServerCertificate=yes
Trusted_Connection=no
```

- Adjust values as needed for your environment.
- For production environments, consider using more secure certificate validation.

## Quick Start

1. **Test the server locally:**
   ```bash
   python -m mssql_mcp_server.server
   ```

2. **Set up environment variables:**
   Create a `.env` file in the project root:
   ```env
   MSSQL_SERVER=localhost
   MSSQL_DATABASE=master
   TrustServerCertificate=yes
   Trusted_Connection=yes
   ```

3. **Test connection:**
   The server should start without errors and be ready to accept MCP requests.

## Logging
- Logs are written to `mssql_mcp_server.log`.

## MCP Integration (Optional)

If you use the [Model Context Protocol (MCP)](https://github.com/modelcontext/modelcontext-protocol) extension or tooling, you can configure a global or workspace `mcp.json` file to register this MSSQL server for all your workspaces.

### MCP Configuration for VS Code

1. **Find your VS Code settings directory:**
   - **Windows**: `%APPDATA%\Code\User\`
   - **macOS**: `~/Library/Application Support/Code/User/`
   - **Linux**: `~/.config/Code/User/`

2. **Create or edit `mcp.json` in the settings directory:**

```jsonc
{
  "servers": {
    "mssql": {
      "command": "python",
      "args": [
        "-m",
        "mssql_mcp_server.server"
      ],
      "env": {
        "PYTHONPATH": "/absolute/path/to/mssql-mcp-server",
        "MSSQL_SERVER": "YOUR_SERVER",
        "MSSQL_DATABASE": "YOUR_DATABASE",
        "TrustServerCertificate": "yes",
        "Trusted_Connection": "yes"
      },
      "type": "stdio"
    }
  },
  "inputs": []
}
```

### Example Server Configuration
```jsonc
{
  "servers": {
    "mssql-test": {
      "command": "python",
      "args": ["-m", "mssql_mcp_server.server"],
      "env": {
        "PYTHONPATH": "D:/my_ai_agent",
        "MSSQL_SERVER": "TEST-SERVER",
        "MSSQL_DATABASE": "TestDatabase",
        "MSSQL_USERNAME": "testuser",
        "MSSQL_PASSWORD": "testpass",
        "TrustServerCertificate": "yes",
        "Trusted_Connection": "no"
      },
      "type": "stdio"
    }
  },
  "inputs": []
}
```

### Configuration Notes
- Adjust the `env` values to match your SQL Server environment.
- Set `PYTHONPATH` to the absolute path of the folder containing the `mssql_mcp_server` directory.
- Use different server names in MCP config to connect to multiple databases simultaneously.
- For production environments, use `TrustServerCertificate=no` and proper SSL certificates.
- Place this file in your global VS Code user settings folder or in your workspace root as needed.

## Troubleshooting

### Common Issues

1. **ODBC Driver Not Found**
   ```
   Error: [Microsoft][ODBC Driver Manager] Data source name not found and no default driver specified
   ```
   **Solution**: Install ODBC Driver 17 for SQL Server

2. **Connection Timeout**
   ```
   Error: Connection timeout expired
   ```
   **Solution**: Check server name, network connectivity, and firewall settings

3. **Authentication Failed**
   ```
   Error: Login failed for user
   ```
   **Solution**: Verify credentials, check SQL Server authentication mode

4. **Database Not Found**
   ```
   Error: Cannot open database requested by the login
   ```
   **Solution**: Ensure database exists and user has access permissions

### Debug Mode
Enable debug logging by setting environment variable:
```bash
export PYTHONPATH=/path/to/your/project
export MSSQL_DEBUG=1
python -m mssql_mcp_server.server
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- Create an issue on GitHub for bug reports or feature requests
- Check the [MCP documentation](https://github.com/modelcontextprotocol/spec) for protocol details
