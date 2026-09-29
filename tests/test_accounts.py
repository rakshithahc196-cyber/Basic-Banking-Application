from decimal import Decimal

from app.models.account import Account
from app.models.transaction import Transaction, TransactionType
from app.services import account_service


def test_get_current_account(client, register_user):
    user = register_user()
    response = client.get("/api/accounts/me", headers=user["headers"])

    assert response.status_code == 200
    assert response.json()["account_number"] == user["account_number"]
    assert response.json()["balance"] == "0.00"


def test_user_only_receives_their_own_account(client, register_user):
    first = register_user()
    second = register_user("Taylor Reed", "taylor@example.com", "AnotherPassword12!")

    first_account = client.get("/api/accounts/me", headers=first["headers"]).json()
    second_account = client.get("/api/accounts/me", headers=second["headers"]).json()

    assert first_account["account_number"] == first["account_number"]
    assert second_account["account_number"] == second["account_number"]
    assert first_account["account_number"] != second_account["account_number"]


def test_deposit_and_amount_validation(client, register_user):
    user = register_user()
    response = client.post("/api/accounts/deposit", json={"amount": "125.50"}, headers=user["headers"])
    invalid = client.post("/api/accounts/deposit", json={"amount": "0"}, headers=user["headers"])

    assert response.status_code == 200
    assert response.json()["balance"] == "125.50"
    assert response.json()["transaction"]["type"] == "DEPOSIT"
    assert invalid.status_code == 422


def test_deposit_cannot_exceed_numeric_balance_capacity(client, register_user):
    user = register_user()
    maximum = client.post(
        "/api/accounts/deposit",
        json={"amount": "9999999999.99"},
        headers=user["headers"],
    )
    overflow = client.post(
        "/api/accounts/deposit",
        json={"amount": "0.01"},
        headers=user["headers"],
    )

    assert maximum.status_code == 200
    assert overflow.status_code == 400
    assert client.get("/api/accounts/me", headers=user["headers"]).json()["balance"] == "9999999999.99"


def test_withdraw_success_and_insufficient_balance(client, register_user):
    user = register_user()
    client.post("/api/accounts/deposit", json={"amount": "100.00"}, headers=user["headers"])

    success = client.post("/api/accounts/withdraw", json={"amount": "35.25"}, headers=user["headers"])
    insufficient = client.post("/api/accounts/withdraw", json={"amount": "100.00"}, headers=user["headers"])
    invalid = client.post("/api/accounts/withdraw", json={"amount": "-1"}, headers=user["headers"])

    assert success.status_code == 200
    assert success.json()["balance"] == "64.75"
    assert success.json()["transaction"]["type"] == "WITHDRAW"
    assert insufficient.status_code == 400
    assert invalid.status_code == 422


def test_transfer_creates_matching_records_for_both_accounts(client, register_user):
    sender = register_user()
    recipient = register_user("Taylor Reed", "taylor@example.com", "AnotherPassword12!")
    client.post("/api/accounts/deposit", json={"amount": "250.00"}, headers=sender["headers"])

    response = client.post(
        "/api/accounts/transfer",
        json={"recipient_account_number": recipient["account_number"], "amount": "80.00"},
        headers=sender["headers"],
    )
    sender_history = client.get("/api/accounts/transactions", headers=sender["headers"]).json()["items"]
    recipient_history = client.get("/api/accounts/transactions", headers=recipient["headers"]).json()["items"]
    debit = next(item for item in sender_history if item["type"] == "TRANSFER_DEBIT")
    credit = next(item for item in recipient_history if item["type"] == "TRANSFER_CREDIT")

    assert response.status_code == 200
    assert response.json()["balance"] == "170.00"
    assert debit["reference_id"] == credit["reference_id"]
    assert debit["amount"] == credit["amount"] == "80.00"
    assert len(sender_history) == 2
    assert len(recipient_history) == 1


def test_transfer_rejects_self_and_insufficient_funds(client, register_user):
    sender = register_user()
    self_transfer = client.post(
        "/api/accounts/transfer",
        json={"recipient_account_number": sender["account_number"], "amount": "1.00"},
        headers=sender["headers"],
    )
    other = register_user("Taylor Reed", "taylor@example.com", "AnotherPassword12!")
    insufficient = client.post(
        "/api/accounts/transfer",
        json={"recipient_account_number": other["account_number"], "amount": "1.00"},
        headers=sender["headers"],
    )

    assert self_transfer.status_code == 400
    assert insufficient.status_code == 400
    assert client.get("/api/accounts/me", headers=sender["headers"]).json()["balance"] == "0.00"


def test_transaction_history_contains_only_owned_records(client, register_user):
    first = register_user()
    second = register_user("Taylor Reed", "taylor@example.com", "AnotherPassword12!")
    client.post("/api/accounts/deposit", json={"amount": "20.00"}, headers=first["headers"])

    first_items = client.get("/api/accounts/transactions", headers=first["headers"]).json()["items"]
    second_items = client.get("/api/accounts/transactions", headers=second["headers"]).json()["items"]

    assert len(first_items) == 1
    assert first_items[0]["type"] == "DEPOSIT"
    assert second_items == []


def test_transfer_rolls_back_if_a_ledger_write_fails(client, register_user, monkeypatch):
    sender = register_user()
    recipient = register_user("Taylor Reed", "taylor@example.com", "AnotherPassword12!")
    client.post("/api/accounts/deposit", json={"amount": "250.00"}, headers=sender["headers"])

    original_create = account_service.transaction_repository.create
    calls = 0

    def fail_on_second_ledger_entry(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("simulated ledger failure")
        return original_create(*args, **kwargs)

    monkeypatch.setattr(account_service.transaction_repository, "create", fail_on_second_ledger_entry)
    response = client.post(
        "/api/accounts/transfer",
        json={"recipient_account_number": recipient["account_number"], "amount": "80.00"},
        headers=sender["headers"],
    )
    monkeypatch.setattr(account_service.transaction_repository, "create", original_create)

    sender_account = client.get("/api/accounts/me", headers=sender["headers"]).json()
    recipient_account = client.get("/api/accounts/me", headers=recipient["headers"]).json()
    sender_history = client.get("/api/accounts/transactions", headers=sender["headers"]).json()["items"]

    assert response.status_code == 500
    assert response.json() == {"detail": "An unexpected server error occurred"}
    assert Decimal(sender_account["balance"]) == Decimal("250.00")
    assert Decimal(recipient_account["balance"]) == Decimal("0.00")
    assert [item["type"] for item in sender_history] == ["DEPOSIT"]