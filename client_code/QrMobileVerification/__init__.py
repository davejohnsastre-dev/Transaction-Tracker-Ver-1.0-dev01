from ._anvil_designer import QrMobileVerificationTemplate
from anvil import *
import anvil.server
import anvil.js
from anvil.js import window


DEVICE_TOKEN_KEY = "transaction_tracker_device_token"
INSTALL_PROMPT_KEY = "__transaction_tracker_install_prompt"


class QrMobileVerification(QrMobileVerificationTemplate):
  def __init__(self, slip_id="", **properties):
    super().__init__(**properties)
    self.slip_id = (slip_id or "").strip()
    self._mobile_device = self._is_mobile_device()
    self._device_token = str(window.localStorage.getItem(DEVICE_TOKEN_KEY) or "").strip()
    self.mobile_scan_actions.visible = self._mobile_device
    self.scan_another_qr_button.visible = self._mobile_device
    self.secure_login_button.visible = self._mobile_device and bool(self._device_token)
    self._deferred_install_prompt = getattr(window, INSTALL_PROMPT_KEY, None)
    self._install_prompt_listener = anvil.js.report_exceptions(
      self._handle_before_install_prompt
    )
    self._appinstalled_listener = anvil.js.report_exceptions(
      self._handle_app_installed
    )
    window.addEventListener("beforeinstallprompt", self._install_prompt_listener)
    window.addEventListener("appinstalled", self._appinstalled_listener)
    self._refresh_install_prompt()
    self._load_verification()

  def _is_mobile_device(self):
    user_agent = str(window.navigator.userAgent or "").lower()
    mobile_markers = ("android", "iphone", "ipad", "ipod")
    if any(marker in user_agent for marker in mobile_markers):
      return True
    platform = str(getattr(window.navigator, "platform", "") or "").lower()
    touch_points = int(getattr(window.navigator, "maxTouchPoints", 0) or 0)
    return platform == "macintel" and touch_points > 1

  def _is_installed_app(self):
    if getattr(window.navigator, "standalone", False):
      return True
    match_media = getattr(window, "matchMedia", None)
    if match_media is None:
      return False
    return bool(match_media("(display-mode: standalone)").matches)

  def _refresh_install_prompt(self):
    if not self._is_mobile_device() or self._is_installed_app():
      self.install_prompt.visible = False
      return
    self.install_prompt.visible = True
    if self._deferred_install_prompt is not None:
      self.install_message.text = "Install this app on your phone for faster access."
    else:
      self.install_message.text = (
        "Install this app from your browser menu, or tap Install app when prompted."
      )

  def _handle_before_install_prompt(self, event):
    event.preventDefault()
    self._deferred_install_prompt = event
    setattr(window, INSTALL_PROMPT_KEY, event)
    self._refresh_install_prompt()

  def _handle_app_installed(self, event):
    self._deferred_install_prompt = None
    setattr(window, INSTALL_PROMPT_KEY, None)
    self.install_prompt.visible = False

  @handle("install_app_button", "click")
  def install_app_button_click(self, **event_args):
    install_prompt = self._deferred_install_prompt
    if install_prompt is None:
      self.install_message.text = (
        "If no install dialog appears, open your browser menu and choose "
        "Install app or Add to Home screen."
      )
      return
    self.install_app_button.enabled = False
    try:
      install_prompt.prompt()
      self._deferred_install_prompt = None
      setattr(window, INSTALL_PROMPT_KEY, None)
      self.install_message.text = "Choose Install in the browser dialog."
    finally:
      self.install_app_button.enabled = True

  @handle("scan_another_qr_button", "click")
  def scan_another_qr_button_click(self, **event_args):
    open_form("Transaction_Tracker_System.QrScanner")

  @handle("secure_login_button", "click")
  def secure_login_button_click(self, **event_args):
    if not self._mobile_device or not self._device_token:
      self._set_message("Secure login is available only on a registered device.")
      return
    self.secure_login_modal.visible = True
    self.secure_login_username_box.focus()

  @handle("secure_login_cancel_button", "click")
  def secure_login_cancel_button_click(self, **event_args):
    self.secure_login_modal.visible = False
    self.secure_login_username_box.text = ""
    self.secure_login_password_box.text = ""
    self.secure_login_message.text = ""
    self.secure_login_message.visible = False

  @handle("secure_login_submit_button", "click")
  def secure_login_submit_button_click(self, **event_args):
    username = (self.secure_login_username_box.text or "").strip()
    password = self.secure_login_password_box.text or ""
    if not username or not password:
      self.secure_login_message.text = "User name and password are required."
      self.secure_login_message.visible = True
      return

    self.secure_login_submit_button.enabled = False
    self.secure_login_submit_button.text = "Verifying..."
    try:
      result = anvil.server.call(
        "verify_user_credentials_for_registered_device",
        username,
        password,
        self._device_token,
      )
      if result.get("success"):
        open_form("Transaction_Tracker_System.Form1", auth_result=result)
      else:
        self.secure_login_message.text = result.get(
          "message", "Secure login failed."
        )
        self.secure_login_message.visible = True
    finally:
      self.secure_login_submit_button.enabled = True
      self.secure_login_submit_button.text = "Secure login"

  @handle("secure_login_username_box", "pressed_enter")
  def secure_login_username_box_pressed_enter(self, **event_args):
    self.secure_login_submit_button_click(**event_args)

  @handle("secure_login_password_box", "pressed_enter")
  def secure_login_password_box_pressed_enter(self, **event_args):
    self.secure_login_submit_button_click(**event_args)

  def _set_message(self, message):
    self.verification_message.text = message or ""
    self.verification_message.visible = bool(message)

  def _load_verification(self):
    if not self.slip_id:
      self._set_message("This verification link does not contain a transaction slip ID.")
      return

    result = anvil.server.call(
      "get_transaction_slip_records_for_qr",
      self.slip_id,
      self._device_token,
    )
    if not result.get("success"):
      self._set_message(result.get("message", "This transaction slip could not be found."))
      return

    slip = result.get("slip") or {}
    slip_id = slip.get("slip_id") or self.slip_id
    self.slip_id_label.text = "SLIP NO: %s" % slip_id
    self.requestor_label.text = "REQUESTOR: %s" % (slip.get("requestor") or "-")
    self.requestor_info_label.text = "REQUESTOR INFO: %s" % (slip.get("requestor_info") or "-")
    self.records_panel.items = [self._prepare_record(row) for row in result.get("records", [])]
    self.records_panel.visible = True
    self._set_message("")

  def _prepare_record(self, row):
    values = {}
    for key in (
      "tdn",
      "pin",
      "owner",
      "lot_no",
      "transaction_type",
      "contact_person",
      "contact_person_info",
      "status",
      "remarks",
      "created_at",
    ):
      values[key] = row.get(key) or "-"
    return values
