# Copyright (c) 2022-2023 Robert Bosch GmbH and Microsoft Corporation
#
# This program and the accompanying materials are made available under the
# terms of the Apache License, Version 2.0 which is available at
# https://www.apache.org/licenses/LICENSE-2.0.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# SPDX-License-Identifier: Apache-2.0

"""A sample Velocitas vehicle app for adjusting seat position."""

import asyncio
import json
import signal
import sys
import time
from functools import partial
from threading import Thread

from awscrt import mqtt
from awsiot import mqtt_connection_builder
from fota.fota import handle_fota_request
from minidemocar2_pb2 import Vehicle as ProtoVehicle
from uploader.uploader import scan_dir_and_upload
from utils.config_loader import loadConfig

# from vehicle import Vehicle  # type: ignore
from vehicle import Vehicle, vehicle
from velocitas_sdk.model import DataPoint, Model
from velocitas_sdk.test.inttesthelper import IntTestHelper
from velocitas_sdk.vdb.reply import DataPointReply

# from sdv.util.log import (  # type: ignore
#    get_opentelemetry_log_factory,
#    get_opentelemetry_log_format,
# )
from velocitas_sdk.vehicle_app import VehicleApp, subscribe_topic

# logging.setLogRecordFactory(get_opentelemetry_log_factory())
# logging.basicConfig(format=get_opentelemetry_log_format())
# logging.getLogger().setLevel("DEBUG")

# logger = logging.getLogger(__name__)

configFile = "/mnt/env_var.json"

message_topic_upstream_ack = "enterer/upstream/SDV_E2E_MiniDemoCar_China"
message_topic_upstream = "enterer/upstream/SDV_E2E_MiniDemoCar_China/binary"
message_topic_upstream_fota_control = (
    "enterer/upstream/SDV_E2E_MiniDemoCar_China/fota_control"
)
message_topic_down = "enterer/downstream"
# message_topic_telemetry_upstream = "enterer/upstream/telemetry"

STATE_PUBLISH_INTERVALL_MS = 1000
IDLE_STATE_PUBLISH_INTERVALL_MS = 5000
IDLE_STATE_TRIGGER_TIME_MS = 600000


def timeMillis():
    return int(round(time.time() * 1000))


