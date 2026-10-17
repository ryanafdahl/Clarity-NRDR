"""Comma 4 vehicle settings for the explicitly confirmed Clarity PTC profile."""
from opendbc.sunnypilot.car.honda.ptc import PTC_PARAM, compatible_clarity_eps
from openpilot.selfdrive.ui.mici.widgets.button import BigToggle, GreyBigButton
from openpilot.selfdrive.ui.mici.widgets.dialog import BigConfirmationCircleButton
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.lib.multilang import tr
from openpilot.system.ui.widgets.scroller import NavScroller


def can_enable_ptc() -> bool:
  return ui_state.is_offroad() and ui_state.CP is not None and compatible_clarity_eps(ui_state.CP)


class PtcFirmwareConfirmPage(NavScroller):
  def __init__(self, on_confirm):
    super().__init__()
    self.confirm = BigConfirmationCircleButton(
      tr("PTC firmware\ninstalled"), gui_app.texture("icons_mici/wheel.png", 64, 64),
      lambda: self.dismiss(on_confirm),
    )
    self.confirm.set_enabled(can_enable_ptc)
    self._scroller.add_widgets([
      GreyBigButton(tr("PTC firmware"), tr("ClarityMax-PTM\nClarityMax 20260928")),
      GreyBigButton("", tr("Keep off for stock EPS\nand the older 3x mod.")),
      GreyBigButton("", tr("Restart the device after\nchanging this setting.")),
      self.confirm,
    ])


class VehicleLayoutMici(NavScroller):
  def __init__(self):
    super().__init__()
    self.ptc_toggle = BigToggle(tr("Clarity PTC"), toggle_callback=self._on_ptc_toggle)
    self.ptc_toggle.set_enabled(lambda: ui_state.is_offroad() and (
      can_enable_ptc() or ui_state.params.get_bool(PTC_PARAM)))
    self._scroller.add_widgets([
      self.ptc_toggle,
      GreyBigButton(tr("PTC firmware"), tr("Keep off for stock EPS\nand the older 3x mod.")),
      GreyBigButton("", tr("Requires compatible EPS.\nChange only while parked.")),
      GreyBigButton("", tr("Restart the device after\nchanging this setting.")),
    ])
    self._refresh()

  def _refresh(self):
    self.ptc_toggle.set_checked(ui_state.params.get_bool(PTC_PARAM))

  def _on_ptc_toggle(self, selected: bool):
    # Keep the pill tied to the saved confirmation until the user confirms.
    self._refresh()
    if not ui_state.is_offroad():
      return
    if selected:
      if can_enable_ptc():
        gui_app.push_widget(PtcFirmwareConfirmPage(self._confirm_ptc))
    else:
      ui_state.params.put_bool(PTC_PARAM, False, block=True)
      self._refresh()

  def _confirm_ptc(self):
    # A confirmation opened offroad may finish after ignition changes.
    if can_enable_ptc():
      ui_state.params.put_bool(PTC_PARAM, True, block=True)
    self._refresh()

  def _update_state(self):
    super()._update_state()
    self._refresh()

  def show_event(self):
    super().show_event()
    self._refresh()
