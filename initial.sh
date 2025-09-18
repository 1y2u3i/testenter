#!/bin/bash

# Script Name: initial.sh
# Description: This script performs initial setup of Owasys OWA5X for Trackbeast.
# Author: Jonathan Fink
# Date: 2025-01-20

# Remove Systemd Presets
function remove_presets() {
    echo "Removing GPS preset..."
    rm /usr/lib/systemd/system-preset/98-owasys-pollux-gps.preset
    echo "Removing Mobile Network preset..."
    rm /usr/lib/systemd/system-preset/98-owasys-pollux-net.preset
    echo "Setting presets in systemd..."
    systemctl preset-all
}

function install_docker(){
    apt-get update
    apt-get install ca-certificates curl
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc

    # Add the repository to Apt sources:
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
    tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update
    apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

function expand_fdisk() {
    STR_FSTAB="/dev/mmcblk2p2"


    DEV_FSTAB=$(grep data_backup /etc/fstab | awk '{print $1}')
    echo "FSTAB:$DEV_FSTAB"
    if [ "$DEV_FSTAB" = "$STR_FSTAB" ]; then
    echo "No need to update /etc/fstab"
    else

    echo "
    d
    n
    p
    1
    2048
    12000000
    N
    n
    p
    2


    N
    w" | fdisk /dev/mmcblk2

    resize2fs /dev/mmcblk2p1
    echo "y" | mkfs.ext4 /dev/mmcblk2p2
    echo "/dev/mmcblk2p2    /data_backup/   ext4          defaults         0      0" >> /etc/fstab
    echo "/etc/fstab updated"
    mkdir /data_backup
    mount -a
    fi     
}

function emmc_overlay() {
    read -p "This step might delete some data. Are you sure you want to proceed with eMMC overlay setup? (Y/n): " confirm
    if [[ "$confirm" != "Y" && "$confirm" != "y" ]]; then
        echo "eMMC overlay setup aborted."
        exit 1
    fi
    echo "Remove old Links..."
    rm -r /var/lib/docker
    rm -r /var/lib/losant-edge-agent
    rm -r /var/log
    rm -r /home/db
    rm -r /home/log
    rm -r /data/var
    rm -r /data/home
    echo "Generate log place..."
    mkdir /var/log
    echo "Prepare overlay..."
    mkdir -p /data/overlay/usr/upper
    mkdir -p /data/overlay/usr/working
    # mkdir -p /data/overlay/etc/upper
    # mkdir -p /data/overlay/etc/working
    mkdir -p /data/overlay/var/upper
    mkdir -p /data/overlay/var/working
    mkdir -p /data/overlay/home/upper
    mkdir -p /data/overlay/home/working
    mkdir -p /data/overlay/tmp/upper
    mkdir -p /data/overlay/tmp/working
    echo "Mount overlay..."
    echo "overlay /usr overlay x-systemd.requires=/data,defaults,lowerdir=/usr,upperdir=/data/overlay/usr/upper,workdir=/data/overlay/usr/working 0 0" >> /etc/fstab
    # echo "overlay /etc overlay x-systemd.requires=/data,defaults,lowerdir=/etc,upperdir=/data/overlay/etc/upper,workdir=/data/overlay/etc/working 0 0" >> /etc/fstab
    echo "overlay /var overlay x-systemd.requires=/data,defaults,lowerdir=/var,upperdir=/data/overlay/var/upper,workdir=/data/overlay/var/working 0 0" >> /etc/fstab
    echo "overlay /home overlay x-systemd.requires=/data,defaults,lowerdir=/home,upperdir=/data/overlay/home/upper,workdir=/data/overlay/home/working 0 0" >> /etc/fstab
    echo "overlay /tmp overlay x-systemd.requires=/data,defaults,lowerdir=/tmp,upperdir=/data/overlay/tmp/upper,workdir=/data/overlay/tmp/working 0 0" >> /etc/fstab
    echo "Reboot necessary"
    exit 1
}

function install_java_corretto() {
    echo "Installing Amazon Corretto 11..."
    sudo apt install software-properties-common unzip curl
    mkdir -p /usr/share/man/man1
    wget -O - https://apt.corretto.aws/corretto.key | sudo gpg --dearmor -o /usr/share/keyrings/corretto-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/corretto-keyring.gpg] https://apt.corretto.aws stable main" | sudo tee /etc/apt/sources.list.d/corretto.list
    apt-get update
    apt-get upgrade
    apt-get install -y java-11-amazon-corretto-jdk
}

function setup_wifi(){

    echo "Create systemd service to start WiFi at boot..."
    cat <<EOF > /etc/systemd/system/owasysd-bt-wifi.service
[Unit]
Description=WiFi switch on at boot
Before=network-pre.target
Wants=network-pre.target
After=pmsrv.service

[Service]
RestartSec=10
Restart=on-failure
StartLimitBurst=2
ExecStart=/usr/bin/Start_BT_WiFi 1
StandardOutput=journal

[Install]
WantedBy=multi-user.target
EOF
    rm /usr/lib/systemd/system-preset/98-owasys-bt-wifi.preset
    systemctl enable owasysd-bt-wifi.service
    systemctl unmask wpa_supplicant@.service
    systemctl enable wpa_supplicant@mlan0.service
    systemctl disable wpa_supplicant.service
    systemctl mask wpa_supplicant.service

    read -p "Enter SSID: " ssid
    read -p "Enter password: " password

    echo "Configuring WiFi..."
    cat <<EOF > /etc/wpa_supplicant/wpa_supplicant-mlan0.conf
ctrl_interface=/var/run/wpa_supplicant
ctrl_interface_group=root
update_config=1
ap_scan=1

autoscan=periodic:10
disable_scan_offload=1

network={
        ssid="$ssid"
        psk="$password"
}
EOF


    cat <<EOF > /etc/systemd/network/05-mlan0.network
[Match]
Name=mlan0

[Network]
DHCP=yes
IgnoreCarrierLoss=3s

[DHCP]
RouteMetric=1
EOF
    echo "iface default inet dhcp" >> /etc/network/interfaces
    echo "Reboot necessary"
    exit 1
}

function install_greengrass() {
    useradd --system --create-home ggc_user
    groupadd --system ggc_group
    read -p "Enter AWS_ACCESS_KEY_ID: " access_key
    read -p "Enter AWS_Secret_ACCESS_KEY: " secret_key
    read -p "ENTER AWS_SESSION_TOKEN: " session_token
    read -p "ENTER IoT Thing Name: " thing_name
    export AWS_ACCESS_KEY_ID=$access_key
    export AWS_SECRET_ACCESS_KEY=$secret_key
    export AWS_SESSION_TOKEN=$session_token
    curl -s https://d2s8p88vqu9w66.cloudfront.net/releases/greengrass-nucleus-latest.zip > greengrass-nucleus-latest.zip
    unzip greengrass-nucleus-latest.zip -d GreengrassInstaller && rm greengrass-nucleus-latest.zip
    sudo -E java -Droot="/data/greengrass/v2" -Dlog.store=FILE \
        -jar ./GreengrassInstaller/lib/Greengrass.jar \
        --aws-region eu-central-1 \
        --thing-name $thing_name \
        --thing-group-name TrackbeastGroup \
        --thing-policy-name GreengrassV2TrackbeastPolicy \
        --tes-role-name GreengrassV2TrackbeastTokenExchangeRole \
        --tes-role-alias-name GreengrassV2TrackbeastTokenExchangeRoleAccess \
        --component-default-user ggc_user:ggc_group \
        --provision true \
        --setup-system-service true
}

# Parse command line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --remove_presets) remove_presets=true ;;
        --expand_fdisk) expand_fdisk=true ;;
        --emmc_overlay) emmc_overlay=true ;;
        --setup_wifi) setup_wifi=true ;;
        --install_java_corretto) install_java_corretto=true ;;
        --install_greengrass) install_greengrass=true ;;        
        --install_docker) install_docker=true ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

# Execute functions based on parameters

if [ "$install_docker" = true ]; then
    install_docker
fi

if [ "$remove_presets" = true ]; then
    remove_presets
fi

if [ "$expand_fdisk" = true ]; then
    expand_fdisk
fi

if [ "$emmc_overlay" = true ]; then
    emmc_overlay
fi

if [ "$install_java_corretto" = true ]; then
    install_java_corretto
fi

if [ "$setup_wifi" = true ]; then
    setup_wifi
fi

if [ "$install_greengrass" = true ]; then
    install_greengrass
fi