class AWSConnection:
    def __init__(self) -> None:
        self.stateUpdateRateMs = STATE_PUBLISH_INTERVALL_MS
        self.idleStateTriggerTimeMs = IDLE_STATE_TRIGGER_TIME_MS
        self.idleStatePublishIntervall = IDLE_STATE_PUBLISH_INTERVALL_MS
        self.lastStatePublish = timeMillis()
        self.lastReceiveTime = timeMillis()
        self.userDefinedStateUpdateRateMs = self.stateUpdateRateMs

        self.proto = ProtoVehicle()
        self.deviceState = {}
        self.protoMapping = {}
        self.config = {}
        self.fotaMessageBuffer = []

        self.binary = True
        self.needTransmit = False
        self.statePublishRetain = True
        self.awsConnectionOk = False

    def startConnection(self, vehicleConnectorApp):
        self.app = vehicleConnectorApp
        self.t = Thread(target=self.initAWSConnection)
        self.t.start()

    def publishSignal(self, data):
        signalName = data["name"]
        signalValue = data["value"]
        self.deviceState[signalName] = signalValue
        try:
            signalPath = signalName.split(".")
            if signalName not in self.protoMapping:
                # insert into protobuf structure
                protoNode = self.proto
                for node in signalName.split(".")[1:-1]:
                    protoNode = getattr(protoNode, node)
                self.protoMapping[signalName] = protoNode
            if (
                self.protoMapping[signalName]
                .DESCRIPTOR.fields_by_name[signalPath[-1]]
                .label
                != 3
            ):
                setattr(self.protoMapping[signalName], signalPath[-1], signalValue)
            else:
                repeatedAttr = getattr(self.protoMapping[signalName], signalPath[-1])
                del repeatedAttr[:]
                repeatedAttr.extend(signalValue)
            self.needTransmit = True
        except Exception as e:
            print("error:", e)

    def publishState(self):
        currentTime = timeMillis()
        try:
            timeDiffMs = currentTime - self.lastStatePublish
            if self.awsConnectionOk:
                # if we did not transmit within the last 10 seconds, we transmit in any case
                self.needTransmit |= timeDiffMs > 500
                if self.binary and self.needTransmit:
                    self.awsMqtt.publish(
                        topic=message_topic_upstream,
                        payload=self.proto.SerializeToString(),
                        qos=mqtt.QoS.AT_LEAST_ONCE,
                        retain=self.statePublishRetain,
                    )
                    self.lastStatePublish = currentTime
                    self.needTransmit = False
                # non binary protocol transmits alyways at base rate
                elif not self.binary:
                    pass
                    # self.awsMqtt.publish(
                    #    topic=message_topic_telemetry_upstream,
                    #    payload=json.dumps(self.deviceState),
                    #    qos=mqtt.QoS.AT_LEAST_ONCE,
                    # )

        except Exception as e:
            print(e)

    def publishFOTAControlMessage(self, payload):
        if self.awsConnectionOk:
            self.fotaMessageBuffer.append(payload)
            self.awsMqtt.publish(
                topic=message_topic_upstream_fota_control,
                payload=json.dumps(self.fotaMessageBuffer),
                qos=mqtt.QoS.AT_LEAST_ONCE,
                retain=True,
            )

    def publishACKMessage(self, payload):
        payloadData = json.loads(payload)
        if self.awsConnectionOk and "sessionId" in payloadData:
            response = {"ack": payloadData["sessionId"]}
            self.awsMqtt.publish(
                topic=message_topic_upstream_ack,
                payload=json.dumps(response),
                qos=mqtt.QoS.AT_LEAST_ONCE,
            )

    def initAWSConnection(self):
        self.awsMqtt = mqtt_connection_builder.mtls_from_path(
            endpoint=self.app.config.endpoint,
            cert_filepath=self.app.config.cert_filepath,
            pri_key_filepath=self.app.config.pri_key_filepath,
            ca_filepath=self.app.config.ca_filepath,
            on_connection_interrupted=self.on_connection_interrupted,
            on_connection_resumed=self.on_connection_resumed,
            client_id=self.app.config.deviceId,
            clean_session=False,
            keep_alive_secs=30,
            on_connection_success=self.on_connection_success,
            on_connection_failure=self.on_connection_failure,
            on_connection_closed=self.on_connection_closed,
        )

        try:
            connect_future = self.awsMqtt.connect()
            connect_future.result()
        except Exception as e:
            print("connected failed: " + str(e))
            sys.exit(-1)

        print("Connected!")

        deviceSpecificSignalTopicDown = "{baseTopic}/{deviceId}/vss/signal".format(
            baseTopic=message_topic_down, deviceId=self.app.config.deviceId
        )

        deviceSpecificConfigTopicDown = "{baseTopic}/{deviceId}/vss/config".format(
            baseTopic=message_topic_down, deviceId=self.app.config.deviceId
        )

        deviceSpecificFotaTopicDown = "{baseTopic}/{deviceId}/fota".format(
            baseTopic=message_topic_down, deviceId=self.app.config.deviceId
        )

        print("Subscribing to topic '{}'...".format(deviceSpecificSignalTopicDown))
        subscribe_future, packet_id = self.awsMqtt.subscribe(
            topic=deviceSpecificSignalTopicDown,
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=self.on_signal_message_received,
        )
        subscribe_result = subscribe_future.result()
        print("Subscribed with {}".format(str(subscribe_result["qos"])))

        print("Subscribing to topic '{}'...".format(deviceSpecificConfigTopicDown))
        subscribe_future, packet_id = self.awsMqtt.subscribe(
            topic=deviceSpecificConfigTopicDown,
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=self.on_config_message_received,
        )
        subscribe_result = subscribe_future.result()
        print("Subscribed with {}".format(str(subscribe_result["qos"])))

        print("Subscribing to topic '{}'...".format(deviceSpecificFotaTopicDown))
        subscribe_future, packet_id = self.awsMqtt.subscribe(
            topic=deviceSpecificFotaTopicDown,
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=self.on_fota_message_received,
        )
        subscribe_result = subscribe_future.result()
        print("Subscribed with {}".format(str(subscribe_result["qos"])))

        self.awsConnectionOk = True

        while True:
            time.sleep(0.2)
            currentTime = timeMillis()
            if (currentTime - self.lastReceiveTime) > IDLE_STATE_TRIGGER_TIME_MS:
                self.stateUpdateRateMs = IDLE_STATE_PUBLISH_INTERVALL_MS

            self.publishState()

    # Callback when connection is accidentally lost.
    def on_connection_interrupted(self, connection, error, **kwargs):
        print("Connection interrupted. error: {}".format(error))

    # Callback when an interrupted connection is re-established.
    def on_connection_resumed(self, connection, return_code, session_present, **kwargs):
        print(
            "Connection resumed. return_code: {} session_present: {}".format(
                return_code, session_present
            )
        )

        if return_code == mqtt.ConnectReturnCode.ACCEPTED and not session_present:
            print("Session did not persist. Resubscribing to existing topics...")
            resubscribe_future, _ = connection.resubscribe_existing_topics()

            # Cannot synchronously wait for resubscribe result because we're on the connection's event-loop thread,
            # evaluate result with a callback instead.
            resubscribe_future.add_done_callback(self.on_resubscribe_complete)

    def on_resubscribe_complete(self, resubscribe_future):
        resubscribe_results = resubscribe_future.result()
        print("Resubscribe results: {}".format(resubscribe_results))

        for topic, qos in resubscribe_results["topics"]:
            if qos is None:
                sys.exit("Server rejected resubscribe to topic: {}".format(topic))

    # Callback when the subscribed topic receives a signal message
    def on_signal_message_received(self, topic, payload, dup, qos, retain, **kwargs):
        print("Received message from topic '{}': {}".format(topic, payload))
        # publish on local broker
        parsedMessage = json.loads(payload)
        if "signal" in parsedMessage:
            self.publishACKMessage(payload)
            self.lastReceiveTime = timeMillis()
            self.stateUpdateRateMs = self.userDefinedStateUpdateRateMs
            asyncio.run(
                self.app.transmit(
                    parsedMessage["signal"],
                    parsedMessage["value"],
                    parsedMessage.get("type"),
                )
            )

    # Callback when the subscribed topic receives a config message
    def on_config_message_received(self, topic, payload, dup, qos, retain, **kwargs):
        print("Received config for kuksa.val VSS signal: {}".format(payload))
        # set VSS signal on broker
        parsedMessage = json.loads(payload)
        if "ignoreList" in parsedMessage:
            print(parsedMessage["ignoreList"])
            self.app.ignoreList = parsedMessage["ignoreList"]
        if "stateUpdateRateMs" in parsedMessage:
            self.userDefinedStateUpdateRateMs = parsedMessage["stateUpdateRateMs"]
            self.stateUpdateRateMs = self.userDefinedStateUpdateRateMs
        if "idleStateTriggerTimeMs" in parsedMessage:
            self.idleStateTriggerTimeMs = parsedMessage["idleStateTriggerTimeMs"]
        if "idleStatePublishIntervall" in parsedMessage:
            self.idleStatePublishIntervall = parsedMessage["idleStatePublishIntervall"]
        if "binary" in parsedMessage:
            self.binary = parsedMessage["binary"]
        if "scan_and_upload" in parsedMessage and "scan_filter" in parsedMessage:
            result = scan_dir_and_upload(
                parsedMessage["scan_and_upload"], parsedMessage["scan_filter"]
            )
            self.awsMqtt.publish(
                topic=message_topic_upstream,
                payload=json.dumps({"scan_and_upload": result}),
                qos=mqtt.QoS.AT_LEAST_ONCE,
            )
        if "statePublishRetain" in parsedMessage:
            self.statePublishRetain = parsedMessage["statePublishRetain"]

        self.config = {**self.config, **parsedMessage}
        self.awsMqtt.publish(
            topic=message_topic_upstream,
            payload=json.dumps(self.config),
            qos=mqtt.QoS.AT_LEAST_ONCE,
        )

    # Callback when the subscribed topic receives a FOTA message
    def on_fota_message_received(self, topic, payload, dup, qos, retain, **kwargs):
        print("Received FOTA message {}".format(payload))
        try:
            self.fotaMessageBuffer.clear()
            
            self.publishFOTAControlMessage("Cloud Connector received FOTA request")
            # needs to be async

            print("send message")
            thread = Thread(
                target=handle_fota_request,
                args=(json.loads(payload), self.app, self.app.config, self),
            )

            thread.start()

            print("launched handler")
        except Exception as e:
            print(e)
            self.publishFOTAControlMessage("fota request failed:" + str(e))

    # Callback when the connection successfully connects
    def on_connection_success(self, connection, callback_data):
        assert isinstance(callback_data, mqtt.OnConnectionSuccessData)
        print(
            "Connection Successful with return code: {} session present: {}".format(
                callback_data.return_code, callback_data.session_present
            )
        )

    # Callback when a connection attempt fails
    def on_connection_failure(self, connection, callback_data):
        assert isinstance(callback_data, mqtt.OnConnectionFailureData)
        print("Connection failed with error code: {}".format(callback_data.error))

    # Callback when a connection has been disconnected or shutdown successfully
    def on_connection_closed(self, connection, callback_data):
        print("Connection closed")


