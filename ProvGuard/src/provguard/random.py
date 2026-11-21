"""Seed control for deterministic reference experiments."""

from __future__ import annotations

import os
import random

import numpy as np


def set_seed(seed: int) -> random.Random:
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    return random.Random(seed)

