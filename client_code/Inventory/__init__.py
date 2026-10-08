from ._anvil_designer import InventoryTemplate
from anvil import *
import anvil.server


FILTER_FIELDS = {
  "row_filter": "row_number",
  "serial_filter": "serial_number",
  "item_filter": "article_item",
  "description_filter": "description",
  "old_property_filter": "old_property_number",
  "new_property_filter": "new_property_number",
  "sku_filter": "sku",
  "unit_value_filter": "unit_value",
  "quantity_card_filter": "quantity_card",
  "quantity_count_filter": "quantity_count",
  "location_filter": "location",
  "assignee_filter": "assignee",
  "remarks_filter": "remarks",
}


class Inventory(InventoryTemplate):
  def __init__(self, session=None, **properties):
    super().__init__(**properties)
    self.session = session or {}
    self.can_manage = False
    self.selected_equipment = None
    self.offices = []
    self.categories = []
    self.equipment_panel.add_event_handler("x-transfer-equipment", self.transfer_equipment)
    self.equipment_panel.add_event_handler("x-status-equipment", self.status_equipment)
    self.equipment_panel.add_event_handler("x-update-remarks", self.update_remarks)
    if self.session.get("session_token"):
      self._load_inventory()

  def set_session(self, session):
    self.session = session or {}
    if self.session.get("session_token"):
      self._load_inventory()

  def _set_message(self, message):
    self.message_label.text = message or ""
    self.message_label.visible = bool(message)

  def _set_add_message(self, message):
    self.add_message.text = message or ""
    self.add_message.visible = bool(message)

  def _lookup_items(self, values):
    return [(item["name"], item["id"]) for item in values]

  def _selected_value(self, box):
    return box.selected_value if box.selected_value else None

  def _filters(self):
    return {
      field: getattr(self, component).text or ""
      for component, field in FILTER_FIELDS.items()
    }

  def _load_inventory(self, **event_args):
    selected_office = self._selected_value(self.office_filter)
    selected_category = self._selected_value(self.category_filter)
    filters = self._filters()
    row_filter = filters.pop("row_number", "")
    result = anvil.server.call(
      "get_inventory",
      self.session.get("session_token", ""),
      selected_office,
      selected_category,
      self.search_box.text or "",
      filters,
    )
    if not result.get("success"):
      self._set_message(result.get("message", "Unable to load inventory."))
      return
    self.can_manage = result.get("can_manage", False)
    self.offices = result.get("offices", [])
    self.categories = result.get("categories", [])
    self.office_filter.items = self._lookup_items(self.offices)
    self.category_filter.items = self._lookup_items(self.categories)
    self.office_box.items = self._lookup_items(self.offices)
    self.category_box.items = self._lookup_items(self.categories)
    self.office_filter.selected_value = selected_office
    self.category_filter.selected_value = selected_category
    self.add_equipment_panel.visible = self.can_manage
    items = [dict(item, row_number=index + 1, can_manage=self.can_manage)
             for index, item in enumerate(result.get("equipment", []))]
    if row_filter:
      items = [item for item in items if row_filter.lower() in str(item["row_number"]).lower()]
    self.equipment_panel.items = items
    self.audit_panel.items = result.get("audits", [])
    statuses = result.get("statuses", [])
    self.new_status_box.items = statuses
    if self.new_status_box.selected_value not in statuses:
      self.new_status_box.selected_value = statuses[0] if statuses else None
    self.status_box.items = statuses
    self.transfer_user_box.items = [
      (item["name"], item["username"]) for item in result.get("users", [])
    ]
    if selected_office and selected_category:
      self.empty_label.text = "No inventory records match the selected filters."
    else:
      self.empty_label.text = "Please select an office and category above to load inventory items..."
    self.empty_label.visible = not bool(items)
    self._set_message("")

  def _reload_from_filter(self, **event_args):
    self._load_inventory()

  @handle("office_filter", "change")
  def office_filter_change(self, **event_args):
    self._reload_from_filter()

  @handle("category_filter", "change")
  def category_filter_change(self, **event_args):
    self._reload_from_filter()

  @handle("search_box", "change")
  def search_box_change(self, **event_args):
    self._reload_from_filter()

  @handle("search_box", "pressed_enter")
  def search_box_pressed_enter(self, **event_args):
    self._reload_from_filter()

  @handle("serial_filter", "change")
  def serial_filter_change(self, **event_args):
    self._reload_from_filter()

  @handle("row_filter", "change")
  def row_filter_change(self, **event_args):
    self._reload_from_filter()

  @handle("item_filter", "change")
  def item_filter_change(self, **event_args):
    self._reload_from_filter()

  @handle("description_filter", "change")
  def description_filter_change(self, **event_args):
    self._reload_from_filter()

  @handle("old_property_filter", "change")
  def old_property_filter_change(self, **event_args):
    self._reload_from_filter()

  @handle("new_property_filter", "change")
  def new_property_filter_change(self, **event_args):
    self._reload_from_filter()

  @handle("sku_filter", "change")
  def sku_filter_change(self, **event_args):
    self._reload_from_filter()

  @handle("unit_value_filter", "change")
  def unit_value_filter_change(self, **event_args):
    self._reload_from_filter()

  @handle("quantity_card_filter", "change")
  def quantity_card_filter_change(self, **event_args):
    self._reload_from_filter()

  @handle("quantity_count_filter", "change")
  def quantity_count_filter_change(self, **event_args):
    self._reload_from_filter()

  @handle("location_filter", "change")
  def location_filter_change(self, **event_args):
    self._reload_from_filter()

  @handle("assignee_filter", "change")
  def assignee_filter_change(self, **event_args):
    self._reload_from_filter()

  @handle("remarks_filter", "change")
  def remarks_filter_change(self, **event_args):
    self._reload_from_filter()

  def _open_action(self, equipment, action):
    self.selected_equipment = equipment
    self.action_heading.text = "%s · %s" % (action, equipment["article_item"])
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

  def update_remarks(self, equipment, remarks, **event_args):
    result = anvil.server.call(
      "update_inventory_remarks",
      equipment["id"],
      remarks,
      self.session.get("session_token", ""),
    )
    self._set_message(result.get("message"))
    if result.get("success"):
      self._load_inventory()

  @handle("add_button", "click")
  def add_button_click(self, **event_args):
    if not (self.article_item_box.text or "").strip():
      self._set_add_message("Article item is required.")
      return
    if not (self.description_box.text or "").strip():
      self._set_add_message("Description is required.")
      return
    self._set_add_message("")
    self.add_button.enabled = False
    try:
      result = anvil.server.call(
        "add_equipment",
        self.article_item_box.text,
        self.description_box.text,
        self.manufacturer_box.text,
        self.model_box.text,
        self.serial_box.text,
        self.location_box.text,
        self.new_status_box.selected_value,
        self.new_notes_box.text,
        self.session.get("session_token", ""),
        self._selected_value(self.office_box),
        self._selected_value(self.category_box),
        self.old_property_box.text,
        self.new_property_box.text,
        self.sku_box.text,
        self.unit_value_box.text,
        self.quantity_card_box.text,
        self.quantity_count_box.text,
      )
      self._set_message(result.get("message"))
      if result.get("success"):
        for box in (
          self.article_item_box, self.description_box, self.manufacturer_box,
          self.model_box, self.serial_box, self.location_box, self.old_property_box,
          self.new_property_box, self.sku_box, self.unit_value_box,
          self.quantity_card_box, self.quantity_count_box, self.new_notes_box,
        ):
          box.text = ""
        self._load_inventory()
      else:
        self._set_add_message(result.get("message", "Unable to add equipment."))
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
          self.selected_equipment["article_item"],
          self.transfer_user_box.selected_value,
          self.action_notes_box.text,
          self.session.get("session_token", ""),
        )
      else:
        result = anvil.server.call(
          "update_equipment_status",
          self.selected_equipment["article_item"],
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
