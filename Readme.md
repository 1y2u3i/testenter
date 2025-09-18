# Provision CCU

## Flash Debian
(Taken from: https://pages.github.boschdevcloud.com/sdv/red-edgers-documentation/020_Projects/021_Owasys%20owa5x/023_Flashing/README.html)

1. Open 2 or 3 terminals on the Linux-PC connected to the owa5x.

Note: it is recommended to open 2 or 3 terminals:
- 1st to connect to owa5x device via serial connection (see step 2)
- 2nd to issue flash command on Linux-PC (see step 4)
- {3rd to switch device off/on (this can of course be done manually)}

2. Erase the U-Boot partition on owa5x:
- Reboot the owa5x
- Enter the U-Boot prompt by pressing immediately space in the terminal while booting (trigger boot either by switching the device off/on or issuing the command ‘reboot’) On U-Boot prompt enter:

`$u-boot-> nand erase.part NAND.u-boot`

3. Turn owa5x off.

4. Execute the flashig tool on Linux-PC:

`$ sudo ~/uuu owa_uboot_nand_kernel_emmc_YOCTO_1.0.1.uuu`

Initially it waits for a new USB device.

5. Turn owa5x on.

Without U-Boot it should start in flash-mode now. The flashing tool on PC notices the owa5x as new USB device (e.g. /dev/hidraw3) and begins to write the 4 flash files to the corresponding memory onboard the owa5x. The progress bar shows the name of the flashed files. In the terminal you can see the flash status on owa5x in parallel.

The flash process finishes after ~4 minutes with output:

1:5 20/20 Done FB: Done

6. Turn owa5x off and on again.

It boots now with the new U-Boot, kernel and root-fs. Check in the terminal that the file dates accord to the build date.

## Connect WIFI
`sudo nano /etc/wpa_supplicant/wpa.conf`
Something like:
>network={
>        ssid="BWSDEV"
>        psk=xxxx
>}

Restart Network Service with: `sudo systemctl restart wpa_supplicant.service`

## Set DNS Server
`sudo nano /etc/systemd/resolved.conf`

DNS=8.8.8.8#dns.google

Restart Resolver: `sudo systemctl restart systemd-resolved.service`

## Expand File System
Execute: `./initial.sh --expand_fdisk --install_docker`

## Setup Docker

https://docs.docker.com/engine/install/debian/

### Create new data root directory in expanded storage
Create: `sudo mkdir /data/docker'

Change data root to: /data/docker
`sudo nano /etc/docker/daemon.json`
`{"data-root": "/data/docker"}`

Restart docker service
`sudo systemctl restart docker.service`
 
The docker-compose.yaml must be located in `/home/debian`, it configures:
- Mosquitto Broker
- kuksa.val Databroker
- Cloud Connector
- SOME/IP Feeders

Run with: `docker compose -f docker-compose.yaml up -d`

## Components
### Cloud Connector
The cloud connector handles all connections to AWS IOT Core and S3 storage.\
It runs within docker

### FOTA Service
Base FOTA directory is: `/data/fota`

FOTA Service runs as a system service, configured from `/etc/systemd/system/fota.service`.\
`sudo systemctl start|stop|status fota.service` \
\
The FOTA Service executes the flash.sh script located in /data/fota, which listens for mosquitto messages on topic `fota_control_start`.\
On receiving a message with a FOTA package file, the script checks if the file exists and if so, calls flash_vip.sh (currently only FOTA for VIP is supported)\
The script will run in a loop (call itself after finishing)


# Troubleshooting

For both Yocta and Debian based, ssh into the CCU via Ethernet Connection: `ssh 192.168.56.6`

Yocto based: root and no Password
Debian based: debian:temppwd

1. Check Internet connection
   `ping google.de` needs to resolve, if not check if WIFI is connected
2. Check connection to VIP
   `ping 192.168.56.49` needs to respond
3. Check if containers are running
   - Yocto based: kanto-cm list
   - Debian based: docker ps
   For both, all containers must be shown as `Running` 
   

