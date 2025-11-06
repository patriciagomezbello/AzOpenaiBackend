#!/bin/bash
set -eo pipefail

# extract ENV_NAME from Environment (.env)
line=$(grep "AZURE_ENV_NAME=" "$ENVIRONMENT")

# Extract the value using cut
envName=$(echo "$line" | cut -d "=" -f 2)
envName="${envName%\"}"
envName="${envName#\"}"

# Create a folder named .azure
mkdir .azure

# Navigate inside the .azure folder
cd .azure

# Create a folder using the value of the GitLab CI variable $AZURE_ENV_NAME
mkdir $envName

# Create a config.json file inside the .azure folder

echo '{"version":1,"defaultEnvironment":"'"$envName"'"}' >config.json

# Replace $AZURE_ENV_NAME with the actual value of the GitLab CI variable $AZURE_ENV_NAME
sed -i 's/$AZURE_ENV_NAME/'"$envName"'/g' config.json

# Navigate into the $AZURE_ENV_NAME folder
cd $envName

# Create a config.json file inside the $AZURE_ENV_NAME folder
echo '{"infra":{"parameters":{"openAiResourceGroupLocation": "'"$OpenAILocation"'"}}}' >config.json

# Replace $AZURE_ENV_NAME with the actual value of the GitLab CI variable $AZURE_ENV_NAME
sed -i 's/$OpenAILocation/'"$OpenAILocation"'/g' config.json

# Copy .env to environment
cp $ENVIRONMENT .env

# navigate back
cd ../../

while IFS='=' read -r key value; do
  value=$(echo "$value" | sed 's/^"//' | sed 's/"$//')
  export "$key=$value"
done <<EOF
$(azd env get-values)
EOF

azd env get-values

if [ "$DEV_ENV" != "true" ] && [ "$AZURE_KEY_DEPLOY" != "false" ] && [ -n "$AZURE_KEYVAULT_NAME" ]; then
  azd env set AZURE_DEPLOY_KEY false
fi

# Copy context.py to core
cp $CONTEXT app/backend/core/context.py

# Copy Abbrevations
if [ -n "${ABBREV}" ]; then
  cp $ABBREV app/backend/core/abbrev.csv
fi

if [ -f "resources/abbrev.csv" ]; then
  echo "File resources/abbrev exists."
  if [ -n "${ABBREV}" ]; then
    echo "Both resources/abbrev.csv and ABBREV variable are set. Using resources/abbrev.csv file. Please migrate ABBREV variable to resources/abbrev.csv file and unset ABBREV variable."
  fi
  cp resources/abbrev.csv app/backend/core/abbrev.csv
fi

#navigate there
cd app/backend/core

csv_file="abbrev.csv"
python_file="abbrev.py"

# Check if the python file exists, if it does, remove it
if [ -f $python_file ]; then
  rm $python_file
fi

# Check if the csv file exists
if [ ! -f $csv_file ]; then
  echo "CSV file does not exist."
  echo "abbreviations = {}" >>$python_file
else
  # Begin writing to Python file
  echo "abbreviations = {" >>$python_file

  # Iterate through the CSV, skipping empty lines
  while IFS=, read -r abbreviation meaning || [ -n "$abbreviation" ]; do
    # Skip lines where the abbreviation or meaning are empty
    if [ -z "$abbreviation" ] || [ -z "$meaning" ]; then
      continue
    fi

    # Write to the Python file
    echo "    \"$abbreviation\": \"$meaning\"," >>$python_file
  done <$csv_file

  # Finish writing to Python file
  echo "}" >>$python_file
fi

echo "Abbreviations dictionary exported to '$python_file'"

if [[ -f "$csv_file" ]]; then
  rm "$csv_file"
  echo "File '$csv_file' has been removed."
else
  echo "File '$csv_file' does not exist."
fi
