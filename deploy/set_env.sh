#!/bin/bash

# Define variables
# CI_VARIABLE_NAME="ENVIRONMENT"

# Get new value using "azd env get-values" command and extract the values from .env
# current_value=$(azd env get-values)
# current_env=$(<"$ENVIRONMENT")

CI_VARIABLE_NAME="test_var"
current_value="test123"
current_env=$(<"$test_var")

echo $current_value
echo $current_env

# Check if new value is different from current value
if [[ "$current_env" != "$current_value" ]]; then
  # Create a JSON payload with the variable value
  JSON_PAYLOAD="{\"value\": \"$current_env\"}"

  # Make a POST request to update the variable
  curl --request PUT --header "PRIVATE-TOKEN: $CI_JOB_TOKEN" \
    --header "Content-Type: application/json" \
    --data "$JSON_PAYLOAD" \
    "https://gitlab.devops.telekom.de/api/v4/projects/$CI_PROJECT_ID/variables/$CI_VARIABLE_NAME"

  echo "CI/CD variable '$CI_VARIABLE_NAME' has been updated with the new value: $new_value"
else
  echo "CI/CD variable '$CI_VARIABLE_NAME' is already up to date with the value: $current_value"
fi
