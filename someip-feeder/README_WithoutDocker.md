# Feeder Service Installation Guide

This guide provides step-by-step instructions to install and set up the Feeder service on the CCU without docker.

## Installation Steps

1. **Copy the archive to `/opt/feeder/` in the target**  
   ```sh
   mkdir -p /opt/feeder/
   cp someip2val_aarch64_release.tar.gz /opt/feeder/

2. **Extract the archive**
   ```sh
   cd /opt/feeder/
   tar -xzvf someip2val_aarch64_release.tar.gz
   
3. **Setting Up the Service**
   - Navigate to the Feeder directory
	   ```sh
	   cd /opt/feeder/
	   
   - Set the executable permission to the script files
	   ```sh
	   chmod +x bin/execute-apps.sh bin/setup-someip2val.sh bin/someip_feeder
   
   - Copy the service file to systemd directory
	   ```sh
	   cp feeder.service /etc/systemd/system/feeder.service
	   
   - Reload systemd to recognize the new service
	   ```sh
	   systemctl daemon-reload
   
   - Enable the service to start on boot
	   ```sh
	   systemctl enable feeder.service
	   
   - Start the Feeder service
	   ```sh
	   systemctl start feeder.service
	   
   - Check the status of the service
	   ```sh
	   systemctl status feeder.service

## Steps to get `someip2val_aarch64_release.tar.gz` file updated:
   - Move in to the directory CCU/someip-feeder and run the build script it will automaticaly generate the tar.gz file in the same folder
	   ```sh
      cd CCU/someip-feeder
	   ./build-release.sh aarch64

## Note: 
- If facing any compiler error during the build, similar to
  ```sh
  Compiler version specified in your conan profile: 11
  Compiler version detected in CMake: 10.2

- Then edit the file `toolchains/target_aarch64_Release` and change the line `compiler.version=11` to `compiler.version=10`