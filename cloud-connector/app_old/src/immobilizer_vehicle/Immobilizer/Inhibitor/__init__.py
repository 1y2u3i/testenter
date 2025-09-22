#!/usr/bin/env python3

"""Inhibitor model."""

# pylint: disable=C0103,R0801,R0902,R0915,C0301,W0235

from immobilizer_vehicle.Immobilizer.Inhibitor.InhibitorType0 import InhibitorType0
from immobilizer_vehicle.Immobilizer.Inhibitor.InhibitorType1 import InhibitorType1
from immobilizer_vehicle.Immobilizer.Inhibitor.InhibitorType2 import InhibitorType2
from immobilizer_vehicle.Immobilizer.Inhibitor.InhibitorType3 import InhibitorType3
from immobilizer_vehicle.Immobilizer.Inhibitor.InhibitorType4 import InhibitorType4
from sdv.model import (
    Model,
)


class Inhibitor(Model):
    """Inhibitor model.

    Attributes
    ----------
    InhibitorType0: branch
        The key Inhibitor.

    InhibitorType1: branch
        The key Inhibitor.

    InhibitorType2: branch
        The key Inhibitor.

    InhibitorType3: branch
        The key Inhibitor.

    InhibitorType4: branch
        The key Inhibitor.

    """

    def __init__(self, name, parent):
        """Create a new Inhibitor model."""
        super().__init__(parent)
        self.name = name

        self.InhibitorType0 = InhibitorType0("InhibitorType0", self)
        self.InhibitorType1 = InhibitorType1("InhibitorType1", self)
        self.InhibitorType2 = InhibitorType2("InhibitorType2", self)
        self.InhibitorType3 = InhibitorType3("InhibitorType3", self)
        self.InhibitorType4 = InhibitorType4("InhibitorType4", self)
