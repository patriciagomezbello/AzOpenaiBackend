 #!/bin/sh

echo ""
echo "Loading azd .env file from current environment"
echo ""

while IFS='=' read -r key value; do
    value=$(echo "$value" | sed 's/^"//' | sed 's/"$//')
    export "$key=$value"
done <<EOF
$(azd env get-values)
EOF


# default values for variables

if [ -z "$DATA_MODE" ]; then
  # Variable is empty or does not exist, possible values: "file", "lc", "all"
  DATA_MODE="lc"
fi

if [ -z "$DATA_CONVERT" ]; then
  # Variable is empty or does not exist, possible values: "false", "true"
  DATA_CONVERT="false"
fi

if [ -z "$FILE_MODE" ]; then
  # Variable is empty or does not exist, possible values: "git", "blob"
  FILE_MODE="git" 
fi

if [ -z "$LC_MODE" ]; then
  # Variable is empty or does not exist, possible values: "create", "delete" and possibly "update"
  LC_MODE="create"
fi

if [ -z "$RESET_INDEX" ]; then
  # Variable is empty or does not exist, possible values: "false", "true"
  RESET_INDEX="false"
fi

echo 'Creating python virtual environment "scripts/.venv"'
python3 -m venv scripts/.venv

echo 'Installing dependencies from "requirements.txt" into virtual environment'
./scripts/.venv/bin/python -m pip install -r scripts/requirements.txt

echo 'Running "prepdocs.py"'
./scripts/.venv/bin/python ./scripts/prepdocs.py \
--files 'data' \
--files2convert 'data2convert' \
--openaiservice "$AZURE_OPENAI_SERVICE" \
--openaideployment "$AZURE_OPENAI_EMB_DEPLOYMENT" \
--storageaccount "$AZURE_STORAGE_ACCOUNT" \
--containerdocs "$AZURE_STORAGE_CONTAINER_DOCS" \
--searchservice "$AZURE_SEARCH_SERVICE" \
--index "$AZURE_SEARCH_INDEX" \
--formrecognizerservice "$AZURE_FORMRECOGNIZER_SERVICE" \
--tenantid "$AZURE_TENANT_ID" \
--data_mode "$DATA_MODE" \
--data_conversion "$DATA_CONVERT" \
--file_mode "$FILE_MODE" \
--lc_mode "$LC_MODE" \
--reset_index "$RESET_INDEX" \
-v 
