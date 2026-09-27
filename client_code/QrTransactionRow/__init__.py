from ._anvil_designer import QrTransactionRowTemplate
from anvil import *


class QrTransactionRow(QrTransactionRowTemplate):
  def __init__(self, **properties):
    super().__init__(**properties)
