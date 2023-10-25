param vnetName string

param subnetDefaultName string
param subnetAppServiceName string
param subnetDefaultAddressPrefix string
param subnetAppServiceAddressPrefix string


var serviceEndpoints = [
  {
    service: 'Microsoft.CognitiveServices'
  }
  {
    service: 'Microsoft.Storage'
  }
  {
    service: 'Microsoft.KeyVault'
  }
]

var delegations = [
  {
    name: 'webapp'
    properties: {
      serviceName: 'Microsoft.Web/serverFarms'
    }
  }
]

resource vnet 'Microsoft.Network/virtualNetworks@2023-05-01' existing = {
  name: vnetName
}

resource serviceEndpointDefault 'Microsoft.Network/virtualNetworks/subnets@2023-05-01' = {
  name: subnetDefaultName
  parent: vnet
  properties: { 
    addressPrefix: subnetDefaultAddressPrefix
    serviceEndpoints: serviceEndpoints
  }
}

resource serviceEndpointAppService 'Microsoft.Network/virtualNetworks/subnets@2023-05-01' = {
  name: subnetAppServiceName
  parent: vnet
  dependsOn: [
    serviceEndpointDefault
  ]
  properties: { 
    addressPrefix: subnetAppServiceAddressPrefix
    serviceEndpoints: serviceEndpoints
    delegations: delegations
  }
}
