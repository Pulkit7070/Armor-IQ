import asyncio
import json
import html
from typing import Any
from datetime import datetime

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


def sanitize_input(value: Any) -> str:
    """Sanitize user input to prevent injection attacks."""
    if value is None:
        return ""
    return html.escape(str(value))

from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from models import Account, Transaction, TransactionType
import crud

Base.metadata.create_all(bind=engine)

server = Server("banking-mcp-server")


def get_db() -> Session:
    return SessionLocal()


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available banking tools."""
    return [
        Tool(
            name="create_account",
            description="Create a new bank account with an owner name and optional initial balance",
            inputSchema={
                "type": "object",
                "properties": {
                    "owner_name": {
                        "type": "string",
                        "description": "The name of the account owner"
                    },
                    "initial_balance": {
                        "type": "number",
                        "description": "Initial balance for the account (default: 0)",
                        "default": 0
                    }
                },
                "required": ["owner_name"]
            }
        ),
        Tool(
            name="deposit",
            description="Deposit funds into an existing bank account",
            inputSchema={
                "type": "object",
                "properties": {
                    "account_id": {
                        "type": "integer",
                        "description": "The ID of the account to deposit into"
                    },
                    "amount": {
                        "type": "number",
                        "description": "The amount to deposit (must be positive)"
                    }
                },
                "required": ["account_id", "amount"]
            }
        ),
        Tool(
            name="withdraw",
            description="Withdraw funds from an existing bank account",
            inputSchema={
                "type": "object",
                "properties": {
                    "account_id": {
                        "type": "integer",
                        "description": "The ID of the account to withdraw from"
                    },
                    "amount": {
                        "type": "number",
                        "description": "The amount to withdraw (must be positive)"
                    }
                },
                "required": ["account_id", "amount"]
            }
        ),
        Tool(
            name="get_balance",
            description="Get the current balance of a bank account",
            inputSchema={
                "type": "object",
                "properties": {
                    "account_id": {
                        "type": "integer",
                        "description": "The ID of the account to check"
                    }
                },
                "required": ["account_id"]
            }
        ),
        Tool(
            name="get_transactions",
            description="Get the transaction history for a bank account",
            inputSchema={
                "type": "object",
                "properties": {
                    "account_id": {
                        "type": "integer",
                        "description": "The ID of the account"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of transactions to return (default: 50)",
                        "default": 50
                    }
                },
                "required": ["account_id"]
            }
        ),
        Tool(
            name="list_accounts",
            description="List all bank accounts in the system",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls for banking operations."""
    db = get_db()
    
    try:
        if name == "create_account":
            owner_name = arguments.get("owner_name", "").strip()
            initial_balance = arguments.get("initial_balance", 0.0)
            
            if not owner_name:
                return [TextContent(type="text", text="Error: Owner name cannot be empty")]
            
            if initial_balance < 0:
                return [TextContent(type="text", text="Error: Initial balance cannot be negative")]
            
            existing = crud.get_account_by_owner_name(db, owner_name)
            if existing:
                return [TextContent(type="text", text="Error: Account with this owner name already exists")]
            
            account = crud.create_account(db, owner_name, initial_balance)
            result = {
                "success": True,
                "message": f"Account created successfully",
                "account": {
                    "id": account.id,
                    "owner_name": account.owner_name,
                    "balance": account.balance,
                    "created_at": account.created_at.isoformat()
                }
            }
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "deposit":
            account_id = arguments.get("account_id")
            amount = arguments.get("amount")
            
            if amount is None or amount <= 0:
                return [TextContent(type="text", text="Error: Amount must be a positive number")]
            
            account = crud.get_account_by_id(db, account_id)
            if not account:
                return [TextContent(type="text", text="Error: Account not found")]
            
            account = crud.deposit(db, account, amount)
            result = {
                "success": True,
                "message": "Deposit successful",
                "account_id": account.id,
                "new_balance": account.balance
            }
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "withdraw":
            account_id = arguments.get("account_id")
            amount = arguments.get("amount")
            
            if amount is None or amount <= 0:
                return [TextContent(type="text", text="Error: Amount must be a positive number")]
            
            account = crud.get_account_by_id(db, account_id)
            if not account:
                return [TextContent(type="text", text="Error: Account not found")]
            
            if account.balance < amount:
                return [TextContent(type="text", text="Error: Insufficient funds")]
            
            account = crud.withdraw(db, account, amount)
            result = {
                "success": True,
                "message": "Withdrawal successful",
                "account_id": account.id,
                "new_balance": account.balance
            }
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "get_balance":
            account_id = arguments.get("account_id")
            
            account = crud.get_account_by_id(db, account_id)
            if not account:
                return [TextContent(type="text", text="Error: Account not found")]
            
            result = {
                "success": True,
                "account_id": account.id,
                "owner_name": account.owner_name,
                "balance": account.balance
            }
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "get_transactions":
            account_id = arguments.get("account_id")
            limit = arguments.get("limit", 50)
            
            account = crud.get_account_by_id(db, account_id)
            if not account:
                return [TextContent(type="text", text="Error: Account not found")]
            
            transactions = crud.get_transactions_by_account(db, account_id, limit=limit)
            total_count = crud.get_transaction_count_by_account(db, account_id)
            
            result = {
                "success": True,
                "account_id": account_id,
                "total_transactions": total_count,
                "transactions": [
                    {
                        "id": t.id,
                        "type": t.type.value,
                        "amount": t.amount,
                        "timestamp": t.timestamp.isoformat()
                    }
                    for t in transactions
                ]
            }
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "list_accounts":
            accounts = db.query(Account).all()
            result = {
                "success": True,
                "total_accounts": len(accounts),
                "accounts": [
                    {
                        "id": a.id,
                        "owner_name": a.owner_name,
                        "balance": a.balance,
                        "created_at": a.created_at.isoformat()
                    }
                    for a in accounts
                ]
            }
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        else:
            return [TextContent(type="text", text=f"Error: Unknown tool '{name}'")]
    
    finally:
        db.close()


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
