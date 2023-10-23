param name string
param location string = resourceGroup().location
param tags object = {}

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

//TODO: check if we need this, throws error but still a connection is there
// resource privateEndpointConnection 'Microsoft.Search/searchServices/privateEndpointConnections@2022-09-01' = {
//   name: 'PECON-${name}'
//   parent: search
//   properties: {
//     privateEndpoint: {
//       id: privateEndpoint.id
//     }
//     privateLinkServiceConnectionState: {
//       status: 'Approved'
//     }
//   }
// }


output id string = search.id
output endpoint string = 'https://${name}.search.windows.net/'
output name string = search.name
