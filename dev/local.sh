#!/bin/bash

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


cd ../../../