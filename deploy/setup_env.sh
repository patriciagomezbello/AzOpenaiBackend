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

csv_file="abbrev.csv"
python_file="abbrev.py"

# Check if the python file exists, if it does, remove it
if [ -f $python_file ]; then
    rm $python_file
fi

# Check if the csv file exists
if [ ! -f $csv_file ]; then
    echo "CSV file does not exist."
    echo "abbreviations = {}" >> $python_file
else
    # Begin writing to Python file
    echo "abbreviations = {" >> $python_file

    # Iterate through the CSV, skipping empty lines
    while IFS=, read -r abbreviation meaning || [ -n "$abbreviation" ]; do
        # Skip lines where the abbreviation or meaning are empty
        if [ -z "$abbreviation" ] || [ -z "$meaning" ]; then
            continue
        fi

        # Write to the Python file
        echo "    \"$abbreviation\": \"$meaning\"," >> $python_file
    done < $csv_file

    # Finish writing to Python file
    echo "}" >> $python_file
fi

echo "Abbreviations dictionary exported to $python_file"

cat $python_file

ls

rm abbrev.csv

cd ../../../




