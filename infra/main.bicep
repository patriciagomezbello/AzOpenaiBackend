targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the the environment which is used to generate a short unique hash used in all resources.')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
param location string

param authClient string

param appServicePlanName string = ''

@allowed([ 'B1', 'B2', 'B3', 'S1', 'S2', 'S3', 'P0v3', 'P1v3', 'P2v3', 'P3v3' ])
param appServicePlanSku string = 'S1'

param backendServiceName string = ''
param resourceGroupName string = ''

param applicationInsightsName string = ''

param searchServiceName string = ''
param searchServiceResourceGroupName string = ''
param searchServiceResourceGroupLocation string = location

@allowed([ 'basic', 'standard', 'standard2', 'standard3' ])
param searchServiceSkuName string = 'standard'

param searchIndexName string = 'gptkbindex'

param storageAccountName string = ''
param storageResourceGroupName string = ''
param storageResourceGroupLocation string = location
param storageContainerNameDocs string = 'docs'

param openAiServiceName string = ''
param openAiResourceGroupName string = ''
@description('Location for the OpenAI resource group')
@allowed([ 'westeurope', 'francecentral', 'swedencentral', 'polandcentral' ])
@metadata({
  azd: {
    type: 'location'
  }
})
param openAiResourceGroupLocation string

param openAiSkuName string = 'S0'

param formRecognizerServiceName string = ''
param formRecognizerResourceGroupName string = ''
param formRecognizerResourceGroupLocation string = location

param formRecognizerSkuName string = 'S0'

param chatGptDeploymentName string
param chatGptDeploymentCapacity int = 60

@allowed([ 'gpt-35-turbo', 'gpt-35-turbo-16k', 'gpt-35-turbo-instruct', 'gpt-4', 'gpt-4-32k' ])
param chatGptModelName string = 'gpt-35-turbo'

@allowed([ '0613', '0914' ])
param chatGptModelVersion string = '0613'

param embeddingDeploymentName string = 'embedding'
param embeddingDeploymentCapacity int = 120

@allowed([ 'text-embedding-ada-002', ])
param embeddingModelName string = 'text-embedding-ada-002'

@description('Id of the user or app to assign application roles')
param principalId string = ''

@description('Use Application Insights for monitoring and performance tracing')
param useApplicationInsights bool = false

@description('Role that needs to be in auth token for authorisation')
param authRole string

@description('Tenant where the user is authenticated, must be specified if the UI and backend tenants differ')
param authTenant string

@description('Redeploy OpenAI (must be set to false after first deployment)')
param redeployOpenAI bool = true

@description('List of cors allowed addresses for the api')
param allowed_cors string

var allowed_cors_list = split(allowed_cors, ',')

param vnetName string
param subnetName string
param subnetName_AppService string

param vnetResourceGroupName string

param deployKey string = 'true'

var abbrs = loadJsonContent('abbreviations.json')
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))
var tags = { 'azd-env-name': environmentName }

var subscriptionName = subscription().displayName

var isContainsCN = contains(subscriptionName, 'cn')

var resourceGroupLGAWS = isContainsCN ? 'cloud-native-infrastructure' : 'cloud-integrated-infrastructure'

resource logAnalyticWorkspace 'Microsoft.OperationalInsights/workspaces@2021-06-01' existing = {
  name: 'lgaws-${replace(subscriptionName, '_', '-')}'
  scope: resourceGroup(resourceGroupLGAWS)
}

// Organize resources in a resource group
resource mainResourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: !empty(resourceGroupName) ? resourceGroupName : '${abbrs.resourcesResourceGroups}${environmentName}'
  location: location
  tags: tags
}

resource openAiResourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' existing = if (!empty(openAiResourceGroupName)) {
  name: !empty(openAiResourceGroupName) ? openAiResourceGroupName : mainResourceGroup.name
}

resource formRecognizerResourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' existing = if (!empty(formRecognizerResourceGroupName)) {
  name: !empty(formRecognizerResourceGroupName) ? formRecognizerResourceGroupName : mainResourceGroup.name
}

