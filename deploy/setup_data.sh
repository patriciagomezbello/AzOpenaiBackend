#!/bin/bash

# Clone the git repository
git clone $REPO_URL data_repo

# Move into the cloned repository
cd data_repo 

# Copy the 'data' and 'data2convert' folders to the parent directory
cp -R data ..
cp -R data2convert ..

cd ..

# Remove the cloned repository
rm -rf data_repo
