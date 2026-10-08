from ._anvil_designer import Form1Template
from anvil import *
import anvil.server
import anvil.js
from anvil.js import window
from anvil.js.window import URLSearchParams
from datetime import datetime


DEVICE_TOKEN_KEY = "transaction_tracker_device_token"
INSTALL_PROMPT_KEY = "__transaction_tracker_install_prompt"


class Form1(Form1Template):
  def __init__(self, auth_result=None, **properties):
    super().__init__(**properties)
    self.inventory_view.visible = False
    self.dashboard_heading.visible = False
    self.records_card.visible = False
    self.session = {"username": "", "session_token": "", "name": "", "read_only": False, "role": ""}
    if auth_result and auth_result.get("sessionToken"):
      self.session = {
        "username": auth_result.get("username", ""),
        "session_token": auth_result.get("sessionToken", ""),
        "name": auth_result.get("employeeName", "USER"),
        "read_only": auth_result.get("readOnly", False),
        "role": auth_result.get("role", "user"),
      }
    self.all_records = []
    self.filtered_records = []
    self.current_page = 1
    self.records_per_page = 30
    self.updating_record_id = None
    self.transaction_types = []
    self.status_types = []
    self.transaction_items = []
    self.editing_transaction_index = None
    self.editing_setting = None
    self.user_access_enabled = True
    self.device_token_required = True
    self.sort_ascending = False
    self._mobile_device = self._is_mobile_install_device()
    self.scan_qr_button.visible = self._mobile_device
    if self._mobile_device:
      self._install_prompt_listener = anvil.js.report_exceptions(
        self._capture_install_prompt
      )
      self._appinstalled_listener = anvil.js.report_exceptions(
        self._clear_install_prompt
      )
      window.addEventListener("beforeinstallprompt", self._install_prompt_listener)
      window.addEventListener("appinstalled", self._appinstalled_listener)
    self._refresh_created_sort_button()
    self.records_grid.columns = [
      {"id": "details", "title": "Transaction details", "data_key": "details", "width": 560, "expand": True},
      {"id": "actions", "title": "Actions", "data_key": "actions", "width": 240},
    ]
    self.records_grid.rows_per_page = 0
    self.records_grid.show_page_controls = False
    self.records_grid.auto_header = False
    self.transaction_items_grid.columns = [
      {"id": "tdn", "title": "TDN", "data_key": "tdn"},
      {"id": "pin", "title": "PIN", "data_key": "pin"},
      {"id": "owner", "title": "Owner / declarant name", "data_key": "owner"},
      {"id": "lot_no", "title": "Lot no.", "data_key": "lot_no"},
      {"id": "transaction_type", "title": "Transaction", "data_key": "transaction_type"},
      {"id": "contact_person", "title": "Contact person", "data_key": "contact_person"},
      {"id": "contact_person_info", "title": "Contact info", "data_key": "contact_person_info"},
      {"id": "status", "title": "Status", "data_key": "status"},
      {"id": "remarks", "title": "Remarks", "data_key": "remarks"},
      {"id": "actions", "title": "Actions", "data_key": "actions"},
    ]
    self.transaction_items_grid.rows_per_page = 0
    self.transaction_items_grid.show_page_controls = False
    self.update_status_radio_buttons = (
      self.update_status_option_1,
      self.update_status_option_2,
      self.update_status_option_3,
      self.update_status_option_4,
      self.update_status_option_5,
      self.update_status_option_6,
      self.update_status_option_7,
      self.update_status_option_8,
    )
    self.records_panel.add_event_handler("x-update-record", self.records_panel_update_record)
    self.records_panel.add_event_handler("x-print-record", self.records_panel_print_record)
    self.records_panel.add_event_handler("x-show-logs", self.records_panel_show_logs)
    self.transaction_items_panel.add_event_handler("x-edit-transaction", self.transaction_items_panel_edit_transaction)
    self.transaction_items_panel.add_event_handler("x-remove-transaction", self.transaction_items_panel_remove_transaction)
    self.users_panel.add_event_handler("x-modify-setting", self.users_panel_modify_setting)
    self.statuses_panel.add_event_handler("x-modify-setting", self.statuses_panel_modify_setting)
    self.types_panel.add_event_handler("x-modify-setting", self.types_panel_modify_setting)
    self.devices_panel.add_event_handler("x-revoke-device", self.devices_panel_revoke_device)
    self._update_page_info()
    if self.session.get("session_token"):
      self._show_authenticated_app()
    else:
      self._open_verification_link()

  def _set_message(self, label, message):
    label.text = message or ""
    label.visible = bool(message)

  def _is_mobile_install_device(self):
    user_agent = str(window.navigator.userAgent or "").lower()
    if any(marker in user_agent for marker in ("android", "iphone", "ipad", "ipod")):
      return True
    platform = str(getattr(window.navigator, "platform", "") or "").lower()
    touch_points = int(getattr(window.navigator, "maxTouchPoints", 0) or 0)
    return platform == "macintel" and touch_points > 1

  def _capture_install_prompt(self, event):
    event.preventDefault()
    setattr(window, INSTALL_PROMPT_KEY, event)

  def _clear_install_prompt(self, event):
    setattr(window, INSTALL_PROMPT_KEY, None)

  def _open_verification_link(self):
    search_params = anvil.js.new(URLSearchParams, str(window.location.search or ""))
    verification_slip_id = search_params.get("verify")
    if not verification_slip_id:
      return
    verification_slip_id = str(verification_slip_id).strip()
    if not verification_slip_id:
      return
    verification_form = (
      "Transaction_Tracker_System.QrMobileVerification"
      if self._is_mobile_verification_client()
      else "Transaction_Tracker_System.QrVerification"
    )
    open_form(verification_form, slip_id=verification_slip_id)

  def _is_mobile_verification_client(self):
    user_agent = str(window.navigator.userAgent or "").lower()
    mobile_markers = (
      "android",
      "iphone",
      "ipad",
      "ipod",
      "mobile",
      "windows phone",
    )
    if int(window.innerWidth or 0) <= 760 or any(
      marker in user_agent for marker in mobile_markers
    ):
      return True
    platform = str(getattr(window.navigator, "platform", "") or "").lower()
    touch_points = int(getattr(window.navigator, "maxTouchPoints", 0) or 0)
    return platform == "macintel" and touch_points > 1

  def _show_authenticated_app(self):
    read_only = self.session.get("read_only", False)
    self.login_panel.visible = False
    self.app_panel.visible = True
    self.transaction_button.visible = True
    self.change_pin_button.visible = not read_only
    self.inventory_button.visible = True
    self.stocks_button.visible = True
    self.settings_button.visible = (
      not read_only
      and self.session.get("role") == "admin"
    )
    self.logout_button.visible = True
    self.new_record_button.visible = not read_only
    self.welcome_label.text = "Logged in as: %s%s" % (
      self.session["name"],
      " (View only)" if read_only else "",
    )
    self._show_module_home_view()
    self.stocks_view.set_session(self.session)
    self.inventory_view.set_session(self.session)
    if not read_only:
      backfill_result = anvil.server.call(
        "backfill_transaction_slip_ids",
        self.session["session_token"],
        str(window.location.origin),
      )
      if not backfill_result.get("success"):
        self._set_message(self.records_message, backfill_result.get("message"))
    self._load_reference_data()
    self.refresh_records()

  def _load_reference_data(self):
    type_result = anvil.server.call("get_transaction_types", self.session["session_token"])
    if not type_result.get("success"):
      self._set_message(self.records_message, type_result.get("message"))
      return
    types = type_result.get("values", [])
    self.transaction_types = types
    self.type_filter.items = types
    self.modal_transaction_type_box.items = types

    status_result = anvil.server.call("get_status_types", self.session["session_token"])
    if not status_result.get("success"):
      self._set_message(self.records_message, status_result.get("message"))
      return
    statuses = status_result.get("values", [])
    self.status_types = statuses
    self.status_filter.items = statuses
    self.modal_status_box.items = statuses

  @handle("login_button", "click")
  def login_button_click(self, **event_args):
    username = self.username_box.text or ""
    pin = self.pin_box.text or ""
    if not username.strip() or not pin.strip():
      self._set_message(self.login_message, "User name and password are required.")
      return

    self.login_button.enabled = False
    self.login_button.text = "Verifying..."
    try:
      result = anvil.server.call("verify_user_credentials", username, pin)
      if result.get("success"):
        self.session = {
          "username": username,
          "session_token": result.get("sessionToken", ""),
          "name": result.get("employeeName", "USER"),
          "read_only": result.get("readOnly", False),
          "role": result.get("role", "user"),
        }
        self._set_message(self.login_message, "")
        self._show_authenticated_app()
      else:
        self._set_message(self.login_message, result.get("message", "Login failed."))
    finally:
      self.login_button.enabled = True
      self.login_button.text = "Secure login"

  @handle("username_box", "pressed_enter")
  def username_box_pressed_enter(self, **event_args):
    self.login_button_click(**event_args)

  @handle("pin_box", "pressed_enter")
  def pin_box_pressed_enter(self, **event_args):
    self.login_button_click(**event_args)

  @handle("scan_qr_button", "click")
  def scan_qr_button_click(self, **event_args):
    open_form("Transaction_Tracker_System.QrScanner")

  @handle("logout_button", "click")
  def logout_button_click(self, **event_args):
    try:
      if self.session.get("session_token"):
        anvil.server.call("logout_session", self.session["session_token"])
    finally:
      self.session = {"username": "", "session_token": "", "name": "", "read_only": False, "role": ""}
      self.login_panel.visible = True
      self.app_panel.visible = False
      self.inventory_view.visible = False
      self.dashboard_heading.visible = False
      self.records_card.visible = False
      self.transaction_button.visible = False
      self.change_pin_button.visible = False
      self.inventory_button.visible = False
      self.stocks_button.visible = False
      self.settings_button.visible = False
      self.logout_button.visible = False
      self.pin_box.text = ""

  @handle("change_pin_button", "click")
  def change_pin_button_click(self, **event_args):
    self._hide_editors()
    self.pin_editor.visible = True
    self.old_pin_box.focus()

  @handle("transaction_button", "click")
  def transaction_button_click(self, **event_args):
    self._show_records_view()

  @handle("inventory_button", "click")
  def inventory_button_click(self, **event_args):
    self._show_inventory_view()

  @handle("stocks_button", "click")
  def stocks_button_click(self, **event_args):
    self._show_stocks_view()

  @handle("cancel_pin_button", "click")
  def cancel_pin_button_click(self, **event_args):
    self.pin_editor.visible = False
    self.old_pin_box.text = ""
    self.new_pin_box.text = ""
    self.confirm_pin_box.text = ""
    self._set_message(self.pin_message, "")

  @handle("save_pin_button", "click")
  def save_pin_button_click(self, **event_args):
    old_pin = self.old_pin_box.text or ""
    new_pin = self.new_pin_box.text or ""
    if new_pin != (self.confirm_pin_box.text or ""):
      self._set_message(self.pin_message, "New password and confirmation do not match.")
      return
    self.save_pin_button.enabled = False
    self.save_pin_button.text = "Saving..."
    try:
      result = anvil.server.call("update_user_pin", self.session["session_token"], old_pin, new_pin)
      if result.get("success"):
        alert(result.get("message", "Password updated."))
        self.cancel_pin_button_click()
      else:
        self._set_message(self.pin_message, result.get("message", "Password update failed."))
    finally:
      self.save_pin_button.enabled = True
      self.save_pin_button.text = "Save new password"

  def _hide_editors(self):
    self.module_home_panel.visible = False
    self.stocks_view.visible = False
    self.inventory_view.visible = False
    self.dashboard_heading.visible = False
    self.records_card.visible = False
    self.transaction_button.role = "secondary-button"
    self.stocks_button.role = "secondary-button"
    self.inventory_button.role = "secondary-button"
    self.record_editor.visible = False
    self.pin_editor.visible = False
    self.logs_editor.visible = False
    self.settings_editor.visible = False
    self.transaction_modal.visible = False
    self.update_modal.visible = False

  def _show_records_view(self):
    self.module_home_panel.visible = False
    self.stocks_view.visible = False
    self.inventory_view.visible = False
    self.dashboard_heading.visible = True
    self.records_card.visible = True
    self.record_editor.visible = False
    self.pin_editor.visible = False
    self.logs_editor.visible = False
    self.settings_editor.visible = False
    self.transaction_button.role = "primary-button"
    self.stocks_button.role = "secondary-button"
    self.inventory_button.role = "secondary-button"

  def _show_record_entry_view(self):
    self.module_home_panel.visible = False
    self.stocks_view.visible = False
    self.inventory_view.visible = False
    self.dashboard_heading.visible = False
    self.records_card.visible = False
    self.pin_editor.visible = False
    self.logs_editor.visible = False
    self.settings_editor.visible = False
    self.record_editor.visible = True

  def _show_module_home_view(self):
    self.module_home_panel.visible = True
    self.stocks_view.visible = False
    self.inventory_view.visible = False
    self.dashboard_heading.visible = False
    self.records_card.visible = False
    self.record_editor.visible = False
    self.pin_editor.visible = False
    self.logs_editor.visible = False
    self.settings_editor.visible = False
    self.transaction_button.role = "secondary-button"

  def _show_stocks_view(self):
    self._hide_editors()
    self.stocks_view.visible = True
    self.stocks_view.set_session(self.session)
    self.stocks_button.role = "primary-button"
    self.inventory_button.role = "secondary-button"

  def _show_inventory_view(self):
    self._hide_editors()
    self.inventory_view.visible = True
    self.inventory_view.set_session(self.session)
    self.inventory_button.role = "primary-button"
    self.stocks_button.role = "secondary-button"

  def _is_admin_session(self):
    return (
      not self.session.get("read_only", False)
      and self.session.get("role") == "admin"
    )

  def _set_settings_message(self, message):
    self.settings_message.text = message or ""
    self.settings_message.visible = bool(message)

  def _load_admin_settings(self):
    result = anvil.server.call(
      "get_admin_settings",
      self.session["session_token"],
    )
    if not result.get("success"):
      self._set_settings_message(result.get("message", "Unable to load settings."))
      return
    self.users_panel.items = result.get("users", [])
    self.statuses_panel.items = result.get("statuses", [])
    self.types_panel.items = result.get("transaction_types", [])
    self.devices_panel.items = result.get("devices", [])
    self.device_token_required = bool(result.get("device_token_required", True))
    self._refresh_device_token_requirement_control()

  def _select_settings_section(self, section_name):
    sections = {
      "users": (self.user_settings_section, self.settings_users_button),
      "statuses": (self.status_settings_section, self.settings_statuses_button),
      "types": (self.type_settings_section, self.settings_types_button),
      "devices": (self.device_settings_section, self.settings_devices_button),
    }
    for name, (section, button) in sections.items():
      selected = name == section_name
      section.visible = selected
      button.role = "primary-button" if selected else "secondary-button"
    self.settings_selector_hint.visible = False

  def _set_settings_modal_message(self, message):
    self.settings_modal_message.text = message or ""
    self.settings_modal_message.visible = bool(message)

  def _refresh_user_access_control(self):
    state = "ENABLED" if self.user_access_enabled else "DISABLED"
    action = "Disable account" if self.user_access_enabled else "Enable account"
    self.settings_modal_user_access_label.text = "Account status: %s" % state
    self.settings_modal_user_access_button.text = action

  def _close_settings_modal(self):
    self.settings_modal.visible = False
    self.editing_setting = None
    self._set_settings_modal_message("")

  def _open_settings_modal(self, setting_type, setting=None):
    if not self._is_admin_session():
      return
    is_edit = setting is not None
    self.editing_setting = {
      "type": setting_type,
      "id": setting.get("id") if is_edit else None,
    }
    self.settings_modal_heading.text = (
      "Modify " if is_edit else "Add "
    ) + {
      "users": "user",
      "statuses": "status",
      "types": "transaction type",
    }[setting_type]
    self.settings_user_fields.visible = setting_type == "users"
    self.settings_status_fields.visible = setting_type == "statuses"
    self.settings_type_fields.visible = setting_type == "types"
    self.settings_modal_header.visible = setting_type != "users"
    self._set_settings_modal_message("")
    self.settings_modal.visible = True

    if setting_type == "users":
      self.settings_modal_username_box.text = (
        (setting.get("username") or setting.get("label") or "") if is_edit else ""
      )
      self.settings_modal_username_box.enabled = not is_edit
      self.settings_modal_employee_name_box.text = (
        setting.get("employee_name") or "" if is_edit else ""
      )
      self.settings_modal_password_box.text = ""
      self.settings_modal_password_box.placeholder = (
        "Leave blank to keep current password" if is_edit else "Temporary password"
      )
      self.user_access_enabled = setting.get("enabled", True) if is_edit else True
      self._refresh_user_access_control()
      self.settings_modal_employee_name_box.focus()
    elif setting_type == "statuses":
      self.settings_modal_status_name_box.text = (
        setting.get("name") or setting.get("label") or "" if is_edit else ""
      )
      self.settings_modal_status_name_box.focus()
    elif setting_type == "types":
      self.settings_modal_type_name_box.text = (
        setting.get("name") or setting.get("label") or "" if is_edit else ""
      )
      self.settings_modal_type_code_box.text = setting.get("code") or "" if is_edit else ""
      self.settings_modal_type_name_box.focus()
  def _reset_setting_forms(self):
    self.settings_modal_username_box.text = ""
    self.settings_modal_username_box.enabled = True
    self.settings_modal_employee_name_box.text = ""
    self.settings_modal_password_box.text = ""
    self.settings_modal_password_box.placeholder = "Temporary password"
    self.settings_modal_status_name_box.text = ""
    self.settings_modal_type_name_box.text = ""
    self.settings_modal_type_code_box.text = ""
    self.device_name_box.text = ""
    self.user_access_enabled = True
    self.device_token_required = True
    self._refresh_user_access_control()
    self._refresh_device_token_requirement_control()
    self._close_settings_modal()


  @handle("settings_button", "click")
  def settings_button_click(self, **event_args):
    if not self._is_admin_session():
      return
    self._hide_editors()
    self.dashboard_heading.visible = False
    self.records_card.visible = False
    self.settings_editor.visible = True
    self._set_settings_message("")
    self._reset_setting_forms()
    self._select_settings_section("users")
    self._load_admin_settings()

  @handle("settings_users_button", "click")
  def settings_users_button_click(self, **event_args):
    self._select_settings_section("users")

  @handle("settings_statuses_button", "click")
  def settings_statuses_button_click(self, **event_args):
    self._select_settings_section("statuses")

  @handle("settings_types_button", "click")
  def settings_types_button_click(self, **event_args):
    self._select_settings_section("types")

  @handle("settings_devices_button", "click")
  def settings_devices_button_click(self, **event_args):
    self._select_settings_section("devices")

  def users_panel_modify_setting(self, setting, **event_args):
    self._open_settings_modal("users", setting)

  def statuses_panel_modify_setting(self, setting, **event_args):
    self._open_settings_modal("statuses", setting)

  def types_panel_modify_setting(self, setting, **event_args):
    self._open_settings_modal("types", setting)

  def devices_panel_revoke_device(self, device_id, **event_args):
    if not self._is_admin_session():
      return
    result = anvil.server.call(
      "admin_revoke_device",
      device_id,
      self.session["session_token"],
    )
    self._set_settings_message(result.get("message", "Unable to revoke device access."))
    if result.get("success"):
      self._load_admin_settings()

  @handle("settings_back_button", "click")
  def settings_back_button_click(self, **event_args):
    self._show_records_view()
    self._set_settings_message("")

  @handle("register_user_button", "click")
  def register_user_button_click(self, **event_args):
    self._open_settings_modal("users")

  @handle("add_status_button", "click")
  def add_status_button_click(self, **event_args):
    self._open_settings_modal("statuses")

  @handle("add_type_button", "click")
  def add_type_button_click(self, **event_args):
    self._open_settings_modal("types")

  @handle("register_device_button", "click")
  def register_device_button_click(self, **event_args):
    if not self._is_admin_session():
      return
    device_name = (self.device_name_box.text or "").strip()
    if not device_name:
      self._set_settings_message("Enter a name for this browser or device first.")
      self.device_name_box.focus()
      return
    self.register_device_button.enabled = False
    self.register_device_button.text = "Registering..."
    try:
      result = anvil.server.call(
        "admin_register_device",
        device_name,
        self.session["session_token"],
      )
      if result.get("success"):
        token = result.get("token")
        if token:
          window.localStorage.setItem(DEVICE_TOKEN_KEY, str(token))
        self.device_name_box.text = ""
        self._set_settings_message(result.get("message", "Device registered."))
        self._load_admin_settings()
      else:
        self._set_settings_message(result.get("message", "Unable to register device."))
    finally:
      self.register_device_button.enabled = True
      self.register_device_button.text = "Register this device"

  def _refresh_device_token_requirement_control(self):
    if self.device_token_required:
      self.verification_access_policy_label.text = "QR access is protected"
      self.verification_access_policy_status.text = "A registered device token is required."
      self.device_token_requirement_button.text = "Turn off requirement"
    else:
      self.verification_access_policy_label.text = "QR access is public"
      self.verification_access_policy_status.text = "Anyone can verify without a device token."
      self.device_token_requirement_button.text = "Turn on requirement"

  @handle("device_token_requirement_button", "click")
  def device_token_requirement_button_click(self, **event_args):
    if not self._is_admin_session():
      return
    desired_requirement = not self.device_token_required
    self.device_token_requirement_button.enabled = False
    try:
      result = anvil.server.call(
        "admin_set_device_token_requirement",
        desired_requirement,
        self.session["session_token"],
      )
      if result.get("success"):
        self.device_token_required = bool(
          result.get("device_token_required", desired_requirement)
        )
        self._refresh_device_token_requirement_control()
        self._set_settings_message(result.get("message", "QR access policy updated."))
      else:
        self._set_settings_message(result.get("message", "Unable to update QR access policy."))
    finally:
      self.device_token_requirement_button.enabled = True

  @handle("settings_modal_user_access_button", "click")
  def settings_modal_user_access_button_click(self, **event_args):
    self.user_access_enabled = not self.user_access_enabled
    self._refresh_user_access_control()

  @handle("settings_modal_cancel_button", "click")
  def settings_modal_cancel_button_click(self, **event_args):
    self._close_settings_modal()

  @handle("settings_modal_cancel_bottom_button", "click")
  def settings_modal_cancel_bottom_button_click(self, **event_args):
    self._close_settings_modal()

  @handle("settings_modal_save_button", "click")
  def settings_modal_save_button_click(self, **event_args):
    if not self._is_admin_session() or not self.editing_setting:
      return
    setting_type = self.editing_setting["type"]
    setting_id = self.editing_setting.get("id")
    self.settings_modal_save_button.enabled = False
    self.settings_modal_save_button.text = "Saving..."
    try:
      if setting_type == "users":
        if setting_id:
          result = anvil.server.call(
            "admin_update_user",
            setting_id,
            self.settings_modal_employee_name_box.text or "",
            self.settings_modal_password_box.text or "",
            self.session["session_token"],
            self.user_access_enabled,
          )
        else:
          result = anvil.server.call(
            "admin_register_user",
            self.settings_modal_username_box.text or "",
            self.settings_modal_employee_name_box.text or "",
            self.settings_modal_password_box.text or "",
            self.session["session_token"],
            self.user_access_enabled,
          )
      elif setting_type == "statuses":
        if setting_id:
          result = anvil.server.call(
            "admin_update_status",
            setting_id,
            self.settings_modal_status_name_box.text or "",
            self.session["session_token"],
          )
        else:
          result = anvil.server.call(
            "admin_add_status",
            self.settings_modal_status_name_box.text or "",
            self.session["session_token"],
          )
      else:
        if setting_id:
          result = anvil.server.call(
            "admin_update_transaction_type",
            setting_id,
            self.settings_modal_type_name_box.text or "",
            self.settings_modal_type_code_box.text or "",
            self.session["session_token"],
          )
        else:
          result = anvil.server.call(
            "admin_add_transaction_type",
            self.settings_modal_type_name_box.text or "",
            self.settings_modal_type_code_box.text or "",
            self.session["session_token"],
          )
      message = result.get("message", "Unable to save setting.")
      if result.get("success"):
        self._close_settings_modal()
        self._set_settings_message(message)
        self._load_admin_settings()
        self._load_reference_data()
      else:
        self._set_settings_modal_message(message)
    finally:
      self.settings_modal_save_button.enabled = True
      self.settings_modal_save_button.text = "Save"

  @handle("new_record_button", "click")
  def new_record_button_click(self, **event_args):
    self._reset_record_editor()
    self.editor_heading.text = "Create new transaction"
    self.add_transaction_button.visible = True
    self._show_record_entry_view()

  @handle("cancel_editor_button", "click")
  def cancel_editor_button_click(self, **event_args):
    self._show_records_view()
    self._reset_record_editor()
    self._set_message(self.editor_message, "")

  def _new_transaction_item(self, values=None):
    values = values or {}
    return {
      "tdn": values.get("tdn", ""),
      "pin": values.get("pin", ""),
      "owner": values.get("owner", ""),
      "lot_no": values.get("lot_no", ""),
      "transaction_type": values.get("transaction_type", ""),
      "contact_person": values.get("contact_person", ""),
      "contact_person_info": values.get("contact_person_info", ""),
      "status": values.get("status", ""),
      "remarks": values.get("remarks", ""),
    }

  def _render_transaction_items(self):
    self.transaction_items_panel.items = self.transaction_items

  def _reset_record_editor(self):
    for component in (
      self.requestor_box,
      self.requestor_info_box,
    ):
      component.text = ""
      component.enabled = True
    self.transaction_items = []
    self._render_transaction_items()
    self.add_transaction_button.visible = True
    self._reset_transaction_modal()
    self._set_message(self.editor_message, "")

  def _reset_transaction_modal(self):
    for component in (
      self.modal_tdn_box,
      self.modal_pin_box,
      self.modal_owner_box,
      self.modal_lot_box,
      self.modal_contact_person_box,
      self.modal_contact_person_info_box,
      self.modal_remarks_box,
    ):
      component.text = ""
    self.modal_transaction_type_box.selected_value = None
    self.modal_status_box.selected_value = None
    self.editing_transaction_index = None
    self.modal_heading.text = "Add transaction"
    self.save_transaction_item_button.text = "Add transaction"
    self._set_message(self.transaction_modal_message, "")

  def _open_transaction_modal(self, item=None, index=None):
    self._reset_transaction_modal()
    if item is not None:
      self.modal_tdn_box.text = item.get("tdn", "")
      self.modal_pin_box.text = item.get("pin", "")
      self.modal_owner_box.text = item.get("owner", "")
      self.modal_lot_box.text = item.get("lot_no", "")
      self.modal_transaction_type_box.selected_value = item.get("transaction_type") or None
      self.modal_contact_person_box.text = item.get("contact_person", "")
      self.modal_contact_person_info_box.text = item.get("contact_person_info", "")
      self.modal_status_box.selected_value = item.get("status") or None
      self.modal_remarks_box.text = item.get("remarks", "")
      self.editing_transaction_index = index
      self.modal_heading.text = "Edit transaction"
      self.save_transaction_item_button.text = "Save transaction"
    self.transaction_modal.visible = True
    self.modal_tdn_box.focus()

  @handle("add_transaction_button", "click")
  def add_transaction_button_click(self, **event_args):
    self._open_transaction_modal()

  @handle("cancel_transaction_button", "click")
  def cancel_transaction_button_click(self, **event_args):
    self.transaction_modal.visible = False
    self._reset_transaction_modal()

  @handle("cancel_transaction_button_bottom", "click")
  def cancel_transaction_button_bottom_click(self, **event_args):
    self.cancel_transaction_button_click(**event_args)

  def _duplicate_tdn_message(self, transaction_items=None):
    transaction_items = self.transaction_items if transaction_items is None else transaction_items
    ignored_tdns = set()
    existing_tdns = {
      (record.get("tdn") or "").strip().upper()
      for record in self.all_records
      if (record.get("tdn") or "").strip()
      and (record.get("tdn") or "").strip().upper() not in ignored_tdns
    }
    seen_tdns = set()
    for item in transaction_items:
      tdn = (item.get("tdn") or "").strip().upper()
      if not tdn:
        continue
      if tdn in seen_tdns:
        return "TDN %s is duplicated in this transaction slip." % tdn
      if tdn in existing_tdns:
        return "TDN %s already exists. Each TDN must be unique." % tdn
      seen_tdns.add(tdn)
    return None

  @handle("save_transaction_item_button", "click")
  def save_transaction_item_button_click(self, **event_args):
    item = self._new_transaction_item({
      "tdn": self.modal_tdn_box.text,
      "pin": self.modal_pin_box.text,
      "owner": self.modal_owner_box.text,
      "lot_no": self.modal_lot_box.text,
      "transaction_type": self.modal_transaction_type_box.selected_value,
      "contact_person": self.modal_contact_person_box.text,
      "contact_person_info": self.modal_contact_person_info_box.text,
      "status": self.modal_status_box.selected_value,
      "remarks": self.modal_remarks_box.text,
    })
    required_fields = [
      item["tdn"], item["pin"], item["owner"], item["transaction_type"],
      item["contact_person"], item["contact_person_info"], item["status"],
    ]
    if any(not (value or "").strip() for value in required_fields):
      self._set_message(
        self.transaction_modal_message,
        "TDN, PIN, owner, transaction type, contact person, contact person info, and status are required.",
      )
      return
    candidate_items = list(self.transaction_items)
    if self.editing_transaction_index is None:
      candidate_items.append(item)
    else:
      candidate_items[self.editing_transaction_index] = item
    duplicate_tdn_message = self._duplicate_tdn_message(candidate_items)
    if duplicate_tdn_message:
      self._set_message(self.transaction_modal_message, duplicate_tdn_message)
      return
    if self.editing_transaction_index is None:
      self.transaction_items.append(item)
    else:
      self.transaction_items[self.editing_transaction_index] = item
    self._render_transaction_items()
    self.transaction_modal.visible = False
    self._reset_transaction_modal()

  @handle("modal_parse_button", "click")
  def parse_button_click(self, **event_args):
    self.modal_parse_button.enabled = False
    self.modal_parse_button.text = "Reading clipboard..."
    try:
      clipboard = getattr(window.navigator, "clipboard", None)
      if clipboard is None:
        raw_text = self.modal_raw_data_box.text or ""
        if not raw_text.strip():
          self._set_message(
            self.transaction_modal_message,
            "Clipboard access is unavailable. Paste the property data into the box above, then click Parse again.",
          )
          return
      else:
        try:
          raw_text = clipboard.readText() or ""
        except anvil.js.ExternalError:
          raw_text = self.modal_raw_data_box.text or ""
          if not raw_text.strip():
            self._set_message(
              self.transaction_modal_message,
              "Clipboard access was blocked. Paste the property data into the box above, then click Parse again.",
            )
            return
      if not raw_text.strip():
        self._set_message(self.transaction_modal_message, "Copy the property data first, then click Parse data from clipboard.")
        return
      result = anvil.server.call("parse_raw_text", raw_text, self.session["session_token"])
      if not result.get("success"):
        self._set_message(self.transaction_modal_message, result.get("message"))
        return
      self.modal_tdn_box.text = result.get("tdn", "")
      self.modal_pin_box.text = result.get("pin", "")
      self.modal_owner_box.text = result.get("owner", "")
      self.modal_lot_box.text = result.get("lot_no", "")
      self.modal_raw_data_box.text = ""
      self._set_message(self.transaction_modal_message, "Clipboard data parsed successfully.")
    finally:
      self.modal_parse_button.enabled = True
      self.modal_parse_button.text = "Parse data from clipboard"

  @handle("save_record_button", "click")
  def save_record_button_click(self, **event_args):
    fields = [self.requestor_box.text, self.requestor_info_box.text]
    if any(not (value or "").strip() for value in fields):
      self._set_message(self.editor_message, "Requestor and requestor info are required.")
      return
    if not self.transaction_items:
      self._set_message(self.editor_message, "Add at least one transaction item before saving the slip.")
      return
    duplicate_tdn_message = self._duplicate_tdn_message()
    if duplicate_tdn_message:
      self._set_message(self.editor_message, duplicate_tdn_message)
      return

    self.save_record_button.enabled = False
    self.save_record_button.text = "Saving data..."
    try:
      client_created_at = datetime.now()
      result = anvil.server.call(
        "process_transaction_batch",
        self.requestor_box.text,
        self.requestor_info_box.text,
        self.transaction_items,
        self.session["session_token"],
        client_created_at,
        str(window.location.origin),
      )
      if result.get("success"):
        self._set_print_data({
          "requestor": self.requestor_box.text,
          "requestor_info": self.requestor_info_box.text,
          "slip_id": result.get("slip_id"),
          "qr_code": result.get("qr_code"),
          "created_at": client_created_at,
          "requests": result.get("records", self.transaction_items),
        })
        self._show_records_view()
        self._reset_record_editor()
        self.refresh_records()
        self._print_slip()
      else:
        self._set_message(self.editor_message, result.get("message", "Database save failed."))
    finally:
      self.save_record_button.enabled = True
      self.save_record_button.text = "Save to database"

  def _reset_update_modal(self):
    self.update_modal.visible = False
    for option in self.update_status_radio_buttons:
      option.visible = False
      option.selected = False
      option.text = ""
      option.value = None
    self.update_record_reference.text = ""
    self.update_remarks_box.text = ""
    self.updating_record_id = None
    self._set_message(self.update_modal_message, "")

  def _open_update_modal(self, record):
    self._reset_update_modal()
    self.updating_record_id = record["id"]
    current_status = (record.get("status") or "").strip().upper()
    statuses = []
    for status in [current_status] + list(self.status_types):
      status = (status or "").strip().upper()
      if status and status not in statuses:
        statuses.append(status)
    for option, status in zip(self.update_status_radio_buttons, statuses):
      option.text = status
      option.value = status
      option.selected = status == current_status
      option.visible = True
    if len(statuses) > len(self.update_status_radio_buttons):
      self._set_message(
        self.update_modal_message,
        "Only the first %s configured statuses can be selected." % len(self.update_status_radio_buttons),
      )
    for option in self.update_status_radio_buttons[len(statuses):]:
      option.visible = False
      option.selected = False
      option.text = ""
      option.value = None
    if not statuses:
      self._set_message(self.update_modal_message, "No statuses are configured.")
    if not current_status:
      for option in self.update_status_radio_buttons:
        if option.visible:
          option.selected = False
    self.update_record_reference.text = "TDN: %s" % (record.get("tdn") or "-")
    self.update_remarks_box.text = record.get("remarks") or ""
    self.update_modal.visible = True
    self.update_remarks_box.focus()

  def _selected_update_status(self):
    for option in self.update_status_radio_buttons:
      if option.visible and option.selected and option.value:
        return option.value
    return None

  @handle("save_update_button", "click")
  def save_update_button_click(self, **event_args):
    new_status = self._selected_update_status()
    if not new_status:
      self._set_message(self.update_modal_message, "Select a status before saving.")
      return
    if not self.updating_record_id:
      self._set_message(self.update_modal_message, "The transaction to update is no longer selected.")
      return
    self.save_update_button.enabled = False
    self.save_update_button.text = "Saving..."
    try:
      result = anvil.server.call(
        "update_record_status",
        self.updating_record_id,
        new_status,
        self.update_remarks_box.text or "",
        self.session["session_token"],
      )
      if result.get("success"):
        self._reset_update_modal()
        self.refresh_records()
      else:
        self._set_message(self.update_modal_message, result.get("message", "Update failed."))
    finally:
      self.save_update_button.enabled = True
      self.save_update_button.text = "Save changes"

  @handle("cancel_update_button", "click")
  def cancel_update_button_click(self, **event_args):
    self._reset_update_modal()

  @handle("cancel_update_button_bottom", "click")
  def cancel_update_button_bottom_click(self, **event_args):
    self.cancel_update_button_click(**event_args)

  def _set_print_data(self, data):
    request_lines = data.get("requests") or []
    now = data.get("created_at") or datetime.now()
    hour = now.hour % 12 or 12
    period = "AM" if now.hour < 12 else "PM"
    self.print_date.text = "%s/%s/%s, %s:%02d %s" % (
      now.month, now.day, str(now.year)[-2:], hour, now.minute, period,
    )
    self.print_slip_id.text = "SLIP NO: %s" % (data.get("slip_id") or "N/A").upper()
    self.print_requestor.text = "REQUESTOR: %s" % (data.get("requestor") or "N/A").upper()
    self.print_requestor_info.text = "REQUESTOR INFO: %s" % (data.get("requestor_info") or "N/A").upper()
    slip_id = str(data.get("slip_id") or "N/A").upper()
    qr_code = data.get("qr_code")
    if qr_code:
      self.print_qr_code.source = qr_code
    else:
      verification_url = "%s?verify=%s" % (str(window.location.origin), slip_id)
      encoded_verification_url = anvil.js.call("encodeURIComponent", verification_url)
      self.print_qr_code.source = (
        "https://api.qrserver.com/v1/create-qr-code/?size=260x260&margin=8&data=%s"
        % encoded_verification_url
      )
    self.print_qr_code.alt_text = "Scan to verify transaction slip %s" % slip_id
    grouped_requests = {}
    group_order = []
    for index, request in enumerate(request_lines, 1):
      transaction_type = (request.get("transaction_type") or request.get("type") or "N/A").upper()
      if transaction_type not in grouped_requests:
        grouped_requests[transaction_type] = []
        group_order.append(transaction_type)
      grouped_requests[transaction_type].append((index, request))

    lines = []
    for transaction_type in group_order:
      lines.append("TRANSACTION TYPE: %s" % transaction_type)
      for index, request in grouped_requests[transaction_type]:
        lines.append(
          "%s. TDN: %s | PIN: %s | OWNER: %s | LOT: %s\n"
          "   CONTACT: %s (%s) | STATUS: %s | REMARKS: %s"
          % (
            index,
            (request.get("tdn") or "N/A").upper(),
            (request.get("pin") or "N/A").upper(),
            (request.get("owner") or "N/A").upper(),
            (request.get("lot_no") or "N/A").upper(),
            (request.get("contact_person") or "N/A").upper(),
            (request.get("contact_person_info") or "N/A").upper(),
            (request.get("status") or "N/A").upper(),
            (request.get("remarks") or "NONE").upper(),
          )
        )
    self.print_transactions.text = "\n".join(lines) or "N/A"
    self.print_footer_url.text = str(window.location.origin)

  def _print_slip(self):
    self.print_slip.visible = True

    def hide_after_print(_event=None):
      self.print_slip.visible = False
      window.removeEventListener("afterprint", afterprint_handler)

    afterprint_handler = anvil.js.report_exceptions(hide_after_print)
    window.addEventListener("afterprint", afterprint_handler)

    def print_now(_timestamp=None):
      window.print()

    window.setTimeout(anvil.js.report_exceptions(print_now), 400)

  @handle("search_button", "click")
  def search_button_click(self, **event_args):
    self.current_page = 1
    self._apply_filters()

  @handle("clear_button", "click")
  def clear_button_click(self, **event_args):
    self.search_box.text = ""
    self.type_filter.selected_value = None
    self.status_filter.selected_value = None
    self.current_page = 1
    self._apply_filters()

  @handle("refresh_button", "click")
  def refresh_button_click(self, **event_args):
    self.refresh_records()

  def _refresh_created_sort_button(self):
    if self.sort_ascending:
      self.sort_created_button.text = "↑"
      self.sort_created_button.tooltip = "Oldest transactions first"
    else:
      self.sort_created_button.text = "↓"
      self.sort_created_button.tooltip = "Newest transactions first"

  @handle("sort_created_button", "click")
  def sort_created_button_click(self, **event_args):
    self.sort_ascending = not self.sort_ascending
    self._refresh_created_sort_button()
    self.current_page = 1
    self._apply_filters()

  @handle("previous_button", "click")
  def previous_button_click(self, **event_args):
    if self.current_page > 1:
      self.current_page -= 1
      self._render_records()

  @handle("next_button", "click")
  def next_button_click(self, **event_args):
    total_pages = max(1, (len(self.filtered_records) + self.records_per_page - 1) // self.records_per_page)
    if self.current_page < total_pages:
      self.current_page += 1
      self._render_records()

  def refresh_records(self):
    result = anvil.server.call("get_spreadsheet_data", self.session["session_token"])
    if not result.get("success"):
      self._set_message(self.records_message, result.get("message"))
      return
    self.all_records = result.get("records", [])
    self.sort_ascending = False
    self._refresh_created_sort_button()
    self.current_page = 1
    self._apply_filters()

  def _apply_filters(self):
    query = (self.search_box.text or "").strip().lower()
    selected_type = (self.type_filter.selected_value or "").strip().lower()
    selected_status = (self.status_filter.selected_value or "").strip().lower()
    self.filtered_records = []
    records = list(reversed(self.all_records)) if self.sort_ascending else self.all_records
    for row in records:
      searchable = " ".join(str(value or "") for value in row.values()).lower()
      if query and query not in searchable:
        continue
      if selected_type and row.get("transaction_type", "").lower() != selected_type:
        continue
      if selected_status and row.get("status", "").lower() != selected_status:
        continue
      row = dict(row)
      row["read_only"] = self.session.get("read_only", False)
      row["details"] = (
        "TDN: %s | PIN: %s | OWNER: %s | LOT: %s | TYPE: %s\n"
        "REQUESTOR: %s | REQUESTOR INFO: %s\n"
        "CONTACT PERSON: %s | CONTACT PERSON INFO: %s\n"
        "REMARKS: %s\n"
        "CREATED: %s %s"
      ) % (
        row.get("tdn", "-"), row.get("pin", "-"), row.get("owner", "-"),
        row.get("lot_no", "-"), row.get("transaction_type", "-"),
        row.get("requestor", "-"), row.get("requestor_info", "-"),
        row.get("contact_person", "-"), row.get("contact_person_info", "-"),
        row.get("remarks", "-") or "-",
        row.get("encoder", "-") or "-",
        row.get("created_at", "-") or "-",
      )
      self.filtered_records.append(row)
    self.current_page = 1
    self._render_records()

  def _render_records(self):
    start = (self.current_page - 1) * self.records_per_page
    end = start + self.records_per_page
    self.records_panel.items = self.filtered_records[start:end]
    self._update_page_info()

  def _update_page_info(self):
    total = len(self.filtered_records)
    total_pages = max(1, (total + self.records_per_page - 1) // self.records_per_page)
    start = 0 if not total else (self.current_page - 1) * self.records_per_page + 1
    end = min(self.current_page * self.records_per_page, total)
    self.page_info.text = "Showing %s to %s of %s records (Page %s of %s)" % (start, end, total, self.current_page, total_pages)
    self.previous_button.enabled = self.current_page > 1
    self.next_button.enabled = self.current_page < total_pages

  def records_panel_update_record(self, record, **event_args):
    self._open_update_modal(record)

  def records_panel_print_record(self, record, **event_args):
    slip_id = (record.get("slip_id") or "").strip()
    if not slip_id:
      self._set_message(self.records_message, "This transaction has no slip ID to print.")
      return
    result = anvil.server.call(
      "get_transaction_slip_records",
      slip_id,
      self.session["session_token"],
    )
    if not result.get("success"):
      self._set_message(self.records_message, result.get("message", "Unable to load the transaction slip."))
      return
    slip = result.get("slip") or {}
    self._set_print_data({
      "requestor": slip.get("requestor"),
      "requestor_info": slip.get("requestor_info"),
      "slip_id": slip.get("slip_id") or slip_id,
      "qr_code": slip.get("qr_code"),
      "requests": result.get("records", []),
    })
    self._print_slip()

  def transaction_items_panel_edit_transaction(self, item, **event_args):
    index = self.transaction_items.index(item)
    self._open_transaction_modal(item, index)

  def transaction_items_panel_remove_transaction(self, item, **event_args):
    self.transaction_items = [line for line in self.transaction_items if line is not item]
    self._render_transaction_items()

  def records_panel_show_logs(self, tdn, **event_args):
    result = anvil.server.call("get_record_logs", tdn, self.session["session_token"])
    if not result.get("success"):
      alert(result.get("message", "Unable to load audit logs."))
      return
    self._hide_editors()
    self.logs_heading.text = "Audit trail: %s" % tdn
    self.logs_panel.items = result.get("logs", [])
    self.logs_editor.visible = True

  @handle("close_logs_button", "click")
  def close_logs_button_click(self, **event_args):
    self.logs_editor.visible = False
