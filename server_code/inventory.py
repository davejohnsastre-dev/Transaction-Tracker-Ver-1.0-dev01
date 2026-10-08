from datetime import datetime

import anvil.server
import anvil.tz
from anvil.tables import app_tables

from transactions import _require_admin, _require_auth, _text, _upper


def _user_by_username(username):
    target = _text(username).lower()
    for row in app_tables.Core_Users.search():
        if _text(row["username"]).lower() == target:
            return row
    return None


def _row_by_id(table, row_id):
    target = _text(row_id)
    for row in table.search():
        if _text(row.get_id()) == target:
            return row
    return None


def _office_by_id(row_id):
    target = _text(row_id)
    for row in app_tables.Offices.search():
        if _text(row.get_id()) == target:
            return row
    return None


def _category_by_id(row_id):
    target = _text(row_id)
    for row in app_tables.Inventory_Category.search():
        if _text(row.get_id()) == target:
            return row
    return None


def _status_by_name(name):
    target = _upper(name)
    for row in app_tables.Inventory_Equipment_Statuses.search():
        if _upper(row["name"]) == target and row["active"] is not False:
            return row
    return None


def _equipment_by_article_item(article_item):
    target = _upper(article_item)
    for row in app_tables.Inventory_Equipment.search():
        if _upper(row["article_item"]) == target:
            return row
    return None


def _display_user(row):
    if not row:
        return "Unassigned"
    return _upper(row["employee_name"]) or _upper(row["username"])


def _display_lookup(row):
    return _upper(row["name"]) if row else ""


def _lookup_payload(table, include_code=False):
    rows = [row for row in table.search() if row["active"] is not False]
    rows.sort(key=lambda row: (row["sort_order"] or 0, _upper(row["name"])))
    return [
        {
            "id": row.get_id(),
            "name": _upper(row["name"]),
            "code": _upper(row["code"]) if include_code else "",
        }
        for row in rows
    ]


def _equipment_payload(row):
    status = row["status"]
    assignee = row["current_assignee"]
    office = row["office"]
    category = row["category"]
    return {
        "id": row.get_id(),
        "article_item": _upper(row["article_item"]),
        "description": _upper(row["description"]),
        "manufacturer": _upper(row["manufacturer"]),
        "model": _upper(row["model"]),
        "serial_number": _upper(row["serial_number"]),
        "old_property_number": _upper(row["old_property_number"]),
        "new_property_number": _upper(row["new_property_number"]),
        "sku": _upper(row["sku"]),
        "unit_value": row["unit_value"],
        "quantity_card": row["quantity_card"],
        "quantity_count": row["quantity_count"],
        "location": _upper(row["location"]),
        "office": _display_lookup(office),
        "office_id": office.get_id() if office else None,
        "category": _display_lookup(category),
        "category_id": category.get_id() if category else None,
        "status": _upper(status["name"]) if status else "NO STATUS",
        "assignee": _display_user(assignee),
        "assignee_username": _upper(assignee["username"]) if assignee else "",
        "remarks": _upper(row["notes"]),
        "notes": _upper(row["notes"]),
        "updated_at": row["updated_at"].strftime("%b %d, %Y %I:%M %p") if row["updated_at"] else "Never",
    }


def _audit_payload(row):
    equipment = row["equipment"]
    operator = row["operator"]
    from_user = row["from_user"]
    to_user = row["to_user"]
    old_status = row["old_status"]
    new_status = row["new_status"]
    details = _upper(row["details"])
    if from_user or to_user:
        details = "%s → %s%s" % (
            _display_user(from_user), _display_user(to_user), (" · " + details) if details else "",
        )
    if old_status or new_status:
        details = "%s → %s%s" % (
            _upper(old_status["name"]) if old_status else "NONE",
            _upper(new_status["name"]) if new_status else "NONE",
            (" · " + details) if details else "",
        )
    return {
        "timestamp": row["timestamp"].strftime("%b %d, %Y %I:%M %p"),
        "article_item": _upper(equipment["article_item"]) if equipment else "",
        "action": _upper(row["action"]),
        "operator": _display_user(operator),
        "details": _upper(details),
    }


