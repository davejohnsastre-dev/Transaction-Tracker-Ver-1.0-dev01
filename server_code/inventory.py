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


def _status_by_name(name):
    target = _upper(name)
    for row in app_tables.Inventory_Equipment_Statuses.search():
        if _upper(row["name"]) == target and row["active"] is not False:
            return row
    return None


def _equipment_by_tag(asset_tag):
    target = _upper(asset_tag)
    for row in app_tables.Inventory_Equipment.search():
        if _upper(row["asset_tag"]) == target:
            return row
    return None


def _display_user(row):
    if not row:
        return "Unassigned"
    return _text(row["employee_name"]) or _text(row["username"])


def _equipment_payload(row):
    status = row["status"]
    assignee = row["current_assignee"]
    return {
        "id": row.get_id(),
        "asset_tag": _upper(row["asset_tag"]),
        "category": _text(row["category"]),
        "manufacturer": _text(row["manufacturer"]),
        "model": _text(row["model"]),
        "serial_number": _text(row["serial_number"]),
        "location": _text(row["location"]),
        "status": _text(status["name"]) if status else "No status",
        "assignee": _display_user(assignee),
        "assignee_username": _text(assignee["username"]) if assignee else "",
        "notes": _text(row["notes"]),
        "updated_at": row["updated_at"].strftime("%b %d, %Y %I:%M %p") if row["updated_at"] else "Never",
    }


def _audit_payload(row):
    equipment = row["equipment"]
    operator = row["operator"]
    from_user = row["from_user"]
    to_user = row["to_user"]
    old_status = row["old_status"]
    new_status = row["new_status"]
    details = _text(row["details"])
    if from_user or to_user:
        details = "%s → %s%s" % (
            _display_user(from_user),
            _display_user(to_user),
            (" · " + details) if details else "",
        )
    if old_status or new_status:
        details = "%s → %s%s" % (
            _text(old_status["name"]) if old_status else "None",
            _text(new_status["name"]) if new_status else "None",
            (" · " + details) if details else "",
        )
    return {
        "timestamp": row["timestamp"].strftime("%b %d, %Y %I:%M %p"),
        "asset_tag": _text(equipment["asset_tag"]) if equipment else "",
        "action": _text(row["action"]),
        "operator": _display_user(operator),
        "details": details,
    }


def _write_inventory_audit(equipment, action, operator, **values):
    audit_values = {
        "timestamp": datetime.now(anvil.tz.UTC),
        "equipment": equipment,
        "action": action,
        "operator": operator,
        "details": _text(values.get("details")),
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
            app_tables.Inventory_Equipment_Statuses.add_row(
                name=name, description=description, active=True
            )


@anvil.server.callable
def get_inventory(session_token):
    user, error = _require_auth(session_token)
    if error:
        return error
    assert user is not None
    _ensure_default_statuses()
    equipment = sorted(
        (_equipment_payload(row) for row in app_tables.Inventory_Equipment.search()),
        key=lambda item: item["asset_tag"],
    )
    statuses = sorted(
        (_text(row["name"]) for row in app_tables.Inventory_Equipment_Statuses.search() if row["active"] is not False),
        key=str.upper,
    )
    users = sorted(
        (
            {"username": _text(row["username"]), "name": _display_user(row)}
            for row in app_tables.Core_Users.search()
            if row["enabled"] is not False
        ),
        key=lambda item: item["name"].upper(),
    )
    audits = sorted(
        (_audit_payload(row) for row in app_tables.Inventory_Audit_Logs.search()),
        key=lambda item: item["timestamp"],
        reverse=True,
    )[:100]
    return {
        "success": True,
        "equipment": equipment,
        "statuses": statuses,
        "users": users,
        "audits": audits,
        "can_manage": bool(_text(user["role"]).lower() == "admin"),
    }


@anvil.server.callable
def add_equipment(asset_tag, category, manufacturer, model, serial_number, location, status_name, notes, session_token):
    user, error = _require_admin(session_token)
    if error:
        return error
    asset_tag = _upper(asset_tag)
    category = _text(category)
    if not asset_tag or not category:
        return {"success": False, "message": "Asset tag and category are required."}
    if _equipment_by_tag(asset_tag):
        return {"success": False, "message": "That asset tag already exists."}
    status = _status_by_name(status_name)
    if not status:
        return {"success": False, "message": "Select a valid inventory status."}
    assert user is not None
    now = datetime.now(anvil.tz.UTC)
    equipment = app_tables.Inventory_Equipment.add_row(
        asset_tag=asset_tag,
        category=category,
        manufacturer=_text(manufacturer),
        model=_text(model),
        serial_number=_text(serial_number),
        location=_text(location),
        status=status,
        notes=_text(notes),
        created_at=now,
        updated_at=now,
    )
    _write_inventory_audit(equipment, "CREATED", user, new_status=status, details="Equipment added")
    return {"success": True, "message": "Equipment added."}


@anvil.server.callable
def transfer_equipment(asset_tag, username, notes, session_token):
    operator, error = _require_admin(session_token)
    if error:
        return error
    equipment = _equipment_by_tag(asset_tag)
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
            assigned_at=now, assigned_by=operator, notes=_text(notes),
        )
    else:
        app_tables.Inventory_Equipment_Assignments.add_row(
            equipment=equipment, to_user=target, assigned_at=now,
            assigned_by=operator, notes=_text(notes),
        )
    _write_inventory_audit(
        equipment, "TRANSFERRED", operator, from_user=previous, to_user=target,
        old_status=old_status, new_status=assigned_status or old_status,
        details=_text(notes),
    )
    return {"success": True, "message": "Equipment transferred."}


@anvil.server.callable
def update_equipment_status(asset_tag, status_name, notes, session_token):
    operator, error = _require_admin(session_token)
    if error:
        return error
    equipment = _equipment_by_tag(asset_tag)
    status = _status_by_name(status_name)
    if not equipment or not status:
        return {"success": False, "message": "Select existing equipment and a valid status."}
    old_status = equipment["status"]
    now = datetime.now(anvil.tz.UTC)
    equipment["status"] = status
    equipment["updated_at"] = now
    _write_inventory_audit(
        equipment, "STATUS CHANGED", operator, old_status=old_status,
        new_status=status, details=_text(notes),
    )
    return {"success": True, "message": "Equipment status updated."}
