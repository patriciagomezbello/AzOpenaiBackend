param name string
param location string
param vnetLocation string
param tags object = {}
param privateDNSZoneId string

param sku object = {
  name: 'standard'
}

param authOptions object = {}

param virtualNetworkSubnetId string

param deployNewResource bool = true

// Use existing resources
resource searchExisting 'Microsoft.Search/searchServices@2024-03-01-preview' existing = if (!deployNewResource) {
  name: name
}

// Create a new resources
resource searchNew 'Microsoft.Search/searchServices@2024-03-01-preview' = if (deployNewResource) {
  name: name
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    authOptions: authOptions
    disableLocalAuth: false
    encryptionWithCmk: {
      enforcement: 'Unspecified'
    }
    hostingMode: 'default'
    networkRuleSet: {
      ipRules: []
    }
    partitionCount: 1
    publicNetworkAccess: 'disabled'
    replicaCount: 1
    semanticSearch: 'standard'
  }
  sku: sku
}

resource privateEndpoint 'Microsoft.Network/privateEndpoints@2023-05-01' = if (deployNewResource) {
  name: 'PE-${name}'
  location: vnetLocation
  properties: {
    subnet: {
      id: virtualNetworkSubnetId
    }
    privateLinkServiceConnections: [
      {
        properties: {
          privateLinkServiceId: searchNew.id
          groupIds: [
            'searchService'
          ]
        }
        name: 'PrivateEndpointSearch'
      }
    ]
  }
}

resource privateEndpointDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2020-04-01' = if (deployNewResource) {
  parent: privateEndpoint
  name: 'peDNSZoneGroup'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'config1'
        properties: {
          privateDnsZoneId: privateDNSZoneId
        }
      }
    ]
  }
}

output id string = deployNewResource ? searchNew.id : searchExisting.id
output endpoint string = 'https://${name}.search.windows.net/'
output name string = deployNewResource ? searchNew.name : searchExisting.name