def _write_inventory_audit(equipment, action, operator, **values):
    audit_values = {
        "timestamp": datetime.now(anvil.tz.UTC),
        "equipment": equipment,
        "action": action,
        "operator": operator,
        "details": _upper(values.get("details")),
    }
    for field in ("from_user", "to_user", "old_status", "new_status"):
        value = values.get(field)
        if value is not None:
            audit_values[field] = value
    app_tables.Inventory_Audit_Logs.add_row(**audit_values)


def _ensure_default_statuses():
    defaults = (
        ("AVAILABLE", "Ready to assign"),
        ("ASSIGNED", "Assigned to an employee"),
        ("IN REPAIR", "Temporarily unavailable for repair"),
        ("RETIRED", "No longer in service"),
    )
    for name, description in defaults:
        if not _status_by_name(name):
            app_tables.Inventory_Equipment_Statuses.add_row(name=name, description=description, active=True)


def _matches_filter(value, criterion):
    criterion = _text(criterion).lower()
    value = _text(value).lower()
    if criterion in ("empty", "null"):
        return not value
    return criterion in value


def _parse_number(value, label, whole=False):
    value = _text(value)
    if not value:
        return None, ""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None, "%s must be a number." % label
    if whole and not number.is_integer():
        return None, "%s must be a whole number." % label
    return (int(number) if whole else number), ""


@anvil.server.callable
def get_inventory(session_token, office_id=None, category_id=None, search="", filters=None):
    user, error = _require_auth(session_token)
    if error:
        return error
    assert user is not None
    _ensure_default_statuses()
    filters = filters or {}
    office = _office_by_id(office_id) if office_id else None
    category = _category_by_id(category_id) if category_id else None
    equipment = []
    if office_id and category_id and office and category:
        for row in app_tables.Inventory_Equipment.search():
            if row["office"] != office or row["category"] != category:
                continue
            payload = _equipment_payload(row)
            searchable = " ".join(_text(payload.get(field)) for field in (
                "article_item", "description", "serial_number", "old_property_number",
                "new_property_number", "sku", "location", "office", "category",
                "assignee", "remarks",
            ))
            search_text = _text(search).lower()
            search_matches = (
                (not _text(payload.get("remarks")))
                if search_text in ("empty", "null")
                else search_text in searchable.lower()
            )
            if search_matches and all(
                _matches_filter(payload.get(field), value)
                for field, value in filters.items() if _text(value)
            ):
                equipment.append(payload)
    equipment.sort(key=lambda item: (item["article_item"], item["serial_number"]))
    statuses = sorted(
        (_upper(row["name"]) for row in app_tables.Inventory_Equipment_Statuses.search() if row["active"] is not False),
        key=str.upper,
    )
    users = sorted(
        ({"username": _text(row["username"]), "name": _display_user(row)}
         for row in app_tables.Core_Users.search() if row["enabled"] is not False),
        key=lambda item: item["name"].upper(),
    )
    audits = sorted(
        (_audit_payload(row) for row in app_tables.Inventory_Audit_Logs.search()),
        key=lambda item: item["timestamp"], reverse=True,
    )[:100]
    return {
        "success": True,
        "equipment": equipment,
        "offices": _lookup_payload(app_tables.Offices, include_code=True),
        "categories": _lookup_payload(app_tables.Inventory_Category),
        "statuses": statuses,
        "users": users,
        "audits": audits,
        "can_manage": bool(_text(user["role"]).lower() == "admin"),
    }


