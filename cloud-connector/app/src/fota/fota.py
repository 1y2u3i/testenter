import base64
import json
import os
import subprocess

import boto3
import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.padding import MGF1, OAEP
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from utils.config_loader import loadConfig


# https://cryptography.io/en/latest/hazmat/primitives/asymmetric/rsa/
def handle_fota_request(fotaRequest, vehicleApp, config, awsClient):
    if "command" in fotaRequest:
        command = fotaRequest["command"]
        if command == "flash-vip":
            file = fotaRequest["file"]
            encryptedKeyBase64 = fotaRequest["key"]
            fota_host_dir = fotaRequest["hostDir"]
            # encryptedKey = base64.b64decode(encryptedKeyBase64)
            # decryptedKeyBase64 = decryptAESKey(encryptedKey, config)
            awsClient.publishFOTAControlMessage("downloading file:" + file)
            tempEncryptedFlashFile, iv = download_file_from_s3(
                file, config, fota_host_dir
            )

            awsClient.publishFOTAControlMessage(
                "download okay, start flashing of:" + tempEncryptedFlashFile
            )
            # if tempEncryptedFlashFile:
            # decryptAESEncryptedFile(
            #    tempEncryptedFlashFile,
            #    tempDecryptedFlashFile,
            #    decryptedKeyBase64,
            #    iv,
            # )

            asyncio.run(
                vehicleApp.publish_event("fota_control_start", tempEncryptedFlashFile)
            )

            return {"state": "ok", "file": tempEncryptedFlashFile}

        else:
            return {"state": "ok"}


def flashFileToTarget(fota_host_dir, awsClient):
    os.chdir(fota_host_dir)
    
    awsClient.publishFOTAControlMessage(str((os.getcwd())))
    try:
        result = subprocess.call(["./flash.sh"])
        print("test")
        # result = subprocess.run(
        #    ["sh", "flash.sh"],
        #    capture_output=True,  # Python >= 3.7 only
        #    text=True,  # Python >= 3.7 only
        # )
        print(result)
    except Exception as e:
        print(e)
        awsClient.publishFOTAControlMessage(str(e))


def encryptAESKey(key, config):
    with open("key.pub", "rb") as f:
        public_key = serialization.load_pem_public_key(f.read())
        print(public_key)
        ciphertext = public_key.encrypt(
            str.encode(key),
            OAEP(
                mgf=MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        return ciphertext


def decryptAESKey(encryptedKey, config) -> bytes | None:
    with open(config.fota_private_key, "rb") as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)
        base64Key = private_key.decrypt(
            encryptedKey,
            OAEP(
                mgf=MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        return base64Key
    return None


def decryptAESEncryptedFile(encryptedFilePath, decryptedFilePath, key, iv):
    with open(encryptedFilePath, "rb") as f:
        cipher = Cipher(
            algorithms.AES(base64.b64decode(key)),
            modes.CBC(base64.b64decode(iv)),
        )
        decryptor = cipher.decryptor()

        decryptedBytes = decryptor.update(f.read()) + decryptor.finalize()
        with open(decryptedFilePath, "wb") as decryptedFile:
            decryptedFile.write(decryptedBytes)


def obtain_temporary_credentials(config):
    device_cert_path = config.cert_filepath
    device_private_key_path = config.pri_key_filepath

    resp = requests.get(
        config.credentials_provider,
        headers={"x-amzn-iot-thingname": config.deviceId},
        cert=(device_cert_path, device_private_key_path),
    )
    print(resp)

    if resp:  # check whether https request succeeds
        credentials = resp.json()
        access_key_id = credentials["credentials"]["accessKeyId"]
        secrete_access_key = credentials["credentials"]["secretAccessKey"]
        session_token = credentials["credentials"]["sessionToken"]
        return access_key_id, secrete_access_key, session_token
    else:
        print("error requesting temporary access to AWS S3")
        return "", "", ""


def download_file_from_s3(file, config, fota_host_dir):
    print(os.getcwd())
    os.chdir(fota_host_dir)
    temp_file = ""
    iv = ""
    access_key_id, secrete_access_key, session_token = obtain_temporary_credentials(
        config
    )
    print("got temporary credentials")
    if access_key_id:
        s3_cli = boto3.client(
            "s3",
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secrete_access_key,
            aws_session_token=session_token,
        )

        for entry in s3_cli.list_objects(Bucket=config.fota_bucket)["Contents"]:
            if "Key" in entry:
                fileKey = entry["Key"]
                if fileKey in file:
                    print("file found in S3 bucket:", entry)
                    metadata = s3_cli.head_object(
                        Bucket=config.fota_bucket, Key=fileKey
                    )
                    # iv = metadata["Metadata"]["iv"]
                    temp_file = f"{fileKey}"
                    with open(temp_file, "wb") as f:
                        s3_cli.download_fileobj(config.fota_bucket, fileKey, f)

    else:
        print("No credentials available for accessing AWS S3")
    return (temp_file, iv)


if __name__ == "__main__":
    sample_message = json.load(open("fota/fota_mqtt_message.json", "r"))
    handle_fota_request(sample_message, loadConfig("../env_var.json"))
