#!/usr/bin/env python3

"""Vehicle model."""

# pylint: disable=C0103,R0801,R0902,R0915,C0301,W0235


from sdv.model import (
    Model,
)

from immobilizer_vehicle.Immobilizer import Immobilizer


class Vehicle(Model):
    """Vehicle model.

    Attributes
    ----------
    Immobilizer: branch
        Immobilizer data.

    """

    def __init__(self, name):
        """Create a new Vehicle model."""
        super().__init__()
        self.name = name

        self.Immobilizer = Immobilizer("Immobilizer", self)


vehicle = Vehicle("Vehicle")
