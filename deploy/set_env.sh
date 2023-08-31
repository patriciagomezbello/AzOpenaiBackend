#!/bin/bash

# Define variables
# GITLAB_TOKEN="<your_gitlab_api_token>"
# GITLAB_PROJECT_ID="<your_gitlab_project_id>"
CI_VARIABLE_NAME="ENVIRONMENT"

echo $ENVIRONMENT
cat $ENVIRONMENT

# # Get current value of the CI/CD variable
# current_value=$(curl -s --header "PRIVATE-TOKEN: $GITLAB_TOKEN" \
#   "https://gitlab.example.com/api/v4/projects/$GITLAB_PROJECT_ID/variables/$CI_VARIABLE_NAME" | \
#   jq -r '.value')

# # Get new value using "azd env get-values" command
# new_value=$(azd env get-values)

# # Check if new value is different from current value
# if [[ "$new_value" != "$current_value" ]]; then
#   # Create a JSON payload with the variable value
#   JSON_PAYLOAD="{\"value\": \"$new_value\"}"

#   # Make a POST request to update the variable
#   curl --request POST --header "PRIVATE-TOKEN: $GITLAB_TOKEN" \
#     --header "Content-Type: application/json" \
#     --data "$JSON_PAYLOAD" \
#     "https://gitlab.example.com/api/v4/projects/$GITLAB_PROJECT_ID/variables/$CI_VARIABLE_NAME"

#   echo "CI/CD variable '$CI_VARIABLE_NAME' has been updated with the new value: $new_value"
# else
#   echo "CI/CD variable '$CI_VARIABLE_NAME' is already up to date with the value: $current_value"
# fi
