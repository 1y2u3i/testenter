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

import argparse
import asyncio
import json
import time
from threading import Thread

import paho.mqtt.client as localMqtt
from awscrt import mqtt
from awsiot import mqtt_connection_builder

# from vehicle import Vehicle  # type: ignore
from vehicle import Vehicle, vehicle
from sdv.model import DataPoint, DataPointString, Model
from sdv.test.inttesthelper import IntTestHelper

# from sdv.util.log import (  # type: ignore
#    get_opentelemetry_log_factory,
#    get_opentelemetry_log_format,
# )
from sdv.vdb.reply import DataPointReply
from sdv.vehicle_app import VehicleApp

# logging.setLogRecordFactory(get_opentelemetry_log_factory())
# logging.basicConfig(format=get_opentelemetry_log_format())
# logging.getLogger().setLevel("DEBUG")

# logger = logging.getLogger(__name__)

configFile = "/mnt/env_var.json"

message_topic_upstream = "enterer/upstream"
message_topic_down = "enterer/downstream"
STATE_PUBLISH_INTERVALL_SECONDS = 60

awsMqtt: mqtt.Connection
awsConnectionOk = False

localMqttConnection: mqtt.Connection


class LocalConnection:
    def __init__(self, connectorApp) -> None:
        self.app = connectorApp

    def startConnection(self):
        self.t = Thread(target=self.initLocalConnection)
        self.t.start()

    def initLocalConnection(self):
        # Init local mqtt connection
        localMqttClient = localMqtt.Client(localMqtt.CallbackAPIVersion.VERSION1)
        localMqttClient.on_connect = self.on_local_connect
        localMqttClient.on_message = self.on_local_message

        localResult = localMqttClient.connect(
            "127.0.0.1", self.app.config.local_mqtt_port
        )
        localMqttClient.subscribe("#")

        print("Local connection result ", localResult)

        localMqttClient.loop_start()

    def on_local_connect(self, a, b, c, d):
        print("connected ", a, b, c, d)
        pass

    def on_local_message(self, topic, payload, d):
        print(topic, payload)
        pass


