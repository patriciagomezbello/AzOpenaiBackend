param vnetName string

param subnetDefaultName string
param subnetAppServiceName string
param subnetDefaultAddressPrefix string
param subnetAppServiceAddressPrefix string

param hasPrefixes bool

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

var propertiesDefault = (hasPrefixes)
  ? {
      addressPrefixes: [subnetDefaultAddressPrefix]
      serviceEndpoints: serviceEndpoints
    }
  : {
      addressPrefix: subnetDefaultAddressPrefix
      serviceEndpoints: serviceEndpoints
    }

var propertiesAppservice = (hasPrefixes)
  ? {
      addressPrefixes: [subnetAppServiceAddressPrefix]
      serviceEndpoints: serviceEndpoints
      delegations: delegations
    }
  : {
      addressPrefix: subnetAppServiceAddressPrefix
      serviceEndpoints: serviceEndpoints
      delegations: delegations
    }

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
  properties: propertiesDefault
}

resource serviceEndpointAppService 'Microsoft.Network/virtualNetworks/subnets@2023-05-01' = {
  name: subnetAppServiceName
  parent: vnet
  dependsOn: [
    serviceEndpointDefault
  ]
  properties: propertiesAppservice
}