class ConnectorApp(VehicleApp):
    def __init__(self, vehicle_client: Vehicle, awsConnection):
        super().__init__()
        self.Vehicle = vehicle_client
        self.config = loadConfig(configFile)

        self.signals: dict = {}
        self.ignoreList = []

        self.awsConnection = awsConnection

    @subscribe_topic("fota_control")
    async def on_set_position_request_received(self, data_str: str) -> None:
        print("#################### data mqtt")
        print(data_str)
        await self.awsConnection.publishFOTAControlMessage(data_str)
        print("published message")

    async def recursive_subscribe(self, root):
        for child in root.__dict__:
            attr = getattr(root, child)
            if child == "parent":
                continue

            if attr.__class__.__base__ == DataPoint and any(
                str(attr.get_path()).startswith(signalNameFilter)
                for signalNameFilter in self.config.vss_signals
            ):
                signalName = attr.get_path()
                print("subscribing: ", signalName)
                await attr.subscribe(partial(self.on_signal_changed, signalName))

                self.signals[signalName] = attr
            elif attr.__class__.__base__ == Model:
                await self.recursive_subscribe(attr)

    async def on_start(self):
        await self.recursive_subscribe(self.Vehicle)

    async def on_signal_changed(self, signalName, data: DataPointReply):
        try:
            if signalName in self.ignoreList:
                return
            signal = data.get(self.signals[signalName])
            if signalName and signal:
                timestampSeconds = signal.timestamp.seconds
                timestampNanos = signal.timestamp.nanos
                self.awsConnection.publishSignal(
                    {
                        "name": signalName,
                        "value": signal.value,
                        "timeSec": timestampSeconds,
                        "timeNano": timestampNanos,
                    }
                )
        except Exception as e:
            print(e)

    async def transmit(self, signalName, data, type=None):
        # print("sending on kuksa broker ", signalName, " ", data)
        try:
            inttesthelper = IntTestHelper()
            if type is not None and type == "int16[]":
                # print("putting int16[] on broker")
                await inttesthelper.set_int16Array_datapoint(
                    name=signalName, value=data
                )
            elif type is not None and type == "uint8":
                # print("putting uint8 on broker")
                await inttesthelper.set_uint8_datapoint(name=signalName, value=data)
            elif isinstance(data, str):
                # print("putting string on broker")
                await inttesthelper.set_string_datapoint(name=signalName, value=data)
            elif isinstance(data, list):
                # print("putting list on broker: ")
                await inttesthelper.set_uint8Array_datapoint(
                    name=signalName, value=data
                )
            else:
                # print("putting boolean on broker")
                await inttesthelper.set_bool_datapoint(name=signalName, value=data)
        except Exception as e:
            print(e)


async def main():
    awsConnection = AWSConnection()
    vehicle_app = ConnectorApp(vehicle, awsConnection)
    awsConnection.startConnection(vehicle_app)
    await vehicle_app.run()


LOOP = asyncio.get_event_loop()
LOOP.add_signal_handler(signal.SIGTERM, LOOP.stop)
LOOP.run_until_complete(main())
LOOP.close()
