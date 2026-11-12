#!/usr/bin/env bash
# stop-stage4.sh
# Teardown Stage 4 microservices stack in Linux/macOS
echo "Stopping Stage 4 microservices stack..."
for file in .pid_*; do
    if [ -f "$file" ]; then
        pid=$(cat "$file")
        echo "Stopping process $pid..."
        kill -9 "$pid" 2>/dev/null
        rm "$file"
    fi
done
echo "Teardown complete."
