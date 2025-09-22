#!/usr/bin/env python3

"""Immobilizer model."""

# pylint: disable=C0103,R0801,R0902,R0915,C0301,W0235


from sdv.model import (
    DataPointString,
    Model,
)

from immobilizer_vehicle.Immobilizer.Inhibitor import Inhibitor
from immobilizer_vehicle.Immobilizer.KeySystems import KeySystems


class Immobilizer(Model):
    """Immobilizer model.

    Attributes
    ----------
    Config: sensor
        Current Immobilizer config (how the In-/Outputs are logically connected)

    Inhibitor: branch
        The key Inhibitor.

    KeySystems: branch
        The keysystem of the vehicle.

    """

    def __init__(self, name, parent):
        """Create a new Immobilizer model."""
        super().__init__(parent)
        self.name = name

        self.Config = DataPointString("Config", self)
        self.Inhibitor = Inhibitor("Inhibitor", self)
        self.KeySystems = KeySystems("KeySystems", self)
