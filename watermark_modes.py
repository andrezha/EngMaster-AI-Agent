# -*- coding: utf-8 -*-
import argparse
from dataclasses import dataclass


LICENSED_USER_MODE = "licensed"
STORE_MATERIAL_MODE = "store"
VALID_WATERMARK_MODES = (LICENSED_USER_MODE, STORE_MATERIAL_MODE)


@dataclass(frozen=True)
class WatermarkSettings:
    mode: str

    @property
    def is_store_material(self):
        return self.mode == STORE_MATERIAL_MODE

    @property
    def is_licensed_user(self):
        return self.mode == LICENSED_USER_MODE

    @property
    def display_name(self):
        if self.is_store_material:
            return "store material"
        return "licensed user"


def parse_watermark_args(argv):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--watermark-mode",
        choices=VALID_WATERMARK_MODES,
        default=LICENSED_USER_MODE,
        help="licensed: normal user exports; store: internal store-material exports",
    )
    args, remaining = parser.parse_known_args(argv[1:])
    return WatermarkSettings(mode=args.watermark_mode), [argv[0], *remaining]
