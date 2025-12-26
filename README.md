# Banking MCP Server

A Python-based MCP (Model Context Protocol) Server with FastAPI REST endpoints for banking operations, backed by SQLite database.

## Features

- **MCP Server**: Full MCP protocol support for AI assistant integration
- **REST API**: FastAPI-based HTTP endpoints
- Account creation with initial balance
- Deposit funds
- Withdraw funds (with balance validation)
- Balance inquiry
- Transaction history

## Requirements

- Python 3.10+

## Installation

```bash
pip install -r requirements.txt
```

## Running the REST API Server

```bash
uvicorn main:app --reload
```

Or:

```bash
python main.py
```

The API will be available at `http://localhost:8000`

## Running the MCP Server

```bash
python mcp_server.py
```

## MCP Configuration

Add this to your MCP client configuration (e.g., Claude Desktop):

```json
{
  "mcpServers": {
    "banking": {
      "command": "python",
      "args": ["path/to/mcp_server.py"]
    }
  }
}
```

## MCP Tools Available

| Tool               | Description                                                   |
| ------------------ | ------------------------------------------------------------- |
| `create_account`   | Create a new bank account with owner name and initial balance |
| `deposit`          | Deposit funds into an existing account                        |
| `withdraw`         | Withdraw funds from an existing account                       |
| `get_balance`      | Get the current balance of an account                         |
| `get_transactions` | Get transaction history for an account                        |
| `list_accounts`    | List all bank accounts in the system                          |

## API Documentation

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## REST Endpoints

| Method | Path                          | Description             |
| ------ | ----------------------------- | ----------------------- |
| GET    | `/health`                     | Health check            |
| POST   | `/accounts`                   | Create a new account    |
| POST   | `/accounts/{id}/deposit`      | Deposit funds           |
| POST   | `/accounts/{id}/withdraw`     | Withdraw funds          |
| GET    | `/accounts/{id}/balance`      | Get account balance     |
| GET    | `/accounts/{id}/transactions` | Get transaction history |

## Environment Variables

| Variable       | Description                | Default                  |
| -------------- | -------------------------- | ------------------------ |
| `PORT`         | Server port                | `8000`                   |
| `DATABASE_URL` | Database connection string | `sqlite:///./banking.db` |

## Deployment

### Render

1. Create a new Web Service
2. Connect your repository
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### Railway

1. Create a new project
2. Deploy from GitHub
3. Railway auto-detects Python and uses the correct start command

### Fly.io

Create a `fly.toml`:

```toml
app = "your-app-name"

[build]
  builder = "paketobuildpacks/builder:base"

[env]
  PORT = "8080"

[[services]]
  internal_port = 8080
  protocol = "tcp"

  [[services.ports]]
    port = 80
    handlers = ["http"]

  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]
```

## Example Usage

### Create Account

```bash
curl -X POST "http://localhost:8000/accounts" \
  -H "Content-Type: application/json" \
  -d '{"owner_name": "John Doe", "initial_balance": 1000}'
```

### Deposit

```bash
curl -X POST "http://localhost:8000/accounts/1/deposit" \
  -H "Content-Type: application/json" \
  -d '{"amount": 500}'
```

### Withdraw

```bash
curl -X POST "http://localhost:8000/accounts/1/withdraw" \
  -H "Content-Type: application/json" \
  -d '{"amount": 200}'
```

### Check Balance

```bash
curl "http://localhost:8000/accounts/1/balance"
```

### Get Transactions

```bash
curl "http://localhost:8000/accounts/1/transactions"
```

## License

MIT
