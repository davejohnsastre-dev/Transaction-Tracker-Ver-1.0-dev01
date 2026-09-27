import base64
import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta
from uuid import uuid4

import anvil.http
import anvil.server
import anvil.tz
from anvil.tables import app_tables


EXCLUDED_COLUMNS = {"password"}
GUEST_USERNAME = "guest"
PASSWORD_HASH_ALGORITHM = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 310000
PASSWORD_MIN_LENGTH = 8
SESSION_LIFETIME = timedelta(hours=8)


PROVIDED_TRANSACTIONS = (
    {
        "date": "2026/06/25", "tdn": "2023-07-0002-00135", "pin": "063-07-0002-001-04",
        "owner": "FLORIFES T. VERGARA; GLENDA T. LINGAYA; JOSE A. TAGHOY, JR. AND DARBY A. TAGHOY",
        "lot_no": "6531-A-1", "transaction_type": "SEGREGATION", "requestor": "l", "contact_info": "l",
        "encoder": "ASSESSOR", "status": "COMPLETED", "remarks": "", "activity": "",
    },
    {
        "date": "2026/06/25", "tdn": "2023-07-0002-00133", "pin": "063-07-0002-001-02",
        "owner": "JOSE TAGHOY", "lot_no": "6531-C", "transaction_type": "SEGREGATION", "requestor": "l", "contact_info": "l",
        "encoder": "ASSESSOR", "status": "FOR INSPECTION", "remarks": "", "activity": "",
    },
    {
        "date": "2026/06/25", "tdn": "2023-07-0002-00001", "pin": "063-07-0002-001-01",
        "owner": "REPUBLIC OF THE PHILIPPINES", "lot_no": "", "transaction_type": "SEGREGATION", "requestor": "DAVE JOHN SASTRE", "contact_info": "9569912810",
        "encoder": "ASSESSOR", "status": "", "remarks": "", "activity": "",
    },
    {
        "date": "2026/07/03", "tdn": "2023-07-0001-00137", "pin": "063-07-0001-003-38",
        "owner": "MUNICIPALITY OF STO. TOMAS", "lot_no": "2562-A", "transaction_type": "SEGREGATION", "requestor": "masso", "contact_info": "masso",
        "encoder": "ASSESSOR", "status": "", "remarks": "", "activity": "",
    },
    {
        "date": "2026/07/03", "tdn": "2023-07-0001-00139", "pin": "063-07-0001-003-40",
        "owner": "JULIUS ROY R. TORRES", "lot_no": "2562-B-2", "transaction_type": "TRANSFER", "requestor": "anna", "contact_info": "123456+97",
        "encoder": "ASSESSOR", "status": "INSPECTED", "remarks": "", "activity": "[Jul 03, 2026 15:52] Updated by ASSESSOR",
    },
    {
        "date": "2026/07/03", "tdn": "2023-07-0001-06058", "pin": "063-07-0001-073-21",
        "owner": "DARIO ROMANO", "lot_no": "22 10", "transaction_type": "SEGREGATION", "requestor": "NANETTE G. DAZON", "contact_info": "SADSADASD",
        "encoder": "ASSESSOR", "status": "TO PROCESS", "remarks": "test", "activity": "[Jul 03, 2026 16:04] Updated by ASSESSOR",
    },
    {
        "date": "2026/07/03", "tdn": "2023-07-0019-00001", "pin": "063-07-0019-001-01",
        "owner": "EMILIO CARTAS", "lot_no": "48", "transaction_type": "SEGREGATION", "requestor": "riza bagohin", "contact_info": "1321654651",
        "encoder": "ASSESSOR", "status": "FOR APPROVAL", "remarks": "txn ############", "activity": "[Jul 03, 2026 16:09] Updated by ASSESSOR",
    },
    {
        "date": "2026/07/03", "tdn": "2023-07-0019-00013", "pin": "063-07-0019-001-13",
        "owner": "DIONESIO SUMI-OG", "lot_no": "74", "transaction_type": "SEGREGATION", "requestor": "xxxxxxxxxx", "contact_info": "xxxxxxxxxx",
        "encoder": "ASSESSOR", "status": "FOR INSPECTION", "remarks": "", "activity": "[Jul 03, 2026 16:10] Created by ASSESSOR",
    },
    {
        "date": "2026/07/03", "tdn": "2023-07-0015-00614", "pin": "063-07-0015-022-02",
        "owner": "ILUMINADA ALCORIZA, VDA. DE", "lot_no": "4 SGS-11-001223-D", "transaction_type": "SEGREGATION", "requestor": "alcoriza", "contact_info": "1234",
        "encoder": "CHERRY DAWN I. JADRAQUE", "status": "COMPLETED", "remarks": "bunal", "activity": "[Jul 03, 2026 16:44] Updated by ASSESSOR",
    },
    {
        "date": "2026/07/06", "tdn": "2023-07-0007-00320", "pin": "063-07-0007-011-12",
        "owner": "GROW FRESH AGRIVENTURES CORP", "lot_no": "1040-E-1", "transaction_type": "SEGREGATION", "requestor": "ME", "contact_info": "ME",
        "encoder": "DAVE JOHN T. SASTRE", "status": "FOR INSPECTION", "remarks": "", "activity": "[Jul 06, 2026 13:53] Created by DAVE JOHN T. SASTRE",
    },
    {
        "date": "2026/07/06", "tdn": "2023-07-0001-03635", "pin": "063-07-0001-046-42",
        "owner": "HLC CONSTRUCTION AND DEVELOPMENT CORPORATION", "lot_no": "2 7", "transaction_type": "SEGREGATION", "requestor": "me", "contact_info": "me",
        "encoder": "DAVE JOHN T. SASTRE", "status": "INSPECTED", "remarks": "", "activity": "[Jul 06, 2026 14:56] Created by DAVE JOHN T. SASTRE",
    },
    {
        "date": "2026/07/06", "tdn": "2023-07-0001-16388", "pin": "063-07-0001-047-65",
        "owner": "PERLY A. TOGONON", "lot_no": "20 7", "transaction_type": "SEGREGATION", "requestor": "YOU", "contact_info": "YOU",
        "encoder": "DAVE JOHN T. SASTRE", "status": "FOR INSPECTION", "remarks": "", "activity": "[JUL 06, 2026 15:01] CREATED BY DAVE JOHN T. SASTRE",
    },
    {
        "date": "2026/07/06", "tdn": "2023-07-0001-03908", "pin": "063-07-0001-048-08-1001",
        "owner": "HLC CONSTRUCTION AND DEVELOPMENT CORPORATION", "lot_no": "", "transaction_type": "CANCELLATION", "requestor": "TEST11", "contact_info": "TEST11",
        "encoder": "DAVE JOHN T. SASTRE", "status": "FOR INSPECTION", "remarks": "", "activity": "[JUL 06, 2026 15:39] CREATED BY DAVE JOHN T. SASTRE",
    },
    {
        "date": "2026/07/06", "tdn": "2023-07-0015-15046", "pin": "063-07-0015-200-01",
        "owner": "MARSMAN ESTATE PLANTATION, INC", "lot_no": "C-23", "transaction_type": "TRANSFER", "requestor": "XXX", "contact_info": "XXX",
        "encoder": "RIZA D. BAGOHIN", "status": "TO PROCESS", "remarks": "", "activity": "[JUL 06, 2026 16:40] CREATED BY RIZA D. BAGOHIN",
    },
)


