from ._anvil_designer import InventoryTemplate
from anvil import *
import anvil.server


class Inventory(InventoryTemplate):
  def __init__(self, session=None, **properties):
    super().__init__(**properties)
    self.session = session or {}
    self.can_manage = False
    self.selected_equipment = None
    self.equipment_panel.add_event_handler("x-transfer-equipment", self.transfer_equipment)
    self.equipment_panel.add_event_handler("x-status-equipment", self.status_equipment)
    self._load_inventory()

  def _set_message(self, message):
    self.message_label.text = message or ""
    self.message_label.visible = bool(message)

  def _load_inventory(self):
    result = anvil.server.call("get_inventory", self.session.get("session_token", ""))
    if not result.get("success"):
      self._set_message(result.get("message", "Unable to load inventory."))
      return
    self.can_manage = result.get("can_manage", False)
    self.add_equipment_panel.visible = self.can_manage
    self.equipment_panel.items = [dict(item, can_manage=self.can_manage) for item in result.get("equipment", [])]
    self.audit_panel.items = result.get("audits", [])
    self.status_box.items = result.get("statuses", [])
    self.transfer_user_box.items = [
      (item["name"], item["username"]) for item in result.get("users", [])
    ]
    self._set_message("")

  def _open_action(self, equipment, action):
    self.selected_equipment = equipment
    self.action_heading.text = "%s · %s" % (action, equipment["asset_tag"])
    self.action_message.text = ""
    self.transfer_fields.visible = action == "Transfer"
    self.status_fields.visible = action == "Change status"
    if action == "Change status":
      self.status_box.selected_value = equipment["status"]
    self.action_panel.visible = True

  def transfer_equipment(self, equipment, **event_args):
    self._open_action(equipment, "Transfer")

  def status_equipment(self, equipment, **event_args):
    self._open_action(equipment, "Change status")

  @handle("add_button", "click")
  def add_button_click(self, **event_args):
    self.add_button.enabled = False
    try:
      result = anvil.server.call(
        "add_equipment",
        self.asset_tag_box.text,
        self.category_box.text,
        self.manufacturer_box.text,
        self.model_box.text,
        self.serial_box.text,
        self.location_box.text,
        self.new_status_box.selected_value,
        self.new_notes_box.text,
        self.session.get("session_token", ""),
      )
      self._set_message(result.get("message"))
      if result.get("success"):
        for box in (self.asset_tag_box, self.category_box, self.manufacturer_box, self.model_box, self.serial_box, self.location_box, self.new_notes_box):
          box.text = ""
        self._load_inventory()
    finally:
      self.add_button.enabled = True

  @handle("action_cancel_button", "click")
  def action_cancel_button_click(self, **event_args):
    self.action_panel.visible = False

  @handle("action_save_button", "click")
  def action_save_button_click(self, **event_args):
    if not self.selected_equipment:
      return
    self.action_save_button.enabled = False
    try:
      if self.transfer_fields.visible:
        result = anvil.server.call(
          "transfer_" + "equipment",
          self.selected_equipment["asset_tag"],
          self.transfer_user_box.selected_value,
          self.action_notes_box.text,
          self.session.get("session_token", ""),
        )
      else:
        result = anvil.server.call(
          "update_equipment_status",
          self.selected_equipment["asset_tag"],
          self.status_box.selected_value,
          self.action_notes_box.text,
          self.session.get("session_token", ""),
        )
      self._set_message(result.get("message"))
      if result.get("success"):
        self.action_panel.visible = False
        self._load_inventory()
      else:
        self.action_message.text = result.get("message", "Unable to save change.")
    finally:
      self.action_save_button.enabled = True

  @handle("back_button", "click")
  def back_button_click(self, **event_args):
    open_form("Transaction_Tracker_System.Form1", auth_result={
      "username": self.session.get("username", ""),
      "sessionToken": self.session.get("session_token", ""),
      "employeeName": self.session.get("name", "USER"),
      "readOnly": self.session.get("read_only", False),
      "role": self.session.get("role", "user"),
    })
