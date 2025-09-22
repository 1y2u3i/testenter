import argparse
import json


def loadConfig(configFile):
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
    parser = init_argparse(content)
    return parser.parse_args()


def init_argparse(content) -> argparse.ArgumentParser:
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

    parser.add_argument(
        "--credentials_provider",
        default=content.get("credentials_provider", "No credentials provider URL set "),
        help="This will set the AWS credentials provider URL"
        "No credentials provider URL set",
    )

    parser.add_argument(
        "--fota_bucket",
        default=content.get("fota_bucket", "No AWS S3 FOTA Bucket set "),
        help="This will set the AWS S3 FOTA Bucket name" "No AWS S3 FOTA Bucket set",
    )

    parser.add_argument(
        "--fota_public_key",
        default=content.get("fota_public_key", "No FOTA public key path set "),
        help="This will set the FOTA public key path" "No FOTA public key path set",
    )

    parser.add_argument(
        "--fota_private_key",
        default=content.get("fota_private_key", "No FOTA private key path set "),
        help="This will set the FOTA private key path" "No FOTA private key path set",
    )

    parser.add_argument(
        "--upload_bucket",
        default=content.get("upload_bucket", "No AWS S3 Upload Bucket set "),
        help="This will set the AWS S3 Upload Bucket" "No AWS S3 Upload Bucket set",
    )

    return parser
