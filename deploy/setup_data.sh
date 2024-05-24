#!/bin/bash

function prepareFiles {
    # Clone the git repository
    transformed_url=$(echo "$REPO_URL" | sed "s/https:\/\/gitlab.devops.telekom.de/https:\/\/gitlab-ci-token:${CI_JOB_TOKEN}@gitlab.devops.telekom.de/")

    echo $transformed_url
    git clone $transformed_url data_repo

    # Move into the cloned repository
    cd data_repo 

    # Copy the 'data' and 'data2convert' folders to the parent directory
    cp -R data ..
    cp -R data2convert ..

    cd ..
}

function prepareLangchain {
    # copy langchain config to scripts folder
    cp $LANGCHAIN_CONFIG langchain_config.json
}

if [ -z "$DATA_MODE" ]; then
    # Variable is empty or does not exist, possible values: "file", "lc", "all"
    echo 'DATA_MODE not set, will be set to "file" (default)'
    export DATA_MODE="file"
fi

if [ -z "$DATA_CONVERT" ]; then
    # Variable is empty or does not exist, possible values: "false", "true"
    echo 'DATA_CONVERT not set, will be set to false (default)'
    export DATA_CONVERT="false"
fi

if [ -z "$FILE_MODE" ]; then
    # Variable is empty or does not exist, possible values: "git", "blob"
    echo 'FILE_MODE not set, will be set to "git" (default)'
    export FILE_MODE="git" 
fi

if [ -z "$LC_MODE" ]; then
    # Variable is empty or does not exist, possible values: "create", "delete"
    echo 'LC_MODE not set, will be set to "create" (default)'
    export LC_MODE="create"
fi

if [ -z "$RESET_INDEX" ]; then
    # Variable is empty or does not exist, possible values: "false", "true"
    echo 'RESET_INDEX not set, will be set to false (default)'
    export RESET_INDEX="false"
fi



if [[ $DATA_MODE == "lc" ]]; then
    prepareLangchain
elif [[ $DATA_MODE == "file" ]]; then
    if [[ $FILE_MODE != "blob" ]]; then
        prepareFiles
    else
        echo "no prep needed, will be handled in Azure"
    fi
elif [[ $DATA_MODE == "all" ]]; then
    if [[ $FILE_MODE != "blob" ]]; then
        prepareFiles
    fi
    prepareLangchain
fi

cp $ROLE_CONFIG role_config.json

./scripts/prepdocs.sh

echo "deleting data ..."

rm langchain_config.json
rm role_config.json

cd ..

# Remove the cloned repository
rm -rf data_repo

rm -rf data
rm -rf data2convert
