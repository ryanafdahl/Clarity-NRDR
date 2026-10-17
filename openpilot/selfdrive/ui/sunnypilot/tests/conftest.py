"""Initialize isolated IPC before UI modules create their status subscribers."""
from openpilot.common.prefix import OpenpilotPrefix


_prefix = OpenpilotPrefix()
_prefix.__enter__()


def pytest_sessionfinish(session, exitstatus):
  _prefix.__exit__(None, None, None)
