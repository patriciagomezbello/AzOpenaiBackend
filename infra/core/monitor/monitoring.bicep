param applicationInsightsName string
param location string = resourceGroup().location
param tags object = {}
param logAnalyticsId string = ''
param virtualNetworkSubnetId string
param privateLinkScope bool = true

param retentionDays int = 30

//TODO: Check ImmediatePurgeDataOn30Days: bool parameter)
resource applicationInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: applicationInsightsName
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    RetentionInDays: retentionDays
    WorkspaceResourceId: logAnalyticsId
  }
}

resource pls_applicationInsights 'Microsoft.Insights/privateLinkScopes@2021-07-01-preview' = if (privateLinkScope) {
  name: 'pls-${applicationInsightsName}'
  location: 'global'
  dependsOn: [
    applicationInsights
  ]
  tags: tags
  properties: {
    accessModeSettings: {
      ingestionAccessMode: 'PrivateOnly'
      queryAccessMode: 'Open'
    }
  }
}

resource pls_scope 'Microsoft.Insights/privateLinkScopes/scopedResources@2021-07-01-preview' = if (privateLinkScope) {
  name: 'pls-sc-${applicationInsightsName}'
  parent: pls_applicationInsights
  properties: {
    linkedResourceId: applicationInsights.id
  }
}

resource privateEndpoint 'Microsoft.Network/privateEndpoints@2023-05-01' = if (privateLinkScope) {
  name: 'pe-${applicationInsightsName}'
  location: location
  dependsOn: [
    pls_scope
  ]
  properties: {
    subnet: {
      id: virtualNetworkSubnetId
    }
    privateLinkServiceConnections: [
      {
        name: 'pel-${applicationInsightsName}'
        properties: {
          privateLinkServiceId: pls_applicationInsights.id
          groupIds: [
            'azuremonitor'
          ]
        }
      }
    ]
  }
}


output applicationInsightsConnectionString string = applicationInsights.properties.ConnectionString
output applicationInsightsInstrumentationKey string = applicationInsights.properties.InstrumentationKey
output applicationInsightsName  string = applicationInsights.name
