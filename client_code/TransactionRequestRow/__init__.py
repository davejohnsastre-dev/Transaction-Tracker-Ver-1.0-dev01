from ._anvil_designer import TransactionRequestRowTemplate
from anvil import *


class TransactionRequestRow(TransactionRequestRowTemplate):
  def __init__(self, **properties):
    super().__init__(**properties)

  @handle("edit_button", "click")
  def edit_button_click(self, **event_args):
    self.parent.raise_event("x-edit-transaction", item=self.item)

  @handle("remove_button", "click")
  def remove_button_click(self, **event_args):
    self.parent.raise_event("x-remove-transaction", item=self.item)
