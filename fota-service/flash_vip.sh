#!/bin/sh
# author : Daniel Grauel BEG/EVC1                                                   
# Copyright 2025 (c) All rights by Robert Bosch GmbH. 
# We reserve all rights of disposal such as copying and passing on to third parties.
                                                          
# Script follows here:                                                       
                                                          
# variables:                                                                 

echo "start actual flash"
HOSTNAME='192.168.56.49'
COUNT=3 # Number of ping attempts
TAR_NAME=$1
echo "flashing $TAR_NAME"

# inform CIP about starting FOTA process
mosquitto_pub -t "fota_mode" -m "1"

mosquitto_pub -t fota_control -m '{"state": 1, "text": "flashing $TAR_NAME"}'
# Note: path must be adapted to location at CCU
VRTE_PATH='/data/fota/vrte/*'
WAIT_TIME='20'
mosquitto_pub -t fota_control -m '{"state": -2, "text": "Test connection to VIP with IP $HOSTNAME"}'
echo "0. Test connection to VIP with IP $HOSTNAME"

if ping -c $COUNT $HOSTNAME > /dev/null 2>&1; then                           
  echo "Ping to VIP with IP $HOSTNAME was successful."                                    
  echo "Starting VRTE update process"            
  mosquitto_pub -t fota_control -m '{"state":3, "text": "Ping successfull" }'
else                                                                                      
  echo "ERROR: Ping to VIP with IP $HOSTNAME was failed. --> Abort"
  mosquitto_pub -t fota_control -m '{"state":-3, "text": "Ping failed"}'       
  exit 1                                                                                  
fi 
# after successful download of the tar file to CCU                                  
# CCU Part                                            
                                                                                    
echo "1. stop vrte and rename current vrte implementation"
mosquitto_pub -t fota_control -m '{"state":4, "text":"stop vrte and rename current vrte implementation"}'
sshpass -p 'root' ssh -o StrictHostKeyChecking=no root@192.168.56.49 'systemctl stop startup_vip.service'
sleep 2                                   
mosquitto_pub -t fota_control -m '{"state":5, "text":"moving old VRTE"}'
sshpass -p 'root' ssh -o StrictHostKeyChecking=no root@192.168.56.49 'rm -rf /opt/vrte_old/' 
sshpass -p 'root' ssh -o StrictHostKeyChecking=no root@192.168.56.49 'mv -f /opt/vrte/ /opt/vrte_old/'   
                                                          

echo "2. create vrte directory"
mosquitto_pub -t fota_control -m '{"state":6, "text":"create VRTE directory"}'
sshpass -p 'root' ssh -o StrictHostKeyChecking=no root@192.168.56.49 'mkdir -p /opt/vrte/'
                                                                             

echo "3. untar of the VRTE files"
rm -rf vrte #remove old unpacked vrte-Directory (if any)
mosquitto_pub -t fota_control -m '{"state":7, "text":"untar VRTE files}' 
tar xfz $TAR_NAME

############### set file permission ############## 

echo "4. Copy VRTE files to VIP"
mosquitto_pub -t fota_control -m '{"state":8, "text":"copy VRTE files to VIP"}' 
sshpass -p 'root' scp -o StrictHostKeyChecking=no -r $VRTE_PATH root@192.168.56.49:/opt/vrte/
sleep 2

##### TODO Set permissions after copiing ##############

echo "5. reboot VIP to restart system with new VRTE in which will be started with systemd"
mosquitto_pub -t fota_control -m '{"state":9, "text":"5. reboot VIP to restart system with new VRTE in which will be started with systemd"}'
sshpass -p 'root' ssh -o StrictHostKeyChecking=no root@192.168.56.49 'reboot'                            
 
echo "6. Wait a few seconds"
mosquitto_pub -t fota_control -m '{"state":10, "text":"Wait a few seconds"}'
sleep $WAIT_TIME                                                                          
                                                                             
echo "7. Test connection to VIP with IP $HOSTNAME"                                        
mosquitto_pub -t fota_control -m '{"state":11, "text":"Test connection to VIP with IP $HOSTNAME"}'
if ping -c $COUNT $HOSTNAME > /dev/null 2>&1; then                        
  echo "Ping to VIP with IP $HOSTNAME was successful."
  mosquitto_pub -t fota_control -m '{"state":12, "text":"Ping successfull"}'
  mosquitto_pub -t "fota_mode" -m "2"
  echo "Update done"                                                         
else                                                                                      
  echo "ERROR: Ping to VIP with IP $HOSTNAME was failed. --> Update failed"
  mosquitt_pub -t "fota_mode" -m "3"
  mosquitto_pub -t fota_control -m '{"state":-12,"text":"ERROR: Ping to VIP with IP $HOSTNAME was failed. --> Update failed"}'
  exit 1                                                                                  
fi           

# in any case we trigger a restart of the CIP, else connection won`t work
sleep 5
mosquitto_pub -t 'fota_mode' -m '5'