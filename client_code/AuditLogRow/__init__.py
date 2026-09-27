from ._anvil_designer import AuditLogRowTemplate
from anvil import *


class AuditLogRow(AuditLogRowTemplate):
  def __init__(self, **properties):
    super().__init__(**properties)
