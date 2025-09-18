#!/bin/bash
#Get the location of the script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Script Location : $SCRIPT_DIR"

#clear the any previous log
rm -rf $SCRIPT_DIR/../log
mkdir -p $SCRIPT_DIR/../log

# if running from install, export LD_LIBRARY_PATH to vsomeip libs.
[ -d "$SCRIPT_DIR/../lib" ] && export LD_LIBRARY_PATH="$SCRIPT_DIR/../lib:$LD_LIBRARY_PATH"

echo "Starting services..."
# Loop through matching files
for file in $SCRIPT_DIR/config/*_someip_feeder.json; do
    # Extract filename
    filename=$(basename "$file")
    
    # Use cut or pattern matching to get the dynamic prefix (aa)
    app="${filename%%_*}"  # everything before first underscore

    export VSOMEIP_CONFIGURATION="${SCRIPT_DIR}/config/${app}_someip_feeder.json"
    export FEEDER_CONFIGURATION="${SCRIPT_DIR}/config/${app}_feeder_mapping.json"
    export VSOMEIP_APPLICATION_NAME="someip_${app}_feeder"

    $SCRIPT_DIR/someip_feeder > $SCRIPT_DIR/../log/"${app}".log &
    sleep 1
done