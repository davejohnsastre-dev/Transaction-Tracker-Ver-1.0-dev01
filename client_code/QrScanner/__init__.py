from ._anvil_designer import QrScannerTemplate
from anvil import *
import anvil.js
from anvil.js import window
from anvil.js.window import URL, URLSearchParams


class QrScanner(QrScannerTemplate):
  def __init__(self, **properties):
    super().__init__(**properties)
    self._camera_stream = None
    self._detector = None
    self._scan_timer = None
    self._scan_active = False
    self._set_message("")
    self._start_camera()

  def _set_message(self, message):
    self.scanner_message.text = message or ""
    self.scanner_message.visible = bool(message)

  def _start_camera(self):
    barcode_detector = getattr(window, "BarcodeDetector", None)
    media_devices = getattr(getattr(window.navigator, "mediaDevices", None), "getUserMedia", None)
    if barcode_detector is None or media_devices is None:
      self._set_message(
        "This browser cannot scan QR codes automatically. Enter the slip ID below instead."
      )
      return

    try:
      self._detector = anvil.js.new(barcode_detector, {"formats": ["qr_code"]})
      self._camera_stream = window.navigator.mediaDevices.getUserMedia({
        "video": {"facingMode": {"ideal": "environment"}},
        "audio": False,
      })
      video = self.dom_nodes["camera_preview"]
      video.setAttribute("playsinline", "")
      video.autoplay = True
      video.srcObject = self._camera_stream
      video.play()
      self._scan_active = True
      self._set_message("Point the camera at the transaction QR code.")
      self._schedule_scan()
    except Exception:
      self._stop_camera()
      self._set_message(
        "Camera access was unavailable. Allow camera permission or enter the slip ID below."
      )

  def _schedule_scan(self):
    if self._scan_active:
      self._scan_timer = window.setTimeout(
        anvil.js.report_exceptions(self._scan_frame),
        250,
      )

  def _scan_frame(self):
    if not self._scan_active:
      return
    video = self.dom_nodes["camera_preview"]
    if getattr(video, "readyState", 0) < 2:
      self._schedule_scan()
      return
    detector = self._detector
    if detector is None:
      return
    try:
      results = detector.detect(video)
      if results and len(results):
        slip_id = self._extract_slip_id(results[0].rawValue)
        if slip_id:
          self._open_verification(slip_id)
          return
    except Exception:
      self._stop_camera()
      self._set_message(
        "The QR code could not be read. Enter the slip ID below or try again."
      )
      return
    self._schedule_scan()

  def _extract_slip_id(self, value):
    value = str(value or "").strip()
    if not value:
      return ""
    try:
      url = anvil.js.new(URL, value)
      params = anvil.js.new(URLSearchParams, str(url.search or ""))
      value = str(params.get("verify") or "").strip()
    except Exception:
      pass
    return value[:160]

  def _open_verification(self, slip_id):
    slip_id = self._extract_slip_id(slip_id)
    if not slip_id:
      self._set_message("Enter a valid transaction slip ID.")
      return
    self._stop_camera()
    open_form("Transaction_Tracker_System.QrMobileVerification", slip_id=slip_id)

  @handle("manual_verify_button", "click")
  def manual_verify_button_click(self, **event_args):
    self._open_verification(self.slip_id_box.text)

  @handle("retry_camera_button", "click")
  def retry_camera_button_click(self, **event_args):
    self._stop_camera()
    self._start_camera()

  @handle("close_scanner_button", "click")
  def close_scanner_button_click(self, **event_args):
    self._stop_camera()
    open_form("Transaction_Tracker_System.Form1")

  def _stop_camera(self):
    self._scan_active = False
    if self._scan_timer is not None:
      window.clearTimeout(self._scan_timer)
      self._scan_timer = None
    if self._camera_stream is not None:
      for track in self._camera_stream.getTracks():
        track.stop()
      self._camera_stream = None
    video = self.dom_nodes.get("camera_preview")
    if video is not None:
      video.srcObject = None
