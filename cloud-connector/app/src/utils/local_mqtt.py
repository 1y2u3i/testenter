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
