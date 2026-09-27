from ._anvil_designer import DeviceSettingRowTemplate
from anvil import *


class DeviceSettingRow(DeviceSettingRowTemplate):
  def __init__(self, **properties):
    super().__init__(**properties)

  @handle("revoke_button", "click")
  def revoke_button_click(self, **event_args):
    self.parent.raise_event("x-revoke-device", device_id=self.item["id"])
