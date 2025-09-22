import glob
import os

import boto3
import requests
from utils.config_loader import loadConfig


def scan_dir_and_upload(directory, filter):
    config = loadConfig("/mnt/env_var.json")
    print("directory to scan: ", directory)
    uploadResult = []
    os.chdir(directory)
    for file in glob.glob(filter):
        print("scanned:", file)
        fileResult = {"name": file, "result": ""}
        try:
            fileResult["result"] = upload_file_to_s3(file, config)
        except Exception as e:
            fileResult["result"] = e

        uploadResult.append(fileResult.copy())
    return uploadResult


def upload_file_to_s3(file, config):
    result = ""
    access_key_id, secrete_access_key, session_token = obtain_temporary_credentials(
        config
    )
    if access_key_id:
        object_name = os.path.basename(file)
        s3_cli = boto3.client(
            "s3",
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secrete_access_key,
            aws_session_token=session_token,
        )
        s3_cli.upload_file(file, config.upload_bucket, object_name)
        result = "success"
    else:
        print("No credentials available for accessing AWS S3")
        result = "AWS S3 credentials missing"

    return result


def obtain_temporary_credentials(config):
    device_cert_path = config.cert_filepath
    device_private_key_path = config.pri_key_filepath

    resp = requests.get(
        config.credentials_provider,
        headers={"x-amzn-iot-thingname": config.deviceId},
        cert=(device_cert_path, device_private_key_path),
    )

    if resp:  # check whether https request succeeds
        credentials = resp.json()
        access_key_id = credentials["credentials"]["accessKeyId"]
        secrete_access_key = credentials["credentials"]["secretAccessKey"]
        session_token = credentials["credentials"]["sessionToken"]
        return access_key_id, secrete_access_key, session_token
    else:
        print("error requesting temporary access to AWS S3")
        return "", "", ""
