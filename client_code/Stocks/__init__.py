from ._anvil_designer import StocksTemplate
from anvil import *
import anvil.server


class Stocks(StocksTemplate):
  def __init__(self, session=None, **properties):
    super().__init__(**properties)
    self.session = session or {}
    self.can_manage = False
    self.selected_item = None
    self.stock_items = []
    self.stock_panel.add_event_handler("x-withdraw-stock", self.withdraw_stock)
    self.stock_panel.add_event_handler("x-add-stock", self.add_stock)
    self._load_stocks()

  def _set_message(self, message):
    self.message_label.text = message or ""
    self.message_label.visible = bool(message)

  def _load_stocks(self):
    result = anvil.server.call("get_stocks", self.session.get("session_token", ""))
    if not result.get("success"):
      self._set_message(result.get("message", "Unable to load stock balances."))
      return
    self.can_manage = result.get("can_manage", False)
    self.stock_items = result.get("items", [])
    self.add_item_panel.visible = self.can_manage
    items = [dict(item, can_manage=self.can_manage) for item in self.stock_items]
    self.stock_panel.items = items
    item_names = [item["name"] for item in self.stock_items]
    self.item_box.items = item_names
    self.movement_panel.items = result.get("movements", [])
    self._set_message("")

  def _open_action(self, item, action):
    self.selected_item = item
    self.action_heading.text = "%s · %s" % (action, item["name"])
    self.action_message.text = ""
    self.action_panel.visible = True
    self.action_type = action
    self.item_box.selected_value = item["name"]

  def withdraw_stock(self, item, **event_args):
    self._open_action(item, "Withdraw stock")

  def add_stock(self, item, **event_args):
    self._open_action(item, "Add stock")

  @handle("add_item_button", "click")
  def add_item_button_click(self, **event_args):
    self.add_item_button.enabled = False
    try:
      result = anvil.server.call(
        "add_stock_item",
        self.item_name_box.text,
        self.item_unit_box.text,
        self.starting_balance_box.text,
        self.session.get("session_token", ""),
      )
      self._set_message(result.get("message"))
      if result.get("success"):
        self.item_name_box.text = ""
        self.item_unit_box.text = ""
        self.starting_balance_box.text = ""
        self._load_stocks()
    finally:
      self.add_item_button.enabled = True

  @handle("action_cancel_button", "click")
  def action_cancel_button_click(self, **event_args):
    self.action_panel.visible = False

  @handle("action_save_button", "click")
  def action_save_button_click(self, **event_args):
    self.action_save_button.enabled = False
    try:
      if self.action_type == "Add stock":
        result = anvil.server.call(
          "add_" + "stock",
          self.item_box.selected_value,
          self.quantity_box.text,
          self.notes_box.text,
          self.session.get("session_token", ""),
        )
      else:
        result = anvil.server.call(
          "withdraw_" + "stock",
          self.item_box.selected_value,
          self.quantity_box.text,
          self.notes_box.text,
          self.session.get("session_token", ""),
        )
      self._set_message(result.get("message"))
      if result.get("success"):
        self.quantity_box.text = ""
        self.notes_box.text = ""
        self.action_panel.visible = False
        self._load_stocks()
      else:
        self.action_message.text = result.get("message", "Unable to record stock movement.")
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
