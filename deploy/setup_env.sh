#!/bin/bash

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

# Create a folder using the value of the GitLab CI variable $envName
mkdir $envName

# Create a config.json file inside the .azure folder
echo '{"version":1,"defaultEnvironment":"'"$envName"'"}' > config.json

# Replace $envName with the actual value of the GitLab CI variable $envName
sed -i 's/$envName/'"$envName"'/g' config.json

# Navigate into the $envName folder
cd $envName

# Create a config.json file inside the $envName folder
echo '{"infra":{"parameters":{"openAiResourceGroupLocation": "'"$OpenAILocation"'"}}}'> config.json 

# Replace $envName with the actual value of the GitLab CI variable $envName
sed -i 's/$OpenAILocation/'"$OpenAILocation"'/g' config.json

# Copy .env to environment
cp $ENVIRONMENT .env

# navigate back
cd ../../

# Copy context.py to core
cp $CONTEXT app/backend/core/context.py

# Copy Abbrevations
cp $ABBREV app/backend/core/abbrev.csv

#navigate there
cd app/backend/core

touch abbrev.py

csv_file="abbrev.csv"
python_file="abbrev.py"

echo "abbrev = {" > $python_file

while IFS=, read -r abbreviation full_form
do
    abbreviation=$(echo $abbreviation 
| sed 's/^[[:space:]]*//;s/[[:space:]]*$//')  # Trim whitespace
    full_form=$(echo $full_form | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')  # Trim whitespace
    echo "    '$abbreviation': '$full_form'," >> $python_file
done < $csv_file

echo "}" >> $python_file
echo "Abbreviations dictionary exported to $python_file"

rm abbrev.csv

cd ../../../




