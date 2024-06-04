param name string
param location string = resourceGroup().location
param tags object = {}

@allowed(['Hot', 'Cool', 'Premium'])
param accessTier string = 'Hot'
param allowBlobPublicAccess bool = false
param allowCrossTenantReplication bool = true
param allowSharedKeyAccess bool = true
param defaultToOAuthAuthentication bool = false
param deleteRetentionPolicy object = {}
@allowed(['AzureDnsZone', 'Standard'])
param dnsEndpointType string = 'Standard'
param kind string = 'StorageV2'
param minimumTlsVersion string = 'TLS1_2'
@allowed(['Enabled', 'Disabled'])
param publicNetworkAccess string = 'Disabled'
param sku object = { name: 'Standard_LRS' }

param containers array = []

// param virtualNetworkSubnetId string
// param virtualNetworkSubnetId_AppService string

// param keyVaultURI string
// param keyName string

// param userAssignedIdentityId string

resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: name
  location: location
  tags: tags
  kind: kind
  sku: sku
  // identity: {
  //   type: 'UserAssigned'
  //   userAssignedIdentities: {
  //     '${userAssignedIdentityId}': {}
  //   }
  // }
  properties: {
    accessTier: accessTier
    allowBlobPublicAccess: allowBlobPublicAccess
    allowCrossTenantReplication: allowCrossTenantReplication
    allowSharedKeyAccess: allowSharedKeyAccess
    defaultToOAuthAuthentication: defaultToOAuthAuthentication
    dnsEndpointType: dnsEndpointType
    minimumTlsVersion: minimumTlsVersion
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Allow'
      // virtualNetworkRules: [
      //   {
      //     id: virtualNetworkSubnetId
      //     action: 'Allow'
      //   }
      //   {
      //     id: virtualNetworkSubnetId_AppService
      //     action: 'Allow'
      //   }
      // ]
    }
    // encryption: {
    //   services: {
    //     blob: {
    //       enabled: true
    //     }
    //     file: {
    //       enabled: true
    //     }
    //   }
    //   identity: {
    //     userAssignedIdentity: userAssignedIdentityId
    //   }
    //   requireInfrastructureEncryption: true
    //   keySource: 'Microsoft.Keyvault'
    //   keyvaultproperties: {
    //     keyname: keyName
    //     keyvaulturi: endsWith(keyVaultURI, '/') ? substring(keyVaultURI, 0, length(keyVaultURI) - 1) : keyVaultURI
    //   }
    // }
    // supportsHttpsTrafficOnly: true
    publicNetworkAccess: publicNetworkAccess
  }

  resource blobServices 'blobServices' = if (!empty(containers)) {
    name: 'default'
    properties: {
      deleteRetentionPolicy: deleteRetentionPolicy
    }
    resource container 'containers' = [
      for container in containers: {
        name: container.name
        properties: {
          publicAccess: contains(container, 'publicAccess') ? container.publicAccess : 'None'
        }
      }
    ]
  }
}

output name string = storage.name
output primaryEndpoints object = storage.properties.primaryEndpoints
