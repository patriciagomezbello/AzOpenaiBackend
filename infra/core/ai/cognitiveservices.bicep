param name string
param location string = resourceGroup().location
param tags object = {}

param customSubDomainName string = name
param deployments array = []
param kind string = 'OpenAI'
param publicNetworkAccess string = 'Enabled'
param sku object = {
  name: 'S0'
}

param virtualNetworkSubnetId string
param virtualNetworkSubnetId_AppService string

param embedding_capacity int = 100

param deployNewResource bool = true

// Use existing resource
resource accountExisting 'Microsoft.CognitiveServices/accounts@2023-05-01' existing = if (!deployNewResource) {
  name: name
}

// Create new resource
resource accountNew 'Microsoft.CognitiveServices/accounts@2023-05-01' = if (deployNewResource) {
  name: name
  location: location
  tags: tags
  kind: kind
  properties: {
    customSubDomainName: customSubDomainName
    publicNetworkAccess: publicNetworkAccess
    networkAcls: {
      defaultAction: 'Deny'
      virtualNetworkRules: [
        {
          id: virtualNetworkSubnetId
          ignoreMissingVnetServiceEndpoint: false
        }
        {
          id: virtualNetworkSubnetId_AppService
          ignoreMissingVnetServiceEndpoint: false
        }
      ]
    }
  }
  sku: sku
}

@batchSize(1)
resource deployment 'Microsoft.CognitiveServices/accounts/deployments@2023-05-01' = [
  for deployment in deployments: if (deployNewResource) {
    parent: accountNew
    name: deployment.name
    properties: {
      model: deployment.model
      raiPolicyName: contains(deployment, 'raiPolicyName') ? deployment.raiPolicyName : null
    }
    sku: contains(deployment, 'sku')
      ? deployment.sku
      : {
          name: 'Standard'
          capacity: embedding_capacity
        }
  }
]

output endpoint string = deployNewResource ? accountNew.properties.endpoint : accountExisting.properties.endpoint
output id string = deployNewResource ? accountNew.id : accountExisting.id
output name string = deployNewResource ? accountNew.name : accountExisting.name
