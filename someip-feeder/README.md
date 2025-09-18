# SOME/IP Configuration (config/feeder_mapping.json)
This project is the modified version of SOME/IP provider [Kuksa-SomeIP-Provider](https://github.com/eclipse-kuksa/kuksa-someip-provider) with service mapping using a JSON file.The json configuration maps the SOME/IP service payload to VSS using a JSON file. The example JSON file provided demonstrates the configuration for a specific SOME/IP service.

## Table of Contents

1. [Introduction](#introduction)
2. [JSON Structure](#json-structure)
3. [Configuration Details](#configuration-details)
4. [Example Configuration](#example-configuration)

## Introduction

SOME/IP (Scalable service-Oriented MiddlewarE over IP) is a protocol used in automotive systems for communication between ECUs (Electronic Control Units). Configuring the SOME/IP mapping involves defining the services, events, and data types exchanged between different ECUs. Also the payload offset and length information from which data needs to be extarcted and transform to VSS. 

## JSON Structure

The configuration file follows a specific JSON structure to define the SOME/IP mapping. Below is a simplified structure of the JSON file:

```json
{
  "SomeipMapping": [
    {
      "ServiceType": "Event",
      "ServiceID": 1999,
      "InstanceID": 802,
      "EventID": 32895, 
      "EventGroup": 1,
      "MAJOR_VERSION": 1,
      "MINOR_VERSION": 0,
      "VSSNode": [
        {
          "Name": "Vehicle.Immobilizer.KeySystems.Key1.PermissionState",
          "ByteOffset": 0,
          "DataType": "UINT32",
          "Length": 4,
          "Transform": {
            "transform": [
              {
                "from": 0,
                "to": "Default"
              },
              {
                "from": 1,
                "to": "Release"
              },
              {
                "from": 2,
                "to":"Inhibit" 
              },
              {
                "from": 3,
                "to": "Others"
              }
            ]
          }
        }
      ]
    }
  ]
}

```
## Configuration Details

- **ServiceType**: Specifies the type of service (e.g., Event, Method, Field).
- **ServiceID**: Unique identifier for the service.
- **InstanceID**: Identifier for the specific instance of the service.
- **EventID**: Unique identifier for the event.
- **EventGroup**: Group identifier for the event.
- **MAJOR_VERSION**: Major version of the service.
- **MINOR_VERSION**: Minor version of the service.
- **VSSNode**: Array containing details of the data nodes within the service.
  - **Name**: Name of the data node.
  - **ByteOffset**: Offset of the data node in bytes.
  - **DataType**: Data type of the data node.
  - **Length**: Length of the data node.
  - **Transform**: Transformation rules for the data node.
    - **transform**: Array containing transformation rules.
      - **from**: Original value.
      - **to**: Transformed value.

## Example Event Configuration

Below is an example configuration based on the provided JSON file:

```json
{
  "SomeipMapping": [
    {
      "ServiceType": "Event",
      "ServiceID": 1999,
      "InstanceID": 802,
      "EventID": 32895,
      "EventGroup": 1,
      "MAJOR_VERSION": 1,
      "MINOR_VERSION": 0,
      "VSSNode": [
        {
          "Name": "Vehicle.Immobilizer.KeySystems.Key1.PermissionState",
          "ByteOffset": 0,
          "DataType": "UINT32",
          "Length": 4,
          "Transform": {
            "transform": [
              {
                "from": 0,
                "to": "Default"
              },
              {
                "from": 1,
                "to": "Release"
              },
              {
                "from": 2,
                "to": "Inhibit"
              },
              {
                "from": 3,
                "to": "Others"
              }
            ]
          }
        }
      ]
    }
  ]
}
```

This configuration defines a SOME/IP service of type Event with a specific service ID, instance ID, and event ID. It includes a single VSS node named "Vehicle.Immobilizer.KeySystems.Key1.PermissionState" of type UINT32 with transformation rules defined for its values. The payload from SOMEIP Event is transformed and feed to the VSS specified in the VSS node. 

The same configuration can be used for SOMEIP Method with "ServiceType" as "Method", here the VSS set request will be send as SOMEIP method request if transform node is added the transformed value will be send to service method request else raw value from vss will be filled in the payload for sending the method request.
Example configuration.

## Example Method Configuration

Below is an example configuration based on the provided JSON file:

```json
{
      "ServiceType": "Method",
      "ServiceID": 24867,
      "InstanceID": 11,
      "MethodID": 7,
      "MAJOR_VERSION": 1,
      "MINOR_VERSION": 0,
      "VSSNode": [
        {
          "Name": "Vehicle.Body.Windshield.Front.Wiping.System.Mode",
          "ByteOffset": 5,
          "DataType": "UINT8",
          "Length": 1,
          "Transform": {
            "transform": [
              {
                "from": "PLANT_MODE",
                "to": 0
              },
              {
                "from": "STOP_HOLD",
                "to": 1
              },
              {
                "from": "WIPE",
                "to": 2
              },
              {
                "from": "EMERGENCY_STOP",
                "to": 3
              }
            ]
          }
        },
        {
          "Name": "Vehicle.Body.Windshield.Front.Wiping.System.Frequency",
          "ByteOffset": 0,
          "DataType": "UINT8",
          "Length": 1
        },
        {
          "Name": "Vehicle.Body.Windshield.Front.Wiping.System.TargetPosition",
          "ByteOffset": 1,
          "DataType": "FLOAT",
          "Length": 4
        }
      ]
    }
```

## Note: 
The someip configuration currently supports only one event and one method.