class AWSConnection:
    def __init__(self, connectorApp) -> None:
        self.app = connectorApp
        self.lastStatePublish = int(time.time())
        self.publishedData = 0

    def startConnection(self):
        self.t = Thread(target=self.initAWSConnection)
        self.t.start()

    def publishData(self, data):
        global awsMqtt
        global awsConnectionOk
        print("publishing:", data)
        if awsConnectionOk:
            awsMqtt.publish(
                topic=message_topic_upstream,
                payload='{"data":' + data + "}",
                qos=mqtt.QoS.AT_LEAST_ONCE,
            )
            self.publishedData += 1

    def publishState(self):
        global awsMqtt
        global awsConnectionOk
        currentTime = int(time.time())
        deviceState = {
            "state": {"time": currentTime, "publishedData": self.publishedData}
        }
        if (
            awsConnectionOk
            and (currentTime - self.lastStatePublish) > STATE_PUBLISH_INTERVALL_SECONDS
        ):
            self.lastStatePublish = currentTime
            awsMqtt.publish(
                topic=message_topic_upstream,
                payload=json.dumps(deviceState),
                qos=mqtt.QoS.AT_LEAST_ONCE,
            )

    def initAWSConnection(self):
        global awsConnectionOk
        global awsMqtt

        awsMqtt = mqtt_connection_builder.mtls_from_path(
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

        connect_future = awsMqtt.connect()

        # Future.result() waits until a result is available
        connect_future.result()

        print("Connected!")

        deviceSpecificSignalTopicDown = "{baseTopic}/{deviceId}/vss/signal".format(
            baseTopic=message_topic_down, deviceId=self.app.config.deviceId
        )

        deviceSpecificConfigTopicDown = "{baseTopic}/{deviceId}/vss/config".format(
            baseTopic=message_topic_down, deviceId=self.app.config.deviceId
        )

        print("Subscribing to topic '{}'...".format(deviceSpecificSignalTopicDown))
        subscribe_future, packet_id = awsMqtt.subscribe(
            topic=deviceSpecificSignalTopicDown,
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=self.on_signal_message_received,
        )
        subscribe_result = subscribe_future.result()
        print("Subscribed with {}".format(str(subscribe_result["qos"])))

        print("Subscribing to topic '{}'...".format(deviceSpecificConfigTopicDown))
        subscribe_future, packet_id = awsMqtt.subscribe(
            topic=deviceSpecificConfigTopicDown,
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=self.on_config_message_received,
        )
        subscribe_result = subscribe_future.result()
        print("Subscribed with {}".format(str(subscribe_result["qos"])))

        awsConnectionOk = True

        while True:
            time.sleep(1)
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
            print("forwarding to kuksa broker: ", parsedMessage["signal"])
            asyncio.run(
                self.app.transmit(parsedMessage["signal"], parsedMessage["value"])
            )

    # Callback when the subscribed topic receives a config message
    def on_config_message_received(self, topic, payload, dup, qos, retain, **kwargs):
        print("Received config for kuksa.val VSS signal: {}".format(payload))
        # set VSS signal on broker
        parsedMessage = json.loads(payload)
        print(parsedMessage)
        if (
            "name" in parsedMessage
            and "type" in parsedMessage
            and "value" in parsedMessage
        ):
            signalName = parsedMessage["name"]
            signalDatatype = parsedMessage["type"]
            signalValue = parsedMessage["value"]

            asyncio.run(
                self.app.updateSubscriptions(signalName, signalDatatype, signalValue)
            )

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
    def __init__(self, vehicle_client: vehicle):
        super().__init__()
        self.Vehicle = vehicle_client
        self.loadConfig()

        self.signals: dict = {}
        self.currentSignalValues: dict = {}
        self.awsConnection = AWSConnection(self)
        self.awsConnection.startConnection()

        self.localConnection = LocalConnection(self)
        self.localConnection.startConnection()

    def loadConfig(self):
        try:
            f = open(configFile, "r")
        except OSError as err:
            # logger.info(
            #    "Couldn't able open file OSError of sub-Class: %s  %s", type(err), err
            # )
            # logger.info("Argument Parser Take Default Variables")
            print(err)
        else:
            content = json.load(f)
            # logger.info("File content %s:", content)
            f.close()

        # Intializing the Argument Parser
        parser = self.init_argparse(content)
        self.config = parser.parse_args()

    async def recursive_subscribe(self, root):
        for child in root.__dict__:
            attr = getattr(root, child)
            if child == "parent":
                continue
            if attr.__class__.__base__ == DataPoint and any(
                str(attr.get_path()).startswith(signalNameFilter)
                for signalNameFilter in self.config.vss_signals
            ):
                print("subscribing: ", attr.get_path())
                await attr.subscribe(self.on_signal_changed)
                self.signals[attr.get_path()] = attr
            elif attr.__class__.__base__ == Model:
                await self.recursive_subscribe(attr)

    async def on_start(self):
        self.Vehicle.Body.
        await self.recursive_subscribe(self.Vehicle)

    async def on_signal_changed(self, data: DataPointReply):
        hasChanged = False
        print("########################changed######################")
        for signalName in self.signals.keys():
            value = data.get(self.signals[signalName]).value
            if not value:
                continue
            if signalName not in self.currentSignalValues:
                hasChanged = True
            else:
                hasChanged = hasChanged or self.currentSignalValues[signalName] != value
            self.currentSignalValues[signalName] = value
        if hasChanged:
            # logger.info("changed, transmitting")
            self.awsConnection.publishData(json.dumps(self.currentSignalValues))

    async def updateSubscriptions(self, signalName, signalType, signalValue):
        print("######################################updating subscriptions")
        bla = DataPointString(signalName, self.Vehicle)

        if bla.get_path() not in self.signals:
            print("adding new signal: " + bla.get_path())
            self.signals[bla.get_path()] = bla
            await bla.subscribe(self.on_signal_changed)

    async def transmit(self, signalName, data):
        print("sending on kuksa broker ", signalName, " ", data)
        inttesthelper = IntTestHelper()
        if isinstance(data, str):
            response = await inttesthelper.set_string_datapoint(
                name=signalName, value=data
            )
        else:
            response = await inttesthelper.set_bool_datapoint(
                name=signalName, value=data
            )

        print(response)

    def init_argparse(self, content) -> argparse.ArgumentParser:
        """This inits the argument parser for ENV Variable used in Kanto-cm container"""
        parser = argparse.ArgumentParser(
            usage="--variable_name=value",
            description="This will get the variable from mounted file to the Kanto-cm container",
        )

        parser.add_argument(
            "--endpoint",
            default=content.get("endpoint", "Default endpoint not set"),
            help="This will get the endpoint details"
            "The default cert path  a1poqnhtwgj0le-ats.iot.eu-central-1.amazonaws.com",
        )

        parser.add_argument(
            "--deviceId",
            default=content.get("deviceId", "AWS device id not set"),
            help="This will get the AWS device id",
        )

        parser.add_argument(
            "--cert_filepath",
            default=content.get("cert_filepath", "Default cert_filepath Not set"),
            help="This indicates the aws cert file path"
            " The default cert_filepath not yet set",
        )

        parser.add_argument(
            "--pri_key_filepath",
            default=content.get("pri_key_filepath", "pri_key_filepath not set"),
            help="This will get pri_key_filepath value"
            "The default pri_key_filepath value not yet set",
        )

        parser.add_argument(
            "--ca_filepath",
            default=content.get("ca_filepath", "Default ca_filepath Value not set "),
            help="This will get the ca_filepath details"
            "The default ca_filepath value not yet set",
        )
        parser.add_argument(
            "--vss_signals",
            default=content.get("vss_signals", "No VSS signal filters set "),
            help="This will get the vss_signal filters" "No VSS signal filter set",
        )

        parser.add_argument(
            "--local_mqtt_port",
            default=content.get("local_mqtt_port", "No local mqtt port set "),
            help="This will get the local mqtt port" "No local mqtt port set",
        )
        return parser
