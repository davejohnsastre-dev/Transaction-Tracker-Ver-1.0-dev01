from ._anvil_designer import TransactionRowTemplate
from anvil import *


class TransactionRow(TransactionRowTemplate):
  def __init__(self, **properties):
    super().__init__(**properties)
    self.update_button.visible = not self.item.get("read_only", False)

  @handle("update_button", "click")
  def update_button_click(self, **event_args):
    self.parent.raise_event("x-update-record", record=self.item)

  @handle("print_button", "click")
  def print_button_click(self, **event_args):
    self.parent.raise_event("x-print-record", record=self.item)

  @handle("logs_button", "click")
  def logs_button_click(self, **event_args):
    self.parent.raise_event("x-show-logs", tdn=self.item["tdn"])
