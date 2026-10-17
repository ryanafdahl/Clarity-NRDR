"""Build this fork's camera warp in JetLink v0.8.7's driving-warp format.

The graph is the same NV12 preparation used by stock modeld. Only its input
layout changes: two frames and their transforms share two batched buffers.
Run at build time; never on modeld's frame thread.
"""
import argparse
import pickle
from pathlib import Path

import numpy as np


def capture(cam_w: int, cam_h: int, model_w: int, model_h: int) -> dict:
  from openpilot.selfdrive.modeld.compile_modeld import NV12Frame, make_warp, nv12_copy_size
  from openpilot.system.camerad.cameras.nv12_info import get_nv12_info
  from tinygrad import Tensor
  from tinygrad.engine.jit import TinyJit

  nv12 = NV12Frame(cam_w, cam_h, *get_nv12_info(cam_w, cam_h))
  size = nv12_copy_size(nv12.stride, nv12.y_height, nv12.uv_height)
  original = make_warp(nv12, model_w, model_h)

  def batched(M_inv, input_frame):
    return original(M_inv[0], M_inv[1], input_frame[0], input_frame[1]).realize()

  inputs = {
    'M_inv': Tensor(np.stack([np.eye(3, dtype=np.float32)] * 2), device=None).realize(),
    'input_frame': Tensor(np.zeros((2, size), dtype=np.uint8), device=None).realize(),
  }
  jit = TinyJit(batched, prune=True)
  for _ in range(3):
    jit(**inputs)
  return {'run': jit, 'input_specs': {k: (tuple(v.shape), v.numpy().dtype.name, v.device) for k, v in inputs.items()}}


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--camera', required=True)
  parser.add_argument('--model', required=True)
  parser.add_argument('--output', type=Path, required=True)
  args = parser.parse_args()
  cam_w, cam_h = map(int, args.camera.split('x'))
  model_w, model_h = map(int, args.model.split('x'))
  warp = capture(cam_w, cam_h, model_w, model_h)
  args.output.parent.mkdir(parents=True, exist_ok=True)
  with args.output.open('wb') as f:
    pickle.dump(warp, f)


if __name__ == '__main__':
  main()
