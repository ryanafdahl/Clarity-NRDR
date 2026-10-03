"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""
from opendbc.sunnypilot.car.honda.ptc import compatible_clarity_eps
from openpilot.selfdrive.ui.sunnypilot.layouts.settings.vehicle.brands.base import BrandSettings
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.multilang import tr
from openpilot.system.ui.sunnypilot.widgets.list_view import toggle_item_sp


class HondaSettings(BrandSettings):
  def __init__(self):
    super().__init__()
    self.ptc_toggle = toggle_item_sp(
      tr("Clarity PTC Firmware Installed"),
      tr("Enable only after installing NRDR ClarityMax-PTM on a compatible TRW-A020 EPS. " +
         "Stock and older torque mods need their original tuning. Restart the device after changing this setting."),
      param="HondaClarityPtcFirmware",
    )
    self.items = [self.ptc_toggle]

  def update_settings(self):
    compatible = ui_state.CP is not None and compatible_clarity_eps(ui_state.CP)
    # Permit turning off a stale confirmation even when the rack is unavailable.
    selected = ui_state.params.get_bool("HondaClarityPtcFirmware")
    self.ptc_toggle.action_item.set_enabled(ui_state.is_offroad() and (compatible or selected))
