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

echo 'Running "prepdocs.py"'
python ./scripts/prepdocs.py  \
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
