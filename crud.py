from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from models import Account, Transaction, TransactionType


def get_account_by_id(db: Session, account_id: int) -> Optional[Account]:
    return db.query(Account).filter(Account.id == account_id).first()


def get_account_by_owner_name(db: Session, owner_name: str) -> Optional[Account]:
    return db.query(Account).filter(Account.owner_name == owner_name).first()


def create_account(db: Session, owner_name: str, initial_balance: float = 0.0) -> Account:
    account = Account(owner_name=owner_name, balance=initial_balance)
    db.add(account)
    db.commit()
    db.refresh(account)
    
    if initial_balance > 0:
        create_transaction(db, account.id, TransactionType.DEPOSIT, initial_balance)
    
    return account


def update_account_balance(db: Session, account: Account, new_balance: float) -> Account:
    account.balance = new_balance
    db.commit()
    db.refresh(account)
    return account


def create_transaction(db: Session, account_id: int, transaction_type: TransactionType, amount: float) -> Transaction:
    transaction = Transaction(
        account_id=account_id,
        type=transaction_type,
        amount=amount
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def get_transactions_by_account(db: Session, account_id: int, limit: int = 50, offset: int = 0) -> List[Transaction]:
    return (
        db.query(Transaction)
        .filter(Transaction.account_id == account_id)
        .order_by(Transaction.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def get_transaction_count_by_account(db: Session, account_id: int) -> int:
    return db.query(Transaction).filter(Transaction.account_id == account_id).count()


def deposit(db: Session, account: Account, amount: float) -> Account:
    new_balance = account.balance + amount
    account = update_account_balance(db, account, new_balance)
    create_transaction(db, account.id, TransactionType.DEPOSIT, amount)
    return account


def withdraw(db: Session, account: Account, amount: float) -> Optional[Account]:
    if account.balance < amount:
        return None
    
    new_balance = account.balance - amount
    account = update_account_balance(db, account, new_balance)
    create_transaction(db, account.id, TransactionType.WITHDRAWAL, amount)
    return account
