#!/bin/sh

echo "ready for next flash command"
OUTPUT="$(mosquitto_sub -t 'fota_control_start' -C 1 --quiet)" 
RETURN_CODE=$?

if [ "$RETURN_CODE" = 0 ]; then
  if [ -e "$OUTPUT" ]; then
    echo "got flash command for VIP: $OUTPUT"
    /bin/bash ./flash_vip.sh $OUTPUT
  else 
    echo "File does not exist"
  fi 
fi

sleep 5

/bin/bash ./flash.sh
