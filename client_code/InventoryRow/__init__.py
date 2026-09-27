from ._anvil_designer import InventoryRowTemplate
from anvil import *


class InventoryRow(InventoryRowTemplate):
  def __init__(self, **properties):
    super().__init__(**properties)
    can_manage = self.item.get("can_manage", False)
    self.transfer_button.visible = can_manage
    self.status_button.visible = can_manage

  @handle("transfer_button", "click")
  def transfer_button_click(self, **event_args):
    self.parent.raise_event("x-transfer-equipment", equipment=self.item)

  @handle("status_button", "click")
  def status_button_click(self, **event_args):
    self.parent.raise_event("x-status-equipment", equipment=self.item)
