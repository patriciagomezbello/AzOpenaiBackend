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

if [ "$MULTIPROCESSING" = "true" ]; then
  ./.venv/bin/pip install gunicorn==21.2.0
  ./.venv/bin/python -m gunicorn main:app
else
  ./.venv/bin/python -B -m quart --app main:app run --port 50505 --reload
fi