resource searchServiceResourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' existing = if (!empty(searchServiceResourceGroupName)) {
  name: !empty(searchServiceResourceGroupName) ? searchServiceResourceGroupName : mainResourceGroup.name
}

resource storageResourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' existing = if (!empty(storageResourceGroupName)) {
  name: !empty(storageResourceGroupName) ? storageResourceGroupName : mainResourceGroup.name
}

var resourceGroupVNET = resourceGroup(vnetResourceGroupName)

resource vnet 'Microsoft.Network/virtualNetworks@2023-05-01' existing = {
  name: vnetName
  scope: resourceGroupVNET
}

resource subnet_default 'Microsoft.Network/virtualNetworks/subnets@2023-05-01' existing = {
  name: subnetName
  parent: vnet
}

resource subnet_AppService 'Microsoft.Network/virtualNetworks/subnets@2023-05-01' existing = {
  name: subnetName_AppService
  parent: vnet
}

module keyvault 'core/vault/keyvault.bicep' = {
  name: 'keyvault'
  dependsOn: [
    serviceEndpoints
  ]
  scope: mainResourceGroup
  params: {
    name: '${abbrs.keyVaultVaults}${resourceToken}'
    location: location
    virtualNetworkSubnetId: subnet_default.id
    userAssignedIdentityName: '${abbrs.managedIdentityUserAssignedIdentities}${resourceToken}'
    deployKey: deployKey
  }
}

// service Endpoints required for VNET Integration of services
module serviceEndpoints 'core/subnet/service-endpoints.bicep' = {
  name: 'serviceEndpoints'
  scope: resourceGroupVNET
  dependsOn: [
    subnet_default
    subnet_AppService
  ]
  params: {
    vnetName: vnet.name
    subnetDefaultName: subnet_default.name
    subnetDefaultAddressPrefix: subnet_default.properties.addressPrefix
    subnetAppServiceName: subnet_AppService.name
    subnetAppServiceAddressPrefix: subnet_AppService.properties.addressPrefix
  }
}

// Monitor application with Azure Monitor
module monitoring './core/monitor/monitoring.bicep' = if (useApplicationInsights) {
  name: 'monitoring'
  scope: mainResourceGroup
  dependsOn: [
    serviceEndpoints
  ]
  params: {
    logAnalyticsId: logAnalyticWorkspace.id
    location: location
    tags: tags
    applicationInsightsName: !empty(applicationInsightsName) ? applicationInsightsName : '${abbrs.insightsComponents}${resourceToken}'
  }
}

// Create an App Service Plan to group applications under the same payment plan and SKU
module appServicePlan 'core/host/appserviceplan.bicep' = {
  name: 'appserviceplan'
  scope: mainResourceGroup
  params: {
    name: !empty(appServicePlanName) ? appServicePlanName : '${abbrs.webServerFarms}${resourceToken}'
    location: location
    tags: tags
    sku: {
      name: appServicePlanSku
      capacity: 1
    }
    kind: 'linux'
  }
}

// The application backend
module backend 'core/host/appservice.bicep' = {
  name: 'web'
  scope: mainResourceGroup
  params: {
    name: !empty(backendServiceName) ? backendServiceName : '${abbrs.webSitesAppService}backend-${resourceToken}'
    location: location
    tags: union(tags, { 'azd-service-name': 'backend' })
    appServicePlanId: appServicePlan.outputs.id
    runtimeName: 'python'
    runtimeVersion: '3.11'
    appCommandLine: 'python3 -m gunicorn main:app'
    scmDoBuildDuringDeployment: true
    managedIdentity: true
    clientId: authClient
    tenantId: tenant().tenantId
    authTenant: (!empty(authTenant)) ? authTenant : 'same'
    allowedOrigins: allowed_cors_list
    virtualNetworkSubnetId_AppService: subnet_AppService.id
    appSettings: {
      AZURE_AUTH_ROLE: (!empty(authRole)) ? authRole : 'all'
      AZURE_AUTH_CLIENT: authClient
      AZURE_AUTH_TENANT: (!empty(authTenant)) ? authTenant : 'same'
      AZURE_STORAGE_ACCOUNT: storage.outputs.name
      AZURE_STORAGE_CONTAINER_DOCS: storageContainerNameDocs
      AZURE_OPENAI_SERVICE: openAi.outputs.name
      AZURE_SEARCH_INDEX: searchIndexName
      AZURE_SEARCH_SERVICE: searchService.outputs.name
      AZURE_OPENAI_CHATGPT_DEPLOYMENT: chatGptDeploymentName
      AZURE_OPENAI_CHATGPT_MODEL: chatGptModelName
      AZURE_OPENAI_EMB_DEPLOYMENT: embeddingDeploymentName
      APPLICATIONINSIGHTS_CONNECTION_STRING: useApplicationInsights ? monitoring.outputs.applicationInsightsConnectionString : ''
    }
  }
}

