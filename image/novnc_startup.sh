#!/bin/bash
echo "starting noVNC with websockify"

# Start websockify as the WebSocket proxy
websockify \
    --web /opt/noVNC \
    6080 \
    localhost:5900 \
    > /tmp/websockify.log 2>&1 &

# Wait for websockify to start
timeout=10
while [ $timeout -gt 0 ]; do
    if netstat -tuln | grep -q ":6080 "; then
        break
    fi
    sleep 1
    ((timeout--))
done

if [ $timeout -eq 0 ]; then
    echo "websockify failed to start, log output:" >&2
    cat /tmp/websockify.log >&2
    exit 1
fi

echo "websockify started successfully"