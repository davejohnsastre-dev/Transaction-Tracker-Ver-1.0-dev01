from datetime import datetime

import anvil.server
import anvil.tz
from anvil.tables import app_tables

from transactions import _require_admin, _require_auth, _text, _upper


def _stock_item_by_name(name):
    target = _upper(name)
    for row in app_tables.Stocks_Items.search():
        if _upper(row["name"]) == target:
            return row
    return None


def _quantity(value):
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return None
    if amount <= 0:
        return None
    return amount


def _display_user(row):
    if not row:
        return "Unknown user"
    return _text(row["employee_name"]) or _text(row["username"])


def _format_quantity(value):
    if value is None:
        return "0"
    return "%g" % float(value)


def _item_payload(row):
    return {
        "id": row.get_id(),
        "name": _text(row["name"]),
        "unit": _text(row["unit"]) or "unit",
        "starting_balance": float(row["starting_balance"] or 0),
        "current_balance": float(row["current_balance"] or 0),
        "balance_display": "%s %s" % (
            _format_quantity(row["current_balance"]),
            _text(row["unit"]) or "unit",
        ),
        "active": row["active"] is not False,
    }


def _movement_payload(row, kind):
    item = row["stock_item"]
    user = row["added_by"] if kind == "ADDITION" else row["withdrawn_by"]
    timestamp = row["added_at"] if kind == "ADDITION" else row["withdrawn_at"]
    return {
        "kind": kind,
        "item": _text(item["name"]) if item else "",
        "quantity": _format_quantity(row["quantity"]),
        "timestamp": timestamp.strftime("%b %d, %Y %I:%M %p") if timestamp else "",
        "user": _display_user(user),
        "notes": _text(row["notes"]),
    }


@anvil.server.callable
def get_stocks(session_token):
    user, error = _require_auth(session_token)
    if error:
        return error
    items = sorted(
        (_item_payload(row) for row in app_tables.Stocks_Items.search() if row["active"] is not False),
        key=lambda item: item["name"].upper(),
    )
    movements = [
        _movement_payload(row, "ADDITION")
        for row in app_tables.Stocks_Additions.search()
    ] + [
        _movement_payload(row, "WITHDRAWAL")
        for row in app_tables.Stocks_Withdrawals.search()
    ]
    movements.sort(key=lambda item: item["timestamp"], reverse=True)
    return {
        "success": True,
        "items": items,
        "movements": movements[:100],
        "can_manage": bool(_text(user["role"]).lower() == "admin") if user else False,
    }


@anvil.server.callable
def add_stock_item(name, unit, starting_balance, session_token):
    user, error = _require_admin(session_token)
    if error:
        return error
    name = _text(name)
    unit = _text(unit) or "unit"
    balance = _quantity(starting_balance)
    if not name:
        return {"success": False, "message": "Stock item name is required."}
    if balance is None and _text(starting_balance) not in ("", "0", "0.0"):
        return {"success": False, "message": "Starting balance must be zero or a positive number."}
    balance = balance or 0
    if _stock_item_by_name(name):
        return {"success": False, "message": "That stock item already exists."}
    now = datetime.now(anvil.tz.UTC)
    app_tables.Stocks_Items.add_row(
        name=name,
        unit=unit,
        starting_balance=balance,
        current_balance=balance,
        active=True,
        created_at=now,
        updated_at=now,
    )
    return {"success": True, "message": "Stock item added."}


@anvil.server.callable
def add_stock(item_name, quantity, notes, session_token):
    user, error = _require_admin(session_token)
    if error:
        return error
    item = _stock_item_by_name(item_name)
    amount = _quantity(quantity)
    if not item or item["active"] is False:
        return {"success": False, "message": "Select an active stock item."}
    if amount is None:
        return {"success": False, "message": "Added stock must be a positive number."}
    assert user is not None
    now = datetime.now(anvil.tz.UTC)
    item["current_balance"] = float(item["current_balance"] or 0) + amount
    item["updated_at"] = now
    app_tables.Stocks_Additions.add_row(
        stock_item=item,
        quantity=amount,
        added_at=now,
        added_by=user,
        notes=_text(notes),
    )
    return {"success": True, "message": "Stock added."}


@anvil.server.callable
def withdraw_stock(item_name, quantity, notes, session_token):
    user, error = _require_auth(session_token)
    if error:
        return error
    item = _stock_item_by_name(item_name)
    amount = _quantity(quantity)
    if not item or item["active"] is False:
        return {"success": False, "message": "Select an active stock item."}
    if amount is None:
        return {"success": False, "message": "Withdrawal must be a positive number."}
    assert user is not None
    current_balance = float(item["current_balance"] or 0)
    if amount > current_balance:
        return {"success": False, "message": "Insufficient stock. Available: %s." % _format_quantity(current_balance)}
    now = datetime.now(anvil.tz.UTC)
    item["current_balance"] = current_balance - amount
    item["updated_at"] = now
    app_tables.Stocks_Withdrawals.add_row(
        stock_item=item,
        quantity=amount,
        withdrawn_at=now,
        withdrawn_by=user,
        notes=_text(notes),
    )
    return {"success": True, "message": "Stock withdrawal recorded."}
