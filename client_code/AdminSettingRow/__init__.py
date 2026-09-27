from ._anvil_designer import AdminSettingRowTemplate
from anvil import *


class AdminSettingRow(AdminSettingRowTemplate):
  def __init__(self, **properties):
    super().__init__(**properties)

  @handle("modify_button", "click")
  def modify_button_click(self, **event_args):
    self.parent.raise_event("x-modify-setting", setting=self.item)
