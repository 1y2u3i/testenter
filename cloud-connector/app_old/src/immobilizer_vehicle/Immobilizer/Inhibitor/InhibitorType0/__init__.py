#!/usr/bin/env python3

"""InhibitorType0 model."""

# pylint: disable=C0103,R0801,R0902,R0915,C0301,W0235


from sdv.model import (
    DataPointString,
    Model,
)


class InhibitorType0(Model):
    """InhibitorType0 model.

    Attributes
    ----------
    Name: attribute (string)
        Name of the Inhibitor system

    UnlockState: actuator
        State of inhibitor

    """

    def __init__(self, name, parent):
        """Create a new InhibitorType0 model."""
        super().__init__(parent)
        self.name = name

        self.Name = DataPointString("Name", self)
        self.UnlockState = DataPointString("UnlockState", self)
