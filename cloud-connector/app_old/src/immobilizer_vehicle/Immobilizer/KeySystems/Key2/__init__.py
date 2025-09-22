#!/usr/bin/env python3

"""Key2 model."""

# pylint: disable=C0103,R0801,R0902,R0915,C0301,W0235


from sdv.model import (
    DataPointString,
    Model,
)


class Key2(Model):
    """Key2 model.

    Attributes
    ----------
    Name: attribute (string)
        Name of the key system

    PermissionState: sensor
        State of the key system

    """

    def __init__(self, name, parent):
        """Create a new Key2 model."""
        super().__init__(parent)
        self.name = name

        self.Name = DataPointString("Name", self)
        self.PermissionState = DataPointString("PermissionState", self)
