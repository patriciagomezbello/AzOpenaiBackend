#!/bin/bash

# Clone the git repository

CI_JOB_TOKEN=123123
REPO_URL=https://gitlab.devops.telekom.de/test/test1

transformed_url=$(echo "$REPO_URL" | sed "s/https:\/\/gitlab.devops.telekom.de/https:\/\/gitlab-ci-token:${CI_JOB_TOKEN}@gitlab.devops.telekom.de/")

git clone $transformed_url data_repo
# Move into the cloned repository
ls

# cd data_repo 

# ls

# # Copy the 'data' and 'data2convert' folders to the parent directory
# cp -R data ..
# cp -R data2convert ..

# cd ..

# ls

# # Remove the cloned repository
# rm -rf data_repo

# ls