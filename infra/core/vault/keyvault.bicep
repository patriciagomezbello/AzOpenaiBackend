param name string 
param userAssignedIdentityName string
param virtualNetworkSubnetId string
param location string = resourceGroup().location
param tags object = {}
param purgeProtection bool = true
param deployKey string

@description('Expiration time of the key')
param keyExpiration int = dateTimeToEpoch(dateTimeAdd(utcNow(), 'P1Y'))

@description('Specifies the permissions to keys in the vault. Valid values are: all, encrypt, decrypt, wrapKey, unwrapKey, sign, verify, get, list, create, update, import, delete, backup, restore, recover, and purge.')
param keysPermissions array = [
  'list'
  'unwrapKey'
  'wrapKey'
  'get'
]

resource userAssignedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: userAssignedIdentityName  
  location: location
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-02-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'standard'
      family: 'A'
    }
    tenantId: subscription().tenantId
    accessPolicies: [
      {
        tenantId: subscription().tenantId
        objectId: userAssignedIdentity.properties.principalId
        permissions: {
          keys: keysPermissions
        }
      }
    ]
    enabledForDeployment: true
    enableSoftDelete: true
    enablePurgeProtection: purgeProtection
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'AzureServices'
      virtualNetworkRules: [
        {
          id: virtualNetworkSubnetId
        }
      ]
    }
  }
}

resource kvKey 'Microsoft.KeyVault/vaults/keys@2023-02-01' = if (deployKey == 'true') {
  parent: keyVault
  name: 'storagekey'
  properties: {
    attributes: {
      exportable: true
      enabled: true
      exp: keyExpiration
    }
    keySize: 4096
    kty: 'RSA'
  }
}


output name string = keyVault.name
output keyVaultId string = keyVault.id
output keyVaultURI string = keyVault.properties.vaultUri
output keyVaultKeyName string = kvKey.name
output userAssignedIdentityId string = userAssignedIdentity.id
