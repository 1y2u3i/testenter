#!/usr/bin/env python3

"""KeySystems model."""

# pylint: disable=C0103,R0801,R0902,R0915,C0301,W0235


from sdv.model import (
    Model,
)

from immobilizer_vehicle.Immobilizer.KeySystems.Key0 import Key0
from immobilizer_vehicle.Immobilizer.KeySystems.Key1 import Key1
from immobilizer_vehicle.Immobilizer.KeySystems.Key2 import Key2
from immobilizer_vehicle.Immobilizer.KeySystems.Key3 import Key3
from immobilizer_vehicle.Immobilizer.KeySystems.Key4 import Key4


class KeySystems(Model):
    """KeySystems model.

    Attributes
    ----------
    Key0: branch
        The keysystem of the vehicle.

    Key1: branch
        The keysystem of the vehicle.

    Key2: branch
        The keysystem of the vehicle.

    Key3: branch
        The keysystem of the vehicle.

    Key4: branch
        The keysystem of the vehicle.

    """

    def __init__(self, name, parent):
        """Create a new KeySystems model."""
        super().__init__(parent)
        self.name = name

        self.Key0 = Key0("Key0", self)
        self.Key1 = Key1("Key1", self)
        self.Key2 = Key2("Key2", self)
        self.Key3 = Key3("Key3", self)
        self.Key4 = Key4("Key4", self)