@anvil.server.callable
def add_equipment(
    article_item, description, manufacturer, model, serial_number, location,
    status_name, notes, session_token, office_id=None, category_id=None,
    old_property_number="", new_property_number="", sku="", unit_value="",
    quantity_card="", quantity_count="",
):
    user, error = _require_admin(session_token)
    if error:
        return error
    article_item = _upper(article_item)
    description = _upper(description)
    if not article_item or not description:
        return {"success": False, "message": "Article item and description are required."}
    if _equipment_by_article_item(article_item):
        return {"success": False, "message": "That article item already exists."}
    office = _office_by_id(office_id) if office_id else None
    category = _category_by_id(category_id) if category_id else None
    if not office or not category:
        return {"success": False, "message": "Select an office and category."}
    unit_value, message = _parse_number(unit_value, "Unit value")
    if message:
        return {"success": False, "message": message}
    quantity_card, message = _parse_number(quantity_card, "Q/card", whole=True)
    if message:
        return {"success": False, "message": message}
    quantity_count, message = _parse_number(quantity_count, "Q/count", whole=True)
    if message:
        return {"success": False, "message": message}
    _ensure_default_statuses()
    status = _status_by_name(status_name)
    if not status and not _text(status_name):
        status = _status_by_name("AVAILABLE")
    if not status:
        return {"success": False, "message": "Select a valid inventory status."}
    assert user is not None
    now = datetime.now(anvil.tz.UTC)
    equipment = app_tables.Inventory_Equipment.add_row(
        article_item=article_item, description=description, office=office, category=category,
        manufacturer=_upper(manufacturer), model=_upper(model), serial_number=_upper(serial_number),
        old_property_number=_upper(old_property_number), new_property_number=_upper(new_property_number),
        sku=_upper(sku), unit_value=unit_value if unit_value is not None else 0,
        quantity_card=quantity_card if quantity_card is not None else 0,
        quantity_count=quantity_count if quantity_count is not None else 0,
        location=_upper(location), status=status, notes=_upper(notes), created_at=now, updated_at=now,
    )
    _write_inventory_audit(equipment, "CREATED", user, new_status=status, details="Equipment added")
    return {"success": True, "message": "Equipment added."}


@anvil.server.callable
def update_inventory_remarks(equipment_id, remarks, session_token):
    operator, error = _require_admin(session_token)
    if error:
        return error
    equipment = _row_by_id(app_tables.Inventory_Equipment, equipment_id)
    if not equipment:
        return {"success": False, "message": "Inventory record was not found."}
    equipment["notes"] = _upper(remarks)
    equipment["updated_at"] = datetime.now(anvil.tz.UTC)
    _write_inventory_audit(equipment, "REMARKS UPDATED", operator, details=equipment["notes"])
    return {"success": True, "message": "Remarks updated.", "item": _equipment_payload(equipment)}


@anvil.server.callable
def transfer_equipment(article_item, username, notes, session_token):
    operator, error = _require_admin(session_token)
    if error:
        return error
    equipment = _equipment_by_article_item(article_item)
    target = _user_by_username(username)
    if not equipment or not target or target["enabled"] is False:
        return {"success": False, "message": "Select an existing enabled employee and equipment."}
    assert operator is not None
    previous = equipment["current_assignee"]
    if previous and _text(previous["username"]).lower() == _text(target["username"]).lower():
        return {"success": False, "message": "This equipment is already assigned to that employee."}
    now = datetime.now(anvil.tz.UTC)
    if previous:
        for assignment in app_tables.Inventory_Equipment_Assignments.search():
            if assignment["equipment"] == equipment and not assignment["returned_at"]:
                assignment["returned_at"] = now
    equipment["current_assignee"] = target
    assigned_status = _status_by_name("ASSIGNED")
    old_status = equipment["status"]
    if assigned_status:
        equipment["status"] = assigned_status
    equipment["updated_at"] = now
    if previous:
        app_tables.Inventory_Equipment_Assignments.add_row(
            equipment=equipment, from_user=previous, to_user=target,
            assigned_at=now, assigned_by=operator, notes=_upper(notes),
        )
    else:
        app_tables.Inventory_Equipment_Assignments.add_row(
            equipment=equipment, to_user=target, assigned_at=now,
            assigned_by=operator, notes=_upper(notes),
        )
    _write_inventory_audit(
        equipment, "TRANSFERRED", operator, from_user=previous, to_user=target,
        old_status=old_status, new_status=assigned_status or old_status,
        details=_upper(notes),
    )
    return {"success": True, "message": "Equipment transferred."}


@anvil.server.callable
def update_equipment_status(article_item, status_name, notes, session_token):
    operator, error = _require_admin(session_token)
    if error:
        return error
    equipment = _equipment_by_article_item(article_item)
    status = _status_by_name(status_name)
    if not equipment or not status:
        return {"success": False, "message": "Select existing equipment and a valid status."}
    old_status = equipment["status"]
    now = datetime.now(anvil.tz.UTC)
    equipment["status"] = status
    equipment["updated_at"] = now
    _write_inventory_audit(
        equipment, "STATUS CHANGED", operator, old_status=old_status,
        new_status=status, details=_upper(notes),
    )
    return {"success": True, "message": "Equipment status updated."}
