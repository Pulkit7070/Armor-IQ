import os
import logging
import html
import secrets
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status, Query, Security
from fastapi.security import APIKeyHeader


def sanitize_input(value: str) -> str:
    """Sanitize user input to prevent injection attacks."""
    if value is None:
        return ""
    return html.escape(str(value))

from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import engine, get_db, Base
from models import Account, TransactionType
import crud
import schemas

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# API Key authentication
API_KEY = os.getenv("API_KEY", "dev-api-key-change-in-production")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """Verify the API key from request header."""
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is missing",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    if not secrets.compare_digest(api_key, API_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
    return api_key


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up - creating database tables")
    Base.metadata.create_all(bind=engine)
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Banking MCP Server",
    description="A Python-based MCP Server with banking operations backed by SQL database",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(
    "/health",
    response_model=schemas.HealthResponse,
    tags=["Health"],
    summary="Health Check",
    description="Check if the API is running and healthy"
)
async def health_check():
    logger.info("Health check requested")
    return schemas.HealthResponse(status="OK", timestamp=datetime.utcnow())


@app.post(
    "/accounts",
    response_model=schemas.AccountResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Accounts"],
    summary="Create Account",
    description="Create a new bank account with owner name and optional initial balance",
    responses={
        201: {"description": "Account created successfully"},
        400: {"description": "Invalid input data"},
        409: {"description": "Account with this owner name already exists"}
    }
)
async def create_account(
    account_data: schemas.AccountCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    safe_owner_name = sanitize_input(account_data.owner_name)
    logger.info("Creating account for owner: %s", safe_owner_name)
    
    existing_account = crud.get_account_by_owner_name(db, account_data.owner_name)
    if existing_account:
        logger.warning("Account already exists for owner: %s", safe_owner_name)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Account with this owner name already exists"
        )
    
    account = crud.create_account(db, account_data.owner_name, account_data.initial_balance)
    logger.info("Account created with ID: %d", account.id)
    return account


@app.post(
    "/accounts/{account_id}/deposit",
    response_model=schemas.MessageResponse,
    tags=["Transactions"],
    summary="Deposit Funds",
    description="Add funds to an existing account",
    responses={
        200: {"description": "Deposit successful"},
        400: {"description": "Invalid amount"},
        404: {"description": "Account not found"}
    }
)
async def deposit(
    account_id: int,
    deposit_data: schemas.DepositRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    logger.info("Deposit request: account_id=%d, amount=%.2f", account_id, deposit_data.amount)
    
    account = crud.get_account_by_id(db, account_id)
    if not account:
        logger.warning("Account not found: %d", account_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    account = crud.deposit(db, account, deposit_data.amount)
    logger.info("Deposit successful: account_id=%d, new_balance=%.2f", account_id, account.balance)
    
    return schemas.MessageResponse(
        message="Deposit successful",
        account_id=account.id,
        new_balance=account.balance
    )


@app.post(
    "/accounts/{account_id}/withdraw",
    response_model=schemas.MessageResponse,
    tags=["Transactions"],
    summary="Withdraw Funds",
    description="Withdraw funds from an existing account if balance is sufficient",
    responses={
        200: {"description": "Withdrawal successful"},
        400: {"description": "Invalid amount or insufficient funds"},
        404: {"description": "Account not found"}
    }
)
async def withdraw(
    account_id: int,
    withdraw_data: schemas.WithdrawRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    logger.info("Withdrawal request: account_id=%d, amount=%.2f", account_id, withdraw_data.amount)
    
    account = crud.get_account_by_id(db, account_id)
    if not account:
        logger.warning("Account not found: %d", account_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    if account.balance < withdraw_data.amount:
        logger.warning("Insufficient funds: account_id=%d, balance=%.2f, requested=%.2f", account_id, account.balance, withdraw_data.amount)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient funds"
        )
    
    account = crud.withdraw(db, account, withdraw_data.amount)
    logger.info("Withdrawal successful: account_id=%d, new_balance=%.2f", account_id, account.balance)
    
    return schemas.MessageResponse(
        message="Withdrawal successful",
        account_id=account.id,
        new_balance=account.balance
    )


@app.get(
    "/accounts/{account_id}/balance",
    response_model=schemas.BalanceResponse,
    tags=["Accounts"],
    summary="Get Balance",
    description="Get the current balance of an account",
    responses={
        200: {"description": "Balance retrieved successfully"},
        404: {"description": "Account not found"}
    }
)
async def get_balance(
    account_id: int,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    logger.info("Balance inquiry: account_id=%d", account_id)
    
    account = crud.get_account_by_id(db, account_id)
    if not account:
        logger.warning("Account not found: %d", account_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    return schemas.BalanceResponse(
        account_id=account.id,
        owner_name=account.owner_name,
        balance=account.balance
    )


@app.get(
    "/accounts/{account_id}/transactions",
    response_model=schemas.TransactionListResponse,
    tags=["Transactions"],
    summary="Get Transaction History",
    description="Get the transaction history for an account",
    responses={
        200: {"description": "Transactions retrieved successfully"},
        404: {"description": "Account not found"}
    }
)
async def get_transactions(
    account_id: int,
    limit: int = Query(default=50, ge=1, le=100, description="Maximum number of transactions to return"),
    offset: int = Query(default=0, ge=0, description="Number of transactions to skip"),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    logger.info("Transaction history request: account_id=%d, limit=%d, offset=%d", account_id, limit, offset)
    
    account = crud.get_account_by_id(db, account_id)
    if not account:
        logger.warning("Account not found: %d", account_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    transactions = crud.get_transactions_by_account(db, account_id, limit, offset)
    total_count = crud.get_transaction_count_by_account(db, account_id)
    
    transaction_responses = [
        schemas.TransactionResponse(
            id=t.id,
            account_id=t.account_id,
            type=t.type.value,
            amount=t.amount,
            timestamp=t.timestamp
        )
        for t in transactions
    ]
    
    return schemas.TransactionListResponse(
        account_id=account_id,
        transactions=transaction_responses,
        total_count=total_count
    )


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "8000"))
    logger.info("Starting server on port %d", port)
    uvicorn.run(app, host="0.0.0.0", port=port)
