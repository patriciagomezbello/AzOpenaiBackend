#!/bin/bash

# Define variables
CI_VARIABLE_NAME="ENVIRONMENT"

# Get new value using "azd env get-values" command
value=$(azd env get-values)
# Get new 
env=$(<"$ENVIRONMENT")

escape_quotes() {
    local input="$1"
    local result="${input//\"/\\\"}"     # Replace " with \"
    result="${result//$'\n'/\\\n}"       # Replace line breaks with \n
    echo "$result"
}

# Check if new value is different from current value
if [[ "$value" != "$env" ]]; then

  escaped=$(escape_quotes "$value")
  # Create a JSON payload with the variable value
  JSON_PAYLOAD="{\"value\": \"$escaped\"}"

  # Make a POST request to update the variable
  curl --request PUT --header "PRIVATE-TOKEN: $ACCESS_TOKEN" \
    --header "Content-Type: application/json" \
    --data "$JSON_PAYLOAD" \
    "https://gitlab.devops.telekom.de/api/v4/projects/$CI_PROJECT_ID/variables/$CI_VARIABLE_NAME"

  echo "CI/CD variable '$CI_VARIABLE_NAME' has been updated with the new value"
else
  echo "CI/CD variable '$CI_VARIABLE_NAME' is already up to date"
fi

# write out artifact
echo "$value" > .ENVIRONMENT