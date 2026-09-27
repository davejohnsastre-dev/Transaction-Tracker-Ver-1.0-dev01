from ._anvil_designer import QrVerificationTemplate
from anvil import *
import anvil.server
from anvil.js import window


DEVICE_TOKEN_KEY = "transaction_tracker_device_token"


class QrVerification(QrVerificationTemplate):
  def __init__(self, slip_id="", **properties):
    super().__init__(**properties)
    self.slip_id = (slip_id or "").strip()
    self.records_grid.columns = [
      {"id": "details", "title": "Transaction details", "data_key": "details", "width": 700, "expand": True},
      {"id": "status", "title": "Status", "data_key": "status", "width": 180},
    ]
    self.records_grid.rows_per_page = 0
    self.records_grid.show_page_controls = False
    self._load_verification()

  def _set_message(self, message):
    self.verification_message.text = message or ""
    self.verification_message.visible = bool(message)

  def _load_verification(self):
    if not self.slip_id:
      self._set_message("This verification link does not contain a transaction slip ID.")
      return

    device_token = str(window.localStorage.getItem(DEVICE_TOKEN_KEY) or "").strip()
    result = anvil.server.call(
      "get_transaction_slip_records_for_qr",
      self.slip_id,
      device_token,
    )
    if not result.get("success"):
      self._set_message(result.get("message", "This transaction slip could not be found."))
      return

    slip = result.get("slip") or {}
    self.slip_id_label.text = "SLIP NO: %s" % (slip.get("slip_id") or self.slip_id)
    self.records_panel.items = [self._prepare_record(row) for row in result.get("records", [])]
    self.records_grid.visible = True
    self._set_message("")

  def _prepare_record(self, row):
    values = {
      "tdn": row.get("tdn") or "-",
      "pin": row.get("pin") or "-",
      "owner": row.get("owner") or "-",
      "lot_no": row.get("lot_no") or "-",
      "transaction_type": row.get("transaction_type") or "-",
      "contact_person": row.get("contact_person") or "-",
      "contact_person_info": row.get("contact_person_info") or "-",
      "remarks": row.get("remarks") or "-",
      "created_at": row.get("created_at") or "-",
    }
    row = dict(row)
    row["details"] = (
      "TDN: %s | PIN: %s | OWNER: %s | LOT: %s | TYPE: %s\n"
      "CONTACT PERSON: %s | CONTACT PERSON INFO: %s\n"
      "REMARKS: %s\n"
      "CREATED: %s"
    ) % (
      values["tdn"],
      values["pin"],
      values["owner"],
      values["lot_no"],
      values["transaction_type"],
      values["contact_person"],
      values["contact_person_info"],
      values["remarks"],
      values["created_at"],
    )
    row["status"] = row.get("status") or "-"
    return row
