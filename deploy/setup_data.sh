#!/bin/bash
set -euo pipefail

function prepareLocalFiles {
  # Setup git credentials to be able to authenticate with the repository
  REPO_AUTH_URL=$(echo "$REPO_URL" | sed "s/https:\/\/gitlab.devops.telekom.de/https:\/\/gitlab-ci-token:${CI_JOB_TOKEN}@gitlab.devops.telekom.de/")

  # Clone the repository
  echo $REPO_URL
  git clone $REPO_AUTH_URL data_repo

  cd data_repo

  # Copy the data to the dataloader or root directory
  if [[ $DATA_PROCESS == "v2" ]]; then
      echo " USING DATA PROCESS v2 beta"
      cp -R data ../app/dataloader
  else
      echo " USING OLD DATA PROCESS"
      cp -R data ..
      cp -R data2convert ..
  fi

  cd ..
  rm -rf data_repo

}

function prepareWebLoader {
  if [[ $DATA_PROCESS == "v2" ]]; then
      cp $LANGCHAIN_CONFIG ./app/dataloader/webloader_config.json
  else
      cp $LANGCHAIN_CONFIG langchain_config.json
  fi

  
}

if [ -z "$DATA_MODE" ]; then
  # Variable is empty or does not exist, possible values: "file", "lc", "all"
  echo 'DATA_MODE not set, will be set to "file" (default)'
  export DATA_MODE="file"
fi

if [ -z "$DATA_CONVERT" ]; then
  # Variable is empty or does not exist, possible values: "false", "true"
  echo "DATA_CONVERT is deprecated and will take no effect anymore.
    Please convert your data manually before running the pipeline."
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

if [ -z "$TEXT_SPLITTER" ]; then
  # Variable is empty or does not exist, possible values: "standard", "recursive", "dynamic"
  echo 'TEXT_SPLITTER not set, will be set to "standard" (default)'
  export TEXT_SPLITTER="standard"
fi

if [[ $DATA_MODE == "lc" ]]; then
  prepareWebLoader
elif [[ $DATA_MODE == "file" ]]; then
  if [[ $FILE_MODE != "blob" ]]; then
    prepareLocalFiles
  else
    echo "no prep needed, will be handled in Azure"
  fi
elif [[ $DATA_MODE == "all" ]]; then
  if [[ $FILE_MODE != "blob" ]]; then
    prepareLocalFiles
  fi
  prepareWebLoader
fi


if [[ $DATA_PROCESS == "v2" ]]; then
    cp $ROLE_CONFIG ./app/dataloader/role_config.json
    cd app/dataloader
    ./start.sh
    cd ../..
    echo "Cleaning up..."
    rm -rf app/dataloader/webloader_config.json
    rm -rf app/dataloader/role_config.json
    rm -rf app/dataloader/data
else
    cp $ROLE_CONFIG role_config.json
    ./scripts/prepdocs.sh
    echo "Cleaning up..."
    rm -rf langchain_config.json
    rm -rf role_config.json
    rm -rf data
    rm -rf data2convert
fi
