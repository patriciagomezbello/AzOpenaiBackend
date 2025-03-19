#!/bin/bash

echo "--> AZD variables"
azd env get-values

while IFS='=' read -r key value; do
value=$(echo "$value" | sed 's/^"//' | sed 's/"$//')
export "$key=$value"
done <<EOF
$(azd env get-values)
EOF
if [ $? -ne 0 ]; then
echo "Failed to load environment variables from azd environment"
exit $?
fi

if [ -d "./.venv" ]; then
  PYTHON_CMD="./.venv/bin/python"
else
  PYTHON_CMD="python"
fi

$PYTHON_CMD app/ticket-bot/main.py
