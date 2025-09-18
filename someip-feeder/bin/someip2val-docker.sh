#!/bin/bash

#********************************************************************************
# Copyright (c) 2022 Contributors to the Eclipse Foundation
#
# See the NOTICE file(s) distributed with this work for additional
# information regarding copyright ownership.
#
# This program and the accompanying materials are made available under the
# terms of the Apache License 2.0 which is available at
# http://www.apache.org/licenses/LICENSE-2.0
#
# SPDX-License-Identifier: Apache-2.0
#*******************************************************************************/

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# allow customization of all environment variables from host

if [ -z "$VSOMEIP_CONFIGURATION" ]; then
    if [ -f "$SCRIPT_DIR/config/someip_feeder.json" ]; then
        VSOMEIP_CONFIGURATION="$SCRIPT_DIR/config/someip_feeder.json"
    else
        if [ -f "/src/config/someip_feeder.json" ]; then
            VSOMEIP_CONFIGURATION="/src/config/someip_feeder.json"
        fi
    fi
    export VSOMEIP_CONFIGURATION
fi

if [ -z "$FEEDER_CONFIGURATION" ]; then
    if [ -f "$SCRIPT_DIR/config/feeder_mapping.json" ]; then
        FEEDER_CONFIGURATION="$SCRIPT_DIR/config/feeder_mapping.json"
    fi
    export FEEDER_CONFIGURATION
    echo "SOME/IP Feeder configuration: $FEEDER_CONFIGURATION"
fi

[ -z "$VSOMEIP_APPLICATION_NAME" ] && export VSOMEIP_APPLICATION_NAME="someip_feeder"

if [ -z "$SOMEIP_CLI_UNICAST" ]; then
	SOMEIP_CLI_UNICAST="$(hostname -I | cut -d ' ' -f 1)"
fi
echo "# Using unicast: $SOMEIP_CLI_UNICAST"


# default debug levels
[ -z "$DBF_DEBUG" ] && export DBF_DEBUG=1 ### INFO
[ -z "$SOMEIP_CLI_DEBUG" ] && export SOMEIP_CLI_DEBUG=1 ### INFO

echo

if [ -z "$VSOMEIP_APPLICATION_NAME" ]; then
    echo "WARNING! VSOMEIP_APPLICATION_NAME not set in environment!"
fi

if [ ! -f "$VSOMEIP_CONFIGURATION" ]; then
    echo "WARNING! Can't find VSOMEIP_CONFIGURATION: $VSOMEIP_CONFIGURATION"
else
    echo "****************************"
    echo "SOME/IP config: $VSOMEIP_CONFIGURATION"
    ### Replace unicast address with Hostname -I (1st record)
    if grep -q "unicast" "$VSOMEIP_CONFIGURATION"; then
        echo "### Replacing uinicast: $SOMEIP_CLI_UNICAST in VSOMEIP_CONFIGURATION"
        jq --arg ip "$SOMEIP_CLI_UNICAST" '.unicast=$ip' "$VSOMEIP_CONFIGURATION" > "$VSOMEIP_CONFIGURATION.tmp" && mv "$VSOMEIP_CONFIGURATION.tmp" "$VSOMEIP_CONFIGURATION"
    fi
    ### Sanity checks for application name
    CONFIG_APP=$(jq -r  '.applications[0].name' "$VSOMEIP_CONFIGURATION")
    ROUTING_APP=$(jq -r  '.routing' "$VSOMEIP_CONFIGURATION")
    UNICAST_APP=$(jq -r  '.unicast' "$VSOMEIP_CONFIGURATION")
    echo " json: { app_name: $CONFIG_APP, routinng: $ROUTING_APP, unicast: $UNICAST_APP }"
    echo "****************************"
    echo ""

    echo "****************************"
    echo "SOME/IP Client enrironment"
    echo "****************************"
    env | grep SOMEIP_ | sort -r
    echo "****************************"

    if [ "$CONFIG_APP" != "$VSOMEIP_APPLICATION_NAME" ]; then
        echo "WARNING! $VSOMEIP_CONFIGURATION has application name: $CONFIG_APP, but VSOMEIP_APPLICATION_NAME is: $VSOMEIP_APPLICATION_NAME"
    fi
fi

# if running from install, export LD_LIBRARY_PATH to vsomeip libs.
[ -d "$SCRIPT_DIR/../lib" ] && export LD_LIBRARY_PATH="$SCRIPT_DIR/../lib:$LD_LIBRARY_PATH"

./$VSOMEIP_APPLICATION_NAME
