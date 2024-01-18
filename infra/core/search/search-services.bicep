param name string
param location string = resourceGroup().location
param tags object = {}
param isNative bool

param sku object = {
  name: 'standard'
}

param authOptions object = {}

param virtualNetworkSubnetId string

resource search 'Microsoft.Search/searchServices@2022-09-01' = {
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
  }
  sku: sku
}

resource privateEndpoint 'Microsoft.Network/privateEndpoints@2023-05-01' = {
  name: 'PE-${name}'
  location: location
  properties: {
    subnet: {
      id: virtualNetworkSubnetId
    }
    privateLinkServiceConnections: [
      {
        properties: {
          privateLinkServiceId: search.id
          groupIds: [
            'searchService'
          ]
        }
        name: 'PrivateEndpointSearch'
      }
    ]
  }
}

//if (isNative) 
resource privateDnsZone 'Microsoft.Network/privateDnsZones@2020-01-01' = {
  name: 'privatelink.search.windows.net'
  location: 'global'
}

resource privateEndpointDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2020-04-01' = {
  parent: privateEndpoint
  name: 'peDNSZoneGroup'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'config1'
        properties: {
          privateDnsZoneId: privateDnsZone.id
        }
      }
    ]
  }
}

output id string = search.id
output endpoint string = 'https://${name}.search.windows.net/'
output name string = search.name
