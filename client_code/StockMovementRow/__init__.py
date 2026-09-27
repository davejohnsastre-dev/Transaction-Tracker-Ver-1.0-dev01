from ._anvil_designer import StockMovementRowTemplate
from anvil import *


class StockMovementRow(StockMovementRowTemplate):
  def __init__(self, **properties):
    super().__init__(**properties)
