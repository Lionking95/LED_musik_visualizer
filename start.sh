#!/bin/bash
cd "$(dirname "$0")" || exit 1

echo "Starte LED Musikvisualisierung..."
echo "Hinweis: GPIO braucht sudo, Audio kommt aus der User-Session."

USER_ID="$(id -u)"
export XDG_RUNTIME_DIR="/run/user/$USER_ID"
export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$USER_ID/bus"

sudo --preserve-env=XDG_RUNTIME_DIR,DBUS_SESSION_BUS_ADDRESS,HOME,PATH \
    env "XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR" \
        "DBUS_SESSION_BUS_ADDRESS=$DBUS_SESSION_BUS_ADDRESS" \
        "PATH=$PATH" \
    python3 main.py