from ._anvil_designer import InventoryRowTemplate
from anvil import *


class InventoryRow(InventoryRowTemplate):
  def __init__(self, **properties):
    super().__init__(**properties)
    self.editing_remarks = False
    can_manage = self.item.get("can_manage", False)
    self.transfer_button.visible = can_manage
    self.status_button.visible = can_manage
    self.remarks_editor.visible = False

  @handle("edit_remarks_button", "click")
  def edit_remarks_button_click(self, **event_args):
    self.editing_remarks = True
    self.remarks_box.text = self.item.get("remarks", "")
    self.remarks_display.visible = False
    self.remarks_editor.visible = True
    self.remarks_box.focus()

  @handle("save_remarks_button", "click")
  def save_remarks_button_click(self, **event_args):
    self.parent.raise_event(
      "x-update-remarks",
      equipment=self.item,
      remarks=self.remarks_box.text or "",
    )
    self.editing_remarks = False
    self.remarks_display.visible = True
    self.remarks_editor.visible = False

  @handle("cancel_remarks_button", "click")
  def cancel_remarks_button_click(self, **event_args):
    self.editing_remarks = False
    self.remarks_display.visible = True
    self.remarks_editor.visible = False

  @handle("transfer_button", "click")
  def transfer_button_click(self, **event_args):
    self.parent.raise_event("x-transfer-equipment", equipment=self.item)

  @handle("status_button", "click")
  def status_button_click(self, **event_args):
    self.parent.raise_event("x-status-equipment", equipment=self.item)