module openAi 'core/ai/cognitiveservices.bicep' = if (redeployOpenAI) {
  name: 'openai'
  scope: openAiResourceGroup
  dependsOn: [
    serviceEndpoints
  ]
  params: {
    name: !empty(openAiServiceName) ? openAiServiceName : '${abbrs.cognitiveServicesAccounts}${resourceToken}'
    location: openAiResourceGroupLocation
    tags: tags
    virtualNetworkSubnetId: subnet_default.id
    virtualNetworkSubnetId_AppService: subnet_AppService.id
    sku: {
      name: openAiSkuName
    }
    deployments: [
      {
        name: chatGptDeploymentName
        model: {
          format: 'OpenAI'
          name: chatGptModelName
          version: chatGptModelVersion
        }
        sku: {
          name: 'Standard'
          capacity: chatGptDeploymentCapacity
        }
      }
      {
        name: embeddingDeploymentName
        model: {
          format: 'OpenAI'
          name: embeddingModelName
          version: '2'
        }
        capacity: embeddingDeploymentCapacity
      }
    ]
  }
}

module formRecognizer 'core/ai/cognitiveservices.bicep' = {
  name: 'formrecognizer'
  scope: formRecognizerResourceGroup
  dependsOn: [
    serviceEndpoints
  ]
  params: {
    name: !empty(formRecognizerServiceName) ? formRecognizerServiceName : '${abbrs.cognitiveServicesFormRecognizer}${resourceToken}'
    kind: 'FormRecognizer'
    location: formRecognizerResourceGroupLocation
    tags: tags
    virtualNetworkSubnetId: subnet_default.id
    virtualNetworkSubnetId_AppService: subnet_AppService.id
    sku: {
      name: formRecognizerSkuName
    }
  }
}

module searchService 'core/search/search-services.bicep' = {
  name: 'search-service'
  scope: searchServiceResourceGroup
  params: {
    name: !empty(searchServiceName) ? searchServiceName : 'gptkb-${resourceToken}'
    location: searchServiceResourceGroupLocation
    tags: tags
    virtualNetworkSubnetId: subnet_default.id
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http401WithBearerChallenge'
      }
    }
    sku: {
      name: searchServiceSkuName
    }
  }
}

module storage 'core/storage/storage-account.bicep' = {
  name: 'storage'
  scope: storageResourceGroup
  dependsOn: [
    serviceEndpoints
    keyvault
  ]
  params: {
    name: !empty(storageAccountName) ? storageAccountName : '${abbrs.storageStorageAccounts}${resourceToken}'
    location: storageResourceGroupLocation
    tags: tags
    publicNetworkAccess: 'Enabled'
    virtualNetworkSubnetId: subnet_default.id
    virtualNetworkSubnetId_AppService: subnet_AppService.id
    keyVaultURI: keyvault.outputs.keyVaultURI
    keyName: keyvault.outputs.keyVaultKeyName
    userAssignedIdentityId: keyvault.outputs.userAssignedIdentityId
    sku: {
      name: 'Standard_ZRS'
    }
    deleteRetentionPolicy: {
      enabled: true
      days: 2
    }
    containers: [
      {
        name: storageContainerNameDocs
        publicAccess: 'None'
      }
    ]
  }
}

// USER ROLES
module openAiRoleUser 'core/security/role.bicep' = {
  scope: openAiResourceGroup
  name: 'openai-role-user'
  params: {
    principalId: principalId
    roleDefinitionId: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
    principalType: 'ServicePrincipal'
  }
}

