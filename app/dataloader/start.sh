#!/bin/sh

# Unfortunately, the environment variables cannot be exported by the Makefile
# so we need this script to load the environment variables from the azd environment
# and run the backend server with the loaded environment variables

# Load the environment variables from the azd environment
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

$PYTHON_CMD ./cli.py \
  -wc webloader_config.json \
  -ic indexer_config.json \
  -rc role_config.json
