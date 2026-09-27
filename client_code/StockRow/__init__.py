from ._anvil_designer import StockRowTemplate
from anvil import *


class StockRow(StockRowTemplate):
  def __init__(self, **properties):
    super().__init__(**properties)
    self.add_stock_button.visible = self.item.get("can_manage", False)

  @handle("withdraw_button", "click")
  def withdraw_button_click(self, **event_args):
    self.parent.raise_event("x-withdraw-stock", item=self.item)

  @handle("add_stock_button", "click")
  def add_stock_button_click(self, **event_args):
    self.parent.raise_event("x-add-stock", item=self.item)