module formRecognizerRoleUser 'core/security/role.bicep' = {
  scope: formRecognizerResourceGroup
  name: 'formrecognizer-role-user'
  params: {
    principalId: principalId
    roleDefinitionId: 'a97b65f3-24c7-4388-baec-2e87135dc908'
    principalType: 'ServicePrincipal'
  }
}

module storageRoleUser 'core/security/role.bicep' = {
  scope: storageResourceGroup
  name: 'storage-role-user'
  params: {
    principalId: principalId
    roleDefinitionId: '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1'
    principalType: 'ServicePrincipal'
  }
}

module storageContribRoleUser 'core/security/role.bicep' = {
  scope: storageResourceGroup
  name: 'storage-contribrole-user'
  params: {
    principalId: principalId
    roleDefinitionId: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
    principalType: 'ServicePrincipal'
  }
}

module searchRoleUser 'core/security/role.bicep' = {
  scope: searchServiceResourceGroup
  name: 'search-role-user'
  params: {
    principalId: principalId
    roleDefinitionId: '1407120a-92aa-4202-b7e9-c0e197c71c8f'
    principalType: 'ServicePrincipal'
  }
}

module searchContribRoleUser 'core/security/role.bicep' = {
  scope: searchServiceResourceGroup
  name: 'search-contrib-role-user'
  params: {
    principalId: principalId
    roleDefinitionId: '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
    principalType: 'ServicePrincipal'
  }
}

module searchSvcContribRoleUser 'core/security/role.bicep' = {
  scope: searchServiceResourceGroup
  name: 'search-svccontrib-role-user'
  params: {
    principalId: principalId
    roleDefinitionId: '7ca78c08-252a-4471-8644-bb5ff32d4ba0'
    principalType: 'ServicePrincipal'
  }
}

// SYSTEM IDENTITIES
module openAiRoleBackend 'core/security/role.bicep' = {
  scope: openAiResourceGroup
  name: 'openai-role-backend'
  params: {
    principalId: backend.outputs.identityPrincipalId
    roleDefinitionId: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
    principalType: 'ServicePrincipal'
  }
}

module storageRoleBackend 'core/security/role.bicep' = {
  scope: storageResourceGroup
  name: 'storage-role-backend'
  params: {
    principalId: backend.outputs.identityPrincipalId
    roleDefinitionId: '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1'
    principalType: 'ServicePrincipal'
  }
}

module searchRoleBackend 'core/security/role.bicep' = {
  scope: searchServiceResourceGroup
  name: 'search-role-backend'
  params: {
    principalId: backend.outputs.identityPrincipalId
    roleDefinitionId: '1407120a-92aa-4202-b7e9-c0e197c71c8f'
    principalType: 'ServicePrincipal'
  }
}

output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = tenant().tenantId
output AZURE_RESOURCE_GROUP string = mainResourceGroup.name

output AZURE_OPENAI_SERVICE string = openAi.outputs.name
output AZURE_OPENAI_RESOURCE_GROUP string = openAiResourceGroup.name
output AZURE_OPENAI_CHATGPT_DEPLOYMENT string = chatGptDeploymentName
output AZURE_OPENAI_CHATGPT_MODEL string = chatGptModelName
output AZURE_OPENAI_EMB_DEPLOYMENT string = embeddingDeploymentName

output AZURE_FORMRECOGNIZER_SERVICE string = formRecognizer.outputs.name
output AZURE_FORMRECOGNIZER_RESOURCE_GROUP string = formRecognizerResourceGroup.name

output AZURE_SEARCH_INDEX string = searchIndexName
output AZURE_SEARCH_SERVICE string = searchService.outputs.name
output AZURE_SEARCH_SERVICE_RESOURCE_GROUP string = searchServiceResourceGroup.name

output AZURE_STORAGE_ACCOUNT string = storage.outputs.name
output AZURE_STORAGE_CONTAINER_DOCS string = storageContainerNameDocs
output AZURE_STORAGE_RESOURCE_GROUP string = storageResourceGroup.name

output AZURE_KEYVAULT_NAME string = keyvault.outputs.name

output BACKEND_URI string = backend.outputs.uri
