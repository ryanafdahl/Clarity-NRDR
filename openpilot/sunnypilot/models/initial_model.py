"""Clarity Pilot's first-install selection, separate from the bundled emergency model."""

INITIAL_SMALL_MODEL = "The Cool Peoples Model v3 (October 10, 2025)"
INITIAL_SMALL_MODEL_REF = "5eb912c025a2207c7d428deee74ded49e5905527"
P_INITIALIZED = "ModelManager_InitialSmallModelSelected"


def cancel_download(params):
  # An explicit cancellation opts out of automatic first-install retries.
  if params.get("ModelManager_DownloadRef") == INITIAL_SMALL_MODEL_REF:
    params.put_bool(P_INITIALIZED, True)
  params.remove("ModelManager_DownloadRef")


def remember_small_model_choice(params):
  params.put_bool(P_INITIALIZED, True)
  if params.get("ModelManager_DownloadRef") == INITIAL_SMALL_MODEL_REF:
    params.remove("ModelManager_DownloadRef")
