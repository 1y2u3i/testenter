#!/bin/sh

echo "Starting services..."
# Loop through matching files
for file in ../config/*_someip_feeder.json; do
    # Extract filename
    filename=$(basename "$file")
    
    # Use cut or pattern matching to get the dynamic prefix (aa)
    app="${filename%%_*}"  # everything before first underscore

    export VSOMEIP_CONFIGURATION="../config/${app}_someip_feeder.json"
    export FEEDER_CONFIGURATION="../config/${app}_feeder_mapping.json"
    export VSOMEIP_APPLICATION_NAME="someip_${app}_feeder"

    ./someip-exe &
    sleep 1
done
tail -f /dev/null  # Keeps the container running