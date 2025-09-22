### Howto
Cloud Connector should start from `./cleanup.sh`
Else:

`kanto-cm create --name aws-cloud-connector --log-driver=none --e="SDV_MQTT_ADDRESS=mqtt://127.0.0.1:1883" --network host --e="SDV_MIDDLEWARE_TYPE=native" --e="SDV_VEHICLEDATABROKER_ADDRESS=grpc://127.0.0.1:55555" --hosts="mosquitto:192.168.56.6" ghcr.io/bosch-engineering/swdv.enterer.aws-cloud-connector:minidemocartechdayV2`

`kanto-cm start --name aws-cloud-connector`