def _text(value):
    return "" if value is None else str(value).strip()


def _upper(value):
    return _text(value).upper()


def _formatted_date(value=None):
    value = value or datetime.now(anvil.tz.UTC)
    return value.strftime("%b %d, %Y %I:%M %p")


def _display_datetime(value):
    return _formatted_date(value) if value else "Never"


def _hash_device_token(token):
    return hashlib.sha256(_text(token).encode("utf-8")).hexdigest()


def _hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        _text(password).encode("utf-8"),
        salt,
        PASSWORD_HASH_ITERATIONS,
    )
    return "$".join(
        (
            PASSWORD_HASH_ALGORITHM,
            str(PASSWORD_HASH_ITERATIONS),
            base64.urlsafe_b64encode(salt).decode("ascii"),
            base64.urlsafe_b64encode(digest).decode("ascii"),
        )
    )


def _verify_password(password, stored_hash):
    try:
        algorithm, iterations, encoded_salt, encoded_digest = _text(stored_hash).split("$", 3)
        iterations = int(iterations)
        if algorithm != PASSWORD_HASH_ALGORITHM or not 100000 <= iterations <= 1000000:
            return False
        salt = base64.urlsafe_b64decode(encoded_salt.encode("ascii"))
        expected_digest = base64.urlsafe_b64decode(encoded_digest.encode("ascii"))
    except (ValueError, TypeError):
        return False
    actual_digest = hashlib.pbkdf2_hmac(
        "sha256",
        _text(password).encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(actual_digest, expected_digest)


def _set_password_hash(user, password):
    user["password_hash"] = _hash_password(password)
    user["password"] = ""


def _migrate_legacy_passwords():
    """Hash and clear any remaining legacy plaintext password values."""
    migrated = 0
    for user in app_tables.Core_Users.search():
        legacy_password = _text(user["password"])
        if not legacy_password:
            continue
        if not _text(user["password_hash"]):
            _set_password_hash(user, legacy_password)
        else:
            # The hash is authoritative; remove a stale plaintext copy.
            user["password"] = ""
        migrated += 1
    return migrated


def _validate_password(password):
    password = _text(password)
    if len(password) < PASSWORD_MIN_LENGTH:
        return "Password must be at least %s characters long." % PASSWORD_MIN_LENGTH
    if len(password) > 256:
        return "Password must be 256 characters or fewer."
    return None


def _ensure_user_role(user):
    role = _text(user.get("role")).lower()
    if role not in {"admin", "user"}:
        # Authorization must come from the server-side role field, never a
        # special username. Unknown legacy roles receive least privilege.
        role = "user"
        user["role"] = role
    return role


def _user_role(user):
    if _is_read_only_user(user):
        return "viewer"
    return _ensure_user_role(user)


def _create_session(user):
    raw_token = secrets.token_urlsafe(32)
    now = datetime.now(anvil.tz.UTC)
    app_tables.Core_Auth_Sessions.add_row(
        token_hash=_hash_device_token(raw_token),
        username=_text(user.get("username")),
        created_at=now,
        expires_at=now + SESSION_LIFETIME,
    )
    return raw_token


def _find_session(token):
    token = _text(token)
    if not token:
        return None
    token_hash = _hash_device_token(token)
    now = datetime.now(anvil.tz.UTC)
    for session in app_tables.Core_Auth_Sessions.search():
        if not hmac.compare_digest(_text(session["token_hash"]), token_hash):
            continue
        if session["revoked_at"] or not session["expires_at"] or session["expires_at"] <= now:
            return None
        if _text(session["username"]).lower() == GUEST_USERNAME:
            # Invalidate sessions created by the removed guest login path.
            if not session["revoked_at"]:
                session["revoked_at"] = datetime.now(anvil.tz.UTC)
            return None
        user = _find_user(session["username"])
        if user:
            _ensure_user_role(user)
        return user
    return None


def _revoke_session(token):
    token = _text(token)
    if not token:
        return None
    token_hash = _hash_device_token(token)
    for session in app_tables.Core_Auth_Sessions.search():
        if hmac.compare_digest(_text(session["token_hash"]), token_hash):
            if not session["revoked_at"]:
                session["revoked_at"] = datetime.now(anvil.tz.UTC)
            return session
    return None


def _revoke_user_sessions(username, except_token=None):
    target_username = _text(username).lower()
    except_hash = _hash_device_token(except_token) if _text(except_token) else ""
    now = datetime.now(anvil.tz.UTC)
    for session in app_tables.Core_Auth_Sessions.search():
        if _text(session["username"]).lower() != target_username:
            continue
        if except_hash and hmac.compare_digest(_text(session["token_hash"]), except_hash):
            continue
        if not session["revoked_at"]:
            session["revoked_at"] = now


def _new_slip_id(value=None):
    value = value or datetime.now(anvil.tz.UTC)
    return "SLIP-%s-%s" % (value.strftime("%Y%m%d%H%M%S"), uuid4().hex[:8].upper())


def _qr_code_media(slip_id, app_origin):
    app_origin = _text(app_origin).rstrip("/")
    if not app_origin:
        return None
    verification_url = "%s?verify=%s" % (app_origin, _text(slip_id))
    qr_url = (
        "https://api.qrserver.com/v1/create-qr-code/?size=260x260&margin=8&data=%s"
        % anvil.http.url_encode(verification_url)
    )
    return anvil.http.request(qr_url, timeout=20)


def _find_user(username):
    target = _text(username).lower()
    for row in app_tables.Core_Users.search():
        if _text(row["username"]).lower() == target and row["enabled"]:
            return row
    return None


def _authenticate(username, pin):
    username = _text(username).lower()
    if username == GUEST_USERNAME:
        return None
    user = _find_user(username)
    if not user:
        return None
    if _verify_password(pin, _text(user["password_hash"])):
        _ensure_user_role(user)
        migrated = _migrate_legacy_passwords()
        if migrated:
            _write_security_audit(user["username"], "Migrated %s legacy password record(s) to password hashes." % migrated)
        return user
    # Upgrade legacy plaintext credentials after a successful login.
    if _text(user["password"]) and hmac.compare_digest(_text(user["password"]), _text(pin)):
        _set_password_hash(user, pin)
        _ensure_user_role(user)
        migrated = _migrate_legacy_passwords()
        if migrated:
            _write_security_audit(user["username"], "Migrated %s legacy password record(s) to password hashes." % migrated)
        return user
    return None


def _is_read_only_user(user):
    return bool(user and user.get("read_only", False))


def _auth_failure():
    return {"success": False, "message": "Access Denied: Invalid User Name or Password."}


@anvil.server.callable
def verify_user_credentials(username, pin):
    user = _authenticate(username, pin)
    if not user:
        _write_security_audit(_text(username) or "UNKNOWN", "Login failed.")
        return _auth_failure()
    assert user is not None
    return _create_login_response(user)


def _create_login_response(user):
    session_token = _create_session(user)
    _write_security_audit(_text(user["username"]), "Login succeeded.")
    return {
        "success": True,
        "username": _text(user["username"]),
        "employeeName": _upper(user["employee_name"]),
        "readOnly": _is_read_only_user(user),
        "role": _user_role(user),
        "sessionToken": session_token,
    }


@anvil.server.callable
def verify_user_credentials_for_registered_device(username, pin, device_token):
    device = _find_registered_device(device_token)
    if device is None:
        _write_security_audit(
            _text(username) or "UNKNOWN",
            "Login failed from an unregistered device.",
        )
        return {
            "success": False,
            "message": "Secure login is available only on a registered device.",
        }
    device["last_seen_at"] = datetime.now(anvil.tz.UTC)

    user = _authenticate(username, pin)
    if not user:
        _write_security_audit(_text(username) or "UNKNOWN", "Login failed.")
        return _auth_failure()
    return _create_login_response(user)


@anvil.server.callable
def logout_session(session_token):
    session = _revoke_session(session_token)
    if session:
        _write_security_audit(_text(session["username"]), "Logout completed.")
    return {"success": True}


@anvil.server.callable
def update_user_pin(session_token, old_pin, new_pin):
    user, error = _require_auth(session_token)
    if error:
        return error
    assert user is not None
    if _is_read_only_user(user):
        return {"success": False, "message": "Read-only accounts cannot change passwords."}
    if not _authenticate(user["username"], old_pin):
        return {"success": False, "message": "Incorrect Current Password."}
    password_error = _validate_password(new_pin)
    if password_error:
        return {"success": False, "message": password_error}
    _set_password_hash(user, new_pin)
    _revoke_user_sessions(user["username"], except_token=session_token)
    _write_security_audit(user["username"], "Password changed.")
    return {"success": True, "message": "Password successfully updated."}


def _require_auth(session_token):
    user = _find_session(session_token)
    if not user:
        return None, {"success": False, "message": "Your session is no longer authorized."}
    return user, None


def _is_admin_user(user):
    return bool(
        user
        and not _is_read_only_user(user)
        and _text(user.get("role")).lower() == "admin"
    )


def _require_admin(session_token):
    user, error = _require_auth(session_token)
    if error:
        return None, error
    if not _is_admin_user(user):
        return None, {"success": False, "message": "Administrator access is required."}
    return user, None


def _find_registered_device(token):
    token = _text(token)
    if not token:
        return None
    token_hash = _hash_device_token(token)
    for row in app_tables.Core_Registered_Devices.search():
        if not row["enabled"]:
            continue
        if hmac.compare_digest(_text(row["token_hash"]), token_hash):
            return row
    return None


def _verification_settings_row():
    for row in app_tables.Core_Verification_Settings.search():
        return row
    return None


def _device_token_required():
    row = _verification_settings_row()
    if row is None or row["device_token_required"] is None:
        return True
    return bool(row["device_token_required"])


@anvil.server.callable
def get_admin_settings(session_token):
    user, error = _require_admin(session_token)
    if error:
        return error
    del user

    users = []
    for row in app_tables.Core_Users.search():
        users.append({
            "id": row.get_id(),
            "setting_type": "users",
            "label": _upper(row["username"]),
                "username": _text(row["username"]),
                "employee_name": _upper(row["employee_name"]),
                "enabled": bool(row["enabled"]),
                "role": _user_role(row),
            "detail": "%s · %s" % (
                _upper(row["employee_name"]),
                "ENABLED" if row["enabled"] else "DISABLED",
            ),
        })

    statuses = []
    for row in app_tables.Tracker_Statuses.search():
        name = _upper(row["name"])
        if name:
            statuses.append({
                "id": row.get_id(),
                "setting_type": "statuses",
                "label": name,
                "name": name,
                "detail": "Status option",
            })

    transaction_types = []
    for row in app_tables.Tracker_Transaction_Types.search():
        name = _upper(row["transaction_name"])
        if name:
            transaction_types.append({
                "id": row.get_id(),
                "setting_type": "types",
                "label": name,
                "name": name,
                "code": _upper(row["transaction_code"]),
                "detail": _upper(row["transaction_code"]) or "No code",
            })

    users.sort(key=lambda item: item["label"])
    statuses.sort(key=lambda item: item["label"])
    transaction_types.sort(key=lambda item: item["label"])
    devices = []
    for row in app_tables.Core_Registered_Devices.search():
        device_name = _text(row["device_name"]) or "Unnamed device"
        enabled = bool(row["enabled"])
        devices.append({
            "id": row.get_id(),
            "setting_type": "devices",
            "label": device_name,
            "device_name": device_name,
            "enabled": enabled,
            "status": "ENABLED" if enabled else "REVOKED",
            "last_seen": _display_datetime(row["last_seen_at"]),
            "detail": "%s · Last used: %s" % (
                "ENABLED" if enabled else "REVOKED",
                _display_datetime(row["last_seen_at"]),
            ),
        })

    devices.sort(key=lambda item: item["label"].lower())
    return {
        "success": True,
        "users": users,
        "statuses": statuses,
        "transaction_types": transaction_types,
        "devices": devices,
        "device_token_required": _device_token_required(),
    }


@anvil.server.callable
def admin_register_device(device_name, session_token):
    user, error = _require_admin(session_token)
    if error:
        return error
    assert user is not None

    device_name = _text(device_name)
    if not device_name:
        return {"success": False, "message": "A device name is required."}
    if len(device_name) > 120:
        return {"success": False, "message": "The device name must be 120 characters or fewer."}

    raw_token = secrets.token_urlsafe(32)
    app_tables.Core_Registered_Devices.add_row(
        device_name=device_name,
        token_hash=_hash_device_token(raw_token),
        enabled=True,
        registered_at=datetime.now(anvil.tz.UTC),
    )
    _write_security_audit(user["username"], "Registered device '%s'." % device_name)
    return {
        "success": True,
        "message": "Device registered. This browser can now verify QR codes.",
        "token": raw_token,
    }


@anvil.server.callable
def admin_revoke_device(device_id, session_token):
    user, error = _require_admin(session_token)
    if error:
        return error
    assert user is not None

    row = app_tables.Core_Registered_Devices.get_by_id(_text(device_id))
    if row is None:
        return {"success": False, "message": "The selected device was not found."}
    row["enabled"] = False
    _write_security_audit(user["username"], "Revoked device '%s'." % _text(row["device_name"]))
    return {"success": True, "message": "Device access revoked."}


@anvil.server.callable
def admin_set_device_token_requirement(required, session_token):
    user, error = _require_admin(session_token)
    if error:
        return error
    assert user is not None

    required = bool(required)
    row = _verification_settings_row()
    if row is None:
        app_tables.Core_Verification_Settings.add_row(
            device_token_required=required,
            updated_at=datetime.now(anvil.tz.UTC),
        )
    else:
        row.update(device_token_required=required, updated_at=datetime.now(anvil.tz.UTC))
    if required:
        message = "Registered device tokens are now required for QR verification."
    else:
        message = "QR verification is now open to the public without a device token."
    _write_security_audit(user["username"], "Set QR device-token requirement to %s." % required)
    return {"success": True, "message": message, "device_token_required": required}


@anvil.server.callable
def admin_register_user(username, employee_name, password, session_token, enabled=True):
    user, error = _require_admin(session_token)
    if error:
        return error
    assert user is not None

    username = _text(username).lower()
    employee_name = _upper(employee_name)
    password = _text(password)
    password_changed = bool(password)
    password_error = _validate_password(password)
    if password_error:
        return {"success": False, "message": password_error}
    if not username or not employee_name:
        return {"success": False, "message": "Username, employee name, and password are required."}
    if not re.fullmatch(r"[a-z0-9._-]{3,64}", username):
        return {"success": False, "message": "Username must be 3-64 lowercase letters, numbers, dots, underscores, or hyphens."}
    if len(employee_name) > 160:
        return {"success": False, "message": "Employee name must be 160 characters or fewer."}
    if username == GUEST_USERNAME:
        return {"success": False, "message": "The guest username is reserved."}
    if any(_text(row["username"]).lower() == username for row in app_tables.Core_Users.search()):
        return {"success": False, "message": "That username is already registered."}

    app_tables.Core_Users.add_row(
        username=username,
        employee_name=employee_name,
        password="",
        password_hash=_hash_password(password),
        enabled=bool(enabled),
        role="user",
    )
    _write_security_audit(user["username"], "Registered user '%s'." % username)
    return {"success": True, "message": "User registered successfully."}


@anvil.server.callable
def admin_update_user(user_id, employee_name, password, session_token, enabled=True):
    user, error = _require_admin(session_token)
    if error:
        return error
    assert user is not None

    row = app_tables.Core_Users.get_by_id(_text(user_id))
    if row is None:
        return {"success": False, "message": "The selected user was not found."}
    employee_name = _upper(employee_name)
    password = _text(password)
    password_changed = bool(password)
    if not employee_name:
        return {"success": False, "message": "Employee name is required."}
    if len(employee_name) > 160:
        return {"success": False, "message": "Employee name must be 160 characters or fewer."}
    if password:
        password_error = _validate_password(password)
        if password_error:
            return {"success": False, "message": password_error}
    row.update(employee_name=employee_name, enabled=bool(enabled))
    if password:
        _set_password_hash(row, password)
        _revoke_user_sessions(row["username"])
    detail = "Updated user '%s'%s." % (
        _text(row["username"]),
        " (password changed)" if password_changed else "",
    )
    _write_security_audit(user["username"], detail)
    return {"success": True, "message": "User updated successfully."}


@anvil.server.callable
def admin_add_status(name, session_token):
    user, error = _require_admin(session_token)
    if error:
        return error
    assert user is not None

    name = _upper(name)
    if not name:
        return {"success": False, "message": "A status name is required."}
    if len(name) > 80:
        return {"success": False, "message": "Status name must be 80 characters or fewer."}
    if any(_upper(row["name"]) == name for row in app_tables.Tracker_Statuses.search()):
        return {"success": False, "message": "That status already exists."}

    app_tables.Tracker_Statuses.add_row(name=name)
    _write_security_audit(user["username"], "Added status '%s'." % name)
    return {"success": True, "message": "Status added successfully."}


@anvil.server.callable
def admin_update_status(status_id, name, session_token):
    user, error = _require_admin(session_token)
    if error:
        return error
    assert user is not None

    row = app_tables.Tracker_Statuses.get_by_id(_text(status_id))
    if row is None:
        return {"success": False, "message": "The selected status was not found."}
    name = _upper(name)
    if not name:
        return {"success": False, "message": "A status name is required."}
    if len(name) > 80:
        return {"success": False, "message": "Status name must be 80 characters or fewer."}
    if any(
        candidate.get_id() != row.get_id() and _upper(candidate["name"]) == name
        for candidate in app_tables.Tracker_Statuses.search()
    ):
        return {"success": False, "message": "That status already exists."}
    row["name"] = name
    _write_security_audit(user["username"], "Updated status '%s'." % name)
    return {"success": True, "message": "Status updated successfully."}


@anvil.server.callable
def admin_add_transaction_type(name, code, session_token):
    user, error = _require_admin(session_token)
    if error:
        return error
    assert user is not None

    name = _upper(name)
    code = _upper(code)
    if not name:
        return {"success": False, "message": "A transaction type name is required."}
    if len(name) > 80 or len(code) > 40:
        return {"success": False, "message": "Transaction type names must be 80 characters or fewer and codes 40 characters or fewer."}
    if any(_upper(row["transaction_name"]) == name for row in app_tables.Tracker_Transaction_Types.search()):
        return {"success": False, "message": "That transaction type already exists."}
    if code and any(_upper(row["transaction_code"]) == code for row in app_tables.Tracker_Transaction_Types.search()):
        return {"success": False, "message": "That transaction type code already exists."}

    app_tables.Tracker_Transaction_Types.add_row(transaction_name=name, transaction_code=code)
    _write_security_audit(user["username"], "Added transaction type '%s'." % name)
    return {"success": True, "message": "Transaction type added successfully."}


@anvil.server.callable
def admin_update_transaction_type(type_id, name, code, session_token):
    user, error = _require_admin(session_token)
    if error:
        return error
    assert user is not None

    row = app_tables.Tracker_Transaction_Types.get_by_id(_text(type_id))
    if row is None:
        return {"success": False, "message": "The selected transaction type was not found."}
    name = _upper(name)
    code = _upper(code)
    if not name:
        return {"success": False, "message": "A transaction type name is required."}
    if len(name) > 80 or len(code) > 40:
        return {"success": False, "message": "Transaction type names must be 80 characters or fewer and codes 40 characters or fewer."}
    if any(
        candidate.get_id() != row.get_id()
        and _upper(candidate["transaction_name"]) == name
        for candidate in app_tables.Tracker_Transaction_Types.search()
    ):
        return {"success": False, "message": "That transaction type already exists."}
    if code and any(
        candidate.get_id() != row.get_id()
        and _upper(candidate["transaction_code"]) == code
        for candidate in app_tables.Tracker_Transaction_Types.search()
    ):
        return {"success": False, "message": "That transaction type code already exists."}
    row.update(transaction_name=name, transaction_code=code)
    _write_security_audit(user["username"], "Updated transaction type '%s'." % name)
    return {"success": True, "message": "Transaction type updated successfully."}


@anvil.server.callable
def get_transaction_types(session_token):
    user, error = _require_auth(session_token)
    if error:
        return error
    del user
    values = [_upper(row["transaction_name"]) for row in app_tables.Tracker_Transaction_Types.search()]
    return {"success": True, "values": [value for value in values if value]}


@anvil.server.callable
def get_status_types(session_token):
    user, error = _require_auth(session_token)
    if error:
        return error
    del user
    values = [_upper(row["name"]) for row in app_tables.Tracker_Statuses.search()]
    return {"success": True, "values": [value for value in values if value]}


def _transaction_dict(row):
    slip = row["transaction_slip"]
    if slip:
        slip_id = slip["slip_id"]
        requestor = slip["requestor"]
        requestor_info = slip["requestor_info"]
    else:
        # These legacy values remain until the one-time backfill has run.
        slip_id = row["slip_id"]
        requestor = row["requestor"]
        requestor_info = row["requestor_info"]
    return {
        "id": row.get_id(),
        "slip_id": _upper(slip_id),
        "created_at": _formatted_date(row["created_at"]),
        "tdn": _upper(row["tdn"]),
        "pin": _upper(row["pin"]),
        "owner": _upper(row["owner"]),
        "lot_no": _upper(row["lot_no"]),
        "transaction_type": _upper(row["transaction_type"]),
        "requestor": _upper(requestor),
        "requestor_info": _upper(requestor_info),
        "contact_person": _upper(row["contact_person"]),
        "contact_person_info": _upper(row["contact_person_info"]),
        "encoder": _upper(row["encoder"]),
        "status": _upper(row["status"]),
        "remarks": _upper(row["remarks"]),
        "latest_activity": _upper(row["latest_activity"]),
    }


def _link_legacy_transaction(row):
    if row["transaction_slip"]:
        return row["transaction_slip"]

    legacy_slip_id = _upper(row["slip_id"])
    slip = None
    if legacy_slip_id:
        for candidate in app_tables.Tracker_Transaction_Slips.search(slip_id=legacy_slip_id):
            if (
                _upper(candidate["requestor"]) == _upper(row["requestor"])
                and _upper(candidate["requestor_info"]) == _upper(row["requestor_info"])
            ):
                slip = candidate
                break
    if slip is None:
        slip = app_tables.Tracker_Transaction_Slips.add_row(
            slip_id=legacy_slip_id,
            requestor=_upper(row["requestor"]),
            requestor_info=_upper(row["requestor_info"]),
        )
    row["transaction_slip"] = slip
    return slip


@anvil.server.callable
def get_spreadsheet_data(session_token):
    user, error = _require_auth(session_token)
    if error:
        return error
    del user
    rows = []
    for row in app_tables.Tracker_Transactions.search():
        if not (_text(row["tdn"]) or _text(row["pin"]) or _text(row["owner"])):
            continue
        _link_legacy_transaction(row)
        rows.append((row["created_at"], _transaction_dict(row)))
    rows.sort(key=lambda item: item[0], reverse=True)
    return {"success": True, "records": [item[1] for item in rows]}


def _transaction_slip_records_payload(slip_id):
    target_slip_id = _upper(slip_id)
    if not target_slip_id:
        return {"success": False, "message": "This transaction has no slip ID to print."}

    slip = None
    for candidate in app_tables.Tracker_Transaction_Slips.search():
        if _upper(candidate["slip_id"]) == target_slip_id:
            slip = candidate
            break
    if slip is None:
        return {"success": False, "message": "The transaction slip was not found in the database."}

    slip_id_value = _upper(slip["slip_id"])
    child_rows = []
    for row in app_tables.Tracker_Transactions.search():
        linked_slip = row["transaction_slip"]
        linked_to_slip = linked_slip is not None and linked_slip.get_id() == slip.get_id()
        legacy_linked_to_slip = linked_slip is None and _upper(row["slip_id"]) == slip_id_value
        if linked_to_slip or legacy_linked_to_slip:
            child_rows.append((row["created_at"], _transaction_dict(row)))
    child_rows.sort(key=lambda item: item[0] or datetime.min.replace(tzinfo=anvil.tz.UTC))

    return {
        "success": True,
        "slip": {
            "slip_id": slip_id_value,
            "requestor": _upper(slip["requestor"]),
            "requestor_info": _upper(slip["requestor_info"]),
            "qr_code": slip["qr_code"],
        },
        "records": [item[1] for item in child_rows],
    }


@anvil.server.callable
def get_transaction_slip_records(slip_id, session_token):
    user, error = _require_auth(session_token)
    if error:
        return error
    if _is_read_only_user(user) and _device_token_required():
        return {
            "success": False,
            "message": "QR verification requires a registered device token.",
        }
    return _transaction_slip_records_payload(slip_id)


@anvil.server.callable
def get_transaction_slip_records_for_device(slip_id, device_token):
    device = _find_registered_device(device_token)
    if device is None:
        return {
            "success": False,
            "message": "This device is not registered for QR verification.",
        }
    device["last_seen_at"] = datetime.now(anvil.tz.UTC)
    return _transaction_slip_records_payload(slip_id)


@anvil.server.callable
def get_transaction_slip_records_for_qr(slip_id, device_token=""):
    if not _device_token_required():
        return _transaction_slip_records_payload(slip_id)

    device = _find_registered_device(device_token)
    if device is None:
        return {
            "success": False,
            "message": "This device is not registered for QR verification.",
        }
    device["last_seen_at"] = datetime.now(anvil.tz.UTC)
    return _transaction_slip_records_payload(slip_id)


def _write_audit_log(tdn, operator, details):
    app_tables.Tracker_Audit_Logs.add_row(
        timestamp=datetime.now(anvil.tz.UTC),
        tdn=_upper(tdn),
        operator=_upper(operator),
        details=_upper(details),
    )


def _write_security_audit(operator, details):
    _write_audit_log("", operator, details)


def _reference_value_exists(table, column, value):
    target = _upper(value)
    return any(_upper(row[column]) == target for row in table.search())


def _find_transaction_by_tdn(tdn):
    target = _upper(tdn)
    for row in app_tables.Tracker_Transactions.search():
        if _upper(row["tdn"]) == target:
            return row
    return None


def _add_provided_audit_log(tdn, activity):
    activity = _upper(activity)
    if not activity:
        return False
    for row in app_tables.Tracker_Audit_Logs.search():
        if _upper(row["tdn"]) == _upper(tdn) and _upper(row["details"]) == activity:
            return False
    match = re.match(r"^\[([^\]]+)\].*?\bBY\s+(.+)$", activity, re.I)
    if not match:
        return False
    timestamp = datetime.strptime(match.group(1).title(), "%b %d, %Y %H:%M")
    app_tables.Tracker_Audit_Logs.add_row(
        timestamp=timestamp,
        tdn=_upper(tdn),
        operator=_upper(match.group(2)),
        details=activity,
    )
    return True


@anvil.server.callable
def import_provided_transactions(session_token):
    user, error = _require_auth(session_token)
    if error:
        return error
    if _is_read_only_user(user):
        return {"success": False, "message": "Read-only accounts cannot import transactions."}
    del user

    added = 0
    skipped = 0
    audit_added = 0
    for item in PROVIDED_TRANSACTIONS:
        existing = _find_transaction_by_tdn(item["tdn"])
        if existing:
            skipped += 1
            if item["activity"] and not _text(existing["latest_activity"]):
                existing["latest_activity"] = _upper(item["activity"])
        else:
            created_at = datetime.strptime(item["date"], "%Y/%m/%d")
            slip = app_tables.Tracker_Transaction_Slips.add_row(
                slip_id=_new_slip_id(created_at),
                requestor=_upper(item["requestor"]),
                requestor_info=_upper(item.get("contact_info")),
            )
            app_tables.Tracker_Transactions.add_row(
                created_at=created_at,
                tdn=_upper(item["tdn"]),
                pin=_upper(item["pin"]),
                owner=_upper(item["owner"]),
                lot_no=_upper(item["lot_no"]),
                transaction_type=_upper(item["transaction_type"]),
                contact_person="",
                contact_person_info="",
                encoder=_upper(item["encoder"]),
                status=_upper(item["status"]),
                remarks=_upper(item["remarks"]),
                latest_activity=_upper(item["activity"]),
                transaction_slip=slip,
            )
            added += 1
        if _add_provided_audit_log(item["tdn"], item["activity"]):
            audit_added += 1
    return {
        "success": True,
        "added": added,
        "skipped": skipped,
        "audit_added": audit_added,
        "message": "Imported %s transaction(s) and %s audit log(s); skipped %s existing transaction(s)." % (added, audit_added, skipped),
    }


@anvil.server.callable
def backfill_transaction_slip_ids(session_token, app_origin=None):
    user, error = _require_auth(session_token)
    if error:
        return error
    if _is_read_only_user(user):
        return {"success": False, "message": "Read-only accounts cannot backfill transaction slips."}
    del user

    assigned = 0
    generated_qr_codes = 0
    for row in app_tables.Tracker_Transactions.search():
        slip = row["transaction_slip"]
        if slip is None:
            slip = _link_legacy_transaction(row)
        if slip is not None and not _text(slip["slip_id"]):
            slip["slip_id"] = _new_slip_id()
            assigned += 1
        if slip is not None and app_origin and not slip["qr_code"]:
            slip["qr_code"] = _qr_code_media(slip["slip_id"], app_origin)
            generated_qr_codes += 1

    for slip in app_tables.Tracker_Transaction_Slips.search():
        if not _text(slip["slip_id"]):
            slip["slip_id"] = _new_slip_id()
            assigned += 1
        if app_origin and not slip["qr_code"]:
            slip["qr_code"] = _qr_code_media(slip["slip_id"], app_origin)
            generated_qr_codes += 1

    return {
        "success": True,
        "assigned": assigned,
        "generated_qr_codes": generated_qr_codes,
        "message": "Updated %s slip ID(s) and stored %s QR image(s)." % (assigned, generated_qr_codes),
    }


@anvil.server.callable
def get_record_logs(tdn, session_token):
    user, error = _require_auth(session_token)
    if error:
        return error
    del user
    target = _upper(tdn)
    logs = []
    for row in app_tables.Tracker_Audit_Logs.search():
        if _upper(row["tdn"]) == target:
            logs.append(
                (row["timestamp"], {
                    "timestamp": _formatted_date(row["timestamp"]),
                    "operator": _upper(row["operator"]),
                    "details": _upper(row["details"]),
                })
            )
    logs.sort(key=lambda item: item[0], reverse=True)
    return {"success": True, "logs": [item[1] for item in logs]}


@anvil.server.callable
def parse_raw_text(text, session_token):
    user, error = _require_auth(session_token)
    if error:
        return error
    del user
    text = _text(text)
    if not text:
        return {"success": True, "tdn": "", "pin": "", "owner": "", "lot_no": ""}

    tdn_match = re.search(r"\d{4}-\d{2}-\d{4}-\d{5}", text)
    tdn = _upper(tdn_match.group(0)) if tdn_match else ""

    pin_match = re.search(r"\b\d{3}-\d{2}-\d{4}-[\d()\-]+", text)
    parsed_pin = _upper(pin_match.group(0)) if pin_match else ""
    if parsed_pin.endswith("-"):
        remainder = text.split(parsed_pin, 1)[1] if parsed_pin in text else ""
        trailing_group = re.match(r"^([A-Za-z0-9()]+)", remainder)
        if trailing_group:
            parsed_pin += _upper(trailing_group.group(1))
    if not parsed_pin:
        alternatives = re.findall(r"[\d()\-]{7,}", text)
        alternatives = [item for item in alternatives if item != tdn]
        if alternatives:
            parsed_pin = _upper(alternatives[0])

    type_match = re.search(r"\b(land|structure|machinery|building|improvement)\b", text, re.I)
    owner = ""
    text_after_name = ""
    if parsed_pin and type_match:
        pin_index = text.find(parsed_pin) + len(parsed_pin)
        type_index = type_match.start()
        if type_index > pin_index:
            owner = re.sub(r"\b(TIBAL-OG|FEERER|BRGY|ROW)\b", "", text[pin_index:type_index], flags=re.I)
            owner = _upper(owner)
            text_after_name = text[type_index:]

    if not owner:
        words = re.findall(r"[A-Z\s.,()\-]{5,}", text)
        noise = re.compile(r"\b(CURRENT|CANCELLED|GR|LAND|STRUCTURE|MACHINERY|BUILDING|IMPROVEMENT|TIBAL-OG|FEERER|BRGY|ROW)\b", re.I)
        for word in words:
            clean_word = _upper(noise.sub("", word)).strip()
            if len(re.sub(r"[\s.,()\-]", "", clean_word)) > 4:
                owner = clean_word
                text_after_name = text[text.find(word) + len(word):]
                break
    owner = re.sub(r"^[\s.,\-]+|[\s.,\-]+$", "", _upper(owner))

    lot_no = ""
    if text_after_name and type_match:
        after_type = re.sub(r"^" + re.escape(type_match.group(0)), "", text_after_name, count=1, flags=re.I).strip()
        barangays = r"new katipunan|new visayas|la libertad|san miguel|san jose|san vicente|santa cruz|balagunan|bobongon|esperanza|esperansa|kimamon|kinamayan|marsman|magwawa|pantaron|salvacion|talomo|tibal-og|tibalog|tulalian|lunga-og|lungaog"
        after_type = re.sub(r"^(?:" + barangays + r")\b", "", after_type, count=1, flags=re.I).strip()
        after_type = re.sub(r"^[A-Z]\s+", "", after_type).strip()
        lot_tokens = []
        tokens = after_type.split()
        for index, token in enumerate(tokens):
            upper_token = _upper(token)
            if re.match(r"^(PSD|PCS|CAD|CSD|PLS|GSS|TCT|OCT|EP|CLOA)", upper_token):
                break
            if re.match(r"^(HA|SQM|SQ\.M\.?)$", upper_token):
                if lot_tokens:
                    lot_tokens.pop()
                break
            if re.match(r"^\d+\.\d{2,}$", upper_token) and index + 1 < len(tokens) and re.match(r"^(HA|SQM|SQ\.M\.?)$", _upper(tokens[index + 1])):
                break
            lot_tokens.append(token)
        lot_no = _upper(" ".join(lot_tokens))

    return {"success": True, "tdn": tdn, "pin": parsed_pin, "owner": owner, "lot_no": lot_no}


def _insert_transaction_batch(requestor, requestor_info, transaction_items, user, client_created_at=None, app_origin=None):
    if not isinstance(transaction_items, list) or not transaction_items:
        return {"success": False, "message": "Add at least one transaction item before saving."}
    requestor = _text(requestor)
    requestor_info = _text(requestor_info)
    if len(requestor) > 200 or len(requestor_info) > 200:
        return {"success": False, "message": "Requestor fields must be 200 characters or fewer."}

    normalized_items = []
    for item in transaction_items:
        if not isinstance(item, dict):
            return {"success": False, "message": "Each transaction item must be a valid entry."}
        normalized_item = {
            "tdn": _upper(item.get("tdn")),
            "pin": _upper(item.get("pin")),
            "owner": _upper(item.get("owner")),
            "lot_no": _upper(item.get("lot_no")),
            "transaction_type": _upper(item.get("transaction_type")),
            "contact_person": _upper(item.get("contact_person")),
            "contact_person_info": _upper(item.get("contact_person_info")),
            "status": _upper(item.get("status")),
            "remarks": _upper(item.get("remarks")),
        }
        field_limits = {
            "tdn": 64,
            "pin": 64,
            "owner": 255,
            "lot_no": 120,
            "transaction_type": 80,
            "contact_person": 120,
            "contact_person_info": 200,
            "status": 80,
            "remarks": 1000,
        }
        for field_name, maximum in field_limits.items():
            if len(normalized_item[field_name]) > maximum:
                return {
                    "success": False,
                    "message": "%s must be %s characters or fewer." % (field_name.replace("_", " ").title(), maximum),
                }
        required_fields = (
            normalized_item["tdn"],
            normalized_item["pin"],
            normalized_item["owner"],
            normalized_item["transaction_type"],
            normalized_item["status"],
        )
        if any(not value for value in required_fields):
            return {"success": False, "message": "Every transaction item needs its required fields completed."}
        if not _reference_value_exists(app_tables.Tracker_Transaction_Types, "transaction_name", normalized_item["transaction_type"]):
            return {"success": False, "message": "Select a valid transaction type."}
        if not _reference_value_exists(app_tables.Tracker_Statuses, "name", normalized_item["status"]):
            return {"success": False, "message": "Select a valid transaction status."}
        if _find_transaction_by_tdn(normalized_item["tdn"]):
            return {
                "success": False,
                "message": "TDN %s already exists. Each TDN must be unique." % normalized_item["tdn"],
            }
        if any(item["tdn"] == normalized_item["tdn"] for item in normalized_items):
            return {
                "success": False,
                "message": "TDN %s is duplicated in this transaction slip." % normalized_item["tdn"],
            }
        normalized_items.append(normalized_item)

    now = datetime.now(anvil.tz.UTC)
    slip_id = _new_slip_id(now)
    slip = app_tables.Tracker_Transaction_Slips.add_row(
        slip_id=slip_id,
        requestor=_upper(requestor),
        requestor_info=_upper(requestor_info),
        qr_code=_qr_code_media(slip_id, app_origin),
    )
    activity = "[%s] CREATED BY %s" % (_formatted_date(now), _upper(user["employee_name"]))
    records = []
    for item in normalized_items:
        target_tdn = item["tdn"]
        record = app_tables.Tracker_Transactions.add_row(
            created_at=now,
            tdn=target_tdn,
            pin=item["pin"],
            owner=item["owner"],
            lot_no=item["lot_no"],
            transaction_type=item["transaction_type"],
            contact_person=item["contact_person"],
            contact_person_info=item["contact_person_info"],
            encoder=_upper(user["employee_name"]),
            status=item["status"],
            remarks=item["remarks"],
            latest_activity=activity,
            transaction_slip=slip,
        )
        records.append(_transaction_dict(record))
        _write_audit_log(
            target_tdn,
            user["employee_name"],
            "Initial entry saved. Slip: '%s', Type: '%s', Status: '%s', Remarks: '%s'."
            % (slip_id, item["transaction_type"], item["status"], item["remarks"] or "None"),
        )
    return {"success": True, "slip_id": slip_id, "qr_code": slip["qr_code"], "records": records}


@anvil.server.callable
def process_transaction_batch(requestor, requestor_info, transaction_items, session_token, client_created_at=None, app_origin=None):
    user, error = _require_auth(session_token)
    if error:
        return error
    assert user is not None
    if _is_read_only_user(user):
        return {"success": False, "message": "Read-only accounts cannot create transactions."}
    return _insert_transaction_batch(requestor, requestor_info, transaction_items, user, client_created_at, app_origin)


@anvil.server.callable
def process_and_insert_data(tdn, pin, owner, lot_no, requestor, requestor_info, transaction_type, status, remarks, session_token):
    """Compatibility wrapper for clients that still submit one transaction."""
    return process_transaction_batch(
        requestor,
        requestor_info,
        [{
            "tdn": tdn,
            "pin": pin,
            "owner": owner,
            "lot_no": lot_no,
            "transaction_type": transaction_type,
            "contact_person": "",
            "contact_person_info": "",
            "status": status,
            "remarks": remarks,
        }],
        session_token,
    )


@anvil.server.callable
def update_record_status(record_id, new_status, new_remarks, session_token):
    user, error = _require_auth(session_token)
    if error:
        return error
    assert user is not None
    if _is_read_only_user(user):
        return {"success": False, "message": "Read-only accounts cannot update transactions."}
    row = None
    for candidate in app_tables.Tracker_Transactions.search():
        if candidate.get_id() == record_id:
            row = candidate
            break
    if not row:
        return {"success": False, "message": "Target transaction was not found in the database."}

    status = _upper(new_status)
    if not status:
        return {"success": False, "message": "A status is required."}
    if len(status) > 80 or not _reference_value_exists(app_tables.Tracker_Statuses, "name", status):
        return {"success": False, "message": "Select a valid transaction status."}
    remarks = _upper(new_remarks)
    if len(remarks) > 1000:
        return {"success": False, "message": "Remarks must be 1000 characters or fewer."}
    activity = "[%s] UPDATED BY %s" % (_formatted_date(), _upper(user["employee_name"]))
    row.update(status=status, remarks=remarks, latest_activity=activity)
    _write_audit_log(
        row["tdn"],
        user["employee_name"],
        "Transaction status updated to: '%s'. Remarks: '%s'." % (status, remarks or "None"),
    )
    return {"success": True, "message": "Transaction status and remarks successfully updated."}
