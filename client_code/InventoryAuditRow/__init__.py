from ._anvil_designer import InventoryAuditRowTemplate
from anvil import *


class InventoryAuditRow(InventoryAuditRowTemplate):
  def __init__(self, **properties):
    super().__init__(**properties)
