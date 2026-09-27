from ._anvil_designer import QrMobileTransactionRowTemplate
from anvil import *


class QrMobileTransactionRow(QrMobileTransactionRowTemplate):
  def __init__(self, **properties):
    super().__init__(**properties)
