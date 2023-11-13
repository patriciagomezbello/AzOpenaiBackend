param applicationInsightsName string
param location string = resourceGroup().location
param tags object = {}
param logAnalyticsId string = ''

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

output applicationInsightsConnectionString string = applicationInsights.properties.ConnectionString
output applicationInsightsInstrumentationKey string = applicationInsights.properties.InstrumentationKey
output applicationInsightsName string = applicationInsights.name
