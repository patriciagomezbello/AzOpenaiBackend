param name string
param location string = resourceGroup().location
param tags object = {}

// Reference Properties
param applicationInsightsName string = ''
param appServicePlanId string
param keyVaultName string = ''
param managedIdentity bool = !empty(keyVaultName)

// MSAL variables
param authTenant string

// API variables
param apiBasePath string

var basePath = !empty(apiBasePath) && apiBasePath != '/' ? '${apiBasePath}' : ''

// OIDC variables
// param authProvider string = 'microsoft' // 'oidc' or 'microsoft'

// Runtime Properties
@allowed([
  'dotnet'
  'dotnetcore'
  'dotnet-isolated'
  'node'
  'python'
  'java'
  'powershell'
  'custom'
])
param runtimeName string
param runtimeNameAndVersion string = '${runtimeName}|${runtimeVersion}'
param runtimeVersion string

param virtualNetworkSubnetId_AppService string

// Documentation
// https://learn.microsoft.com/en-gb/azure/templates/microsoft.web/sites?pivots=deployment-language-bicep

// Microsoft.Web/sites Properties
param kind string = 'app,linux'

// Microsoft.Web/sites/config
param allowedOrigins array
param alwaysOn bool = true
param appCommandLine string = ''
param appSettings object = {}
param clientAffinityEnabled bool = false
param enableOryxBuild bool = contains(kind, 'linux')
param functionAppScaleLimit int = -1
param linuxFxVersion string = runtimeNameAndVersion
param minimumElasticInstanceCount int = -1
param numberOfWorkers int = -1
param scmDoBuildDuringDeployment bool = false
param use32BitWorkerProcess bool = false
param ftpsState string = 'FtpsOnly'
param healthCheckPath string = ''
param clientId string = ''
param tenantId string = ''

#disable-next-line no-hardcoded-env-urls
var commonLogin = 'https://login.microsoftonline.com/common/v2.0'
var tenantLogin = 'https://sts.windows.net/${tenantId}/v2.0'

var excludedRoutes = ['/docs', '/redocs', '/openapi.json', '/openapi.yaml', '/openapi.yml', '/health']
var excludedPaths = [for route in excludedRoutes: '${basePath}${route}']

param ipSecurityRestrictionIp string = ''

var thirdLastChar = !empty(ipSecurityRestrictionIp)
  ? substring(ipSecurityRestrictionIp, length(ipSecurityRestrictionIp) - 3, 1)
  : null
var secondLastChar = !empty(ipSecurityRestrictionIp)
  ? substring(ipSecurityRestrictionIp, length(ipSecurityRestrictionIp) - 2, 1)
  : null
var isSecondLastCharSlash = (secondLastChar == '/')
var isThirdLastCharSlash = (thirdLastChar == '/')

var ip = isThirdLastCharSlash || isSecondLastCharSlash ? ipSecurityRestrictionIp : '${ipSecurityRestrictionIp}/32'

var ipSecurityRestrictions = !empty(ipSecurityRestrictionIp)
  ? [
      {
        ipAddress: ip
        priority: 100
        action: 'Allow'
        tag: 'Default'
        name: 'IP Gateway'
        description: 'Allow IP Gateway'
      }
    ]
  : []

resource appService 'Microsoft.Web/sites@2022-09-01' = {
  name: name
  location: location
  tags: tags
  kind: kind
  properties: {
    serverFarmId: appServicePlanId
    siteConfig: {
      linuxFxVersion: linuxFxVersion
      alwaysOn: alwaysOn
      ftpsState: ftpsState
      appCommandLine: appCommandLine
      numberOfWorkers: numberOfWorkers != -1 ? numberOfWorkers : null
      minimumElasticInstanceCount: minimumElasticInstanceCount != -1 ? minimumElasticInstanceCount : null
      minTlsVersion: '1.2'
      use32BitWorkerProcess: use32BitWorkerProcess
      functionAppScaleLimit: functionAppScaleLimit != -1 ? functionAppScaleLimit : null
      healthCheckPath: healthCheckPath
      cors: {
        allowedOrigins: union(['https://portal.azure.com', 'https://ms.portal.azure.com'], allowedOrigins)
      }
      ipSecurityRestrictions: ipSecurityRestrictions
      ipSecurityRestrictionsDefaultAction: !empty(ipSecurityRestrictions) ? 'Deny' : 'Allow'
    }
    clientAffinityEnabled: clientAffinityEnabled
    httpsOnly: true
    virtualNetworkSubnetId: virtualNetworkSubnetId_AppService
  }

  identity: { type: managedIdentity ? 'SystemAssigned' : 'None' }

  // auth config
  resource authSettings 'config' = {
    name: 'authsettingsV2'
    properties: {
      globalValidation: {
        requireAuthentication: true
        unauthenticatedClientAction: 'Return401'
        excludedPaths: excludedPaths
      }
      identityProviders: {
        azureActiveDirectory: {
          enabled: true
          registration: {
            clientId: clientId
            openIdIssuer: (authTenant == 'same') ? tenantLogin : commonLogin
          }
        }
      }
      login: {
        tokenStore: {
          enabled: true
        }
      }
      platform: {
        enabled: true
      }
    }
  }

  resource configAppSettings 'config' = {
    name: 'appsettings'
    properties: union(
      appSettings,
      {
        SCM_DO_BUILD_DURING_DEPLOYMENT: string(scmDoBuildDuringDeployment)
        ENABLE_ORYX_BUILD: string(enableOryxBuild)
      },
      runtimeName == 'python' ? { PYTHON_ENABLE_GUNICORN_MULTIWORKERS: 'true' } : {},
      !empty(applicationInsightsName)
        ? { APPLICATIONINSIGHTS_CONNECTION_STRING: applicationInsights.properties.ConnectionString }
        : {},
      !empty(keyVaultName) ? { AZURE_KEY_VAULT_ENDPOINT: keyVault.properties.vaultUri } : {}
    )
  }

  resource configLogs 'config' = {
    name: 'logs'
    properties: {
      applicationLogs: { fileSystem: { level: 'Verbose' } }
      detailedErrorMessages: { enabled: true }
      failedRequestsTracing: { enabled: true }
      httpLogs: { fileSystem: { enabled: true, retentionInDays: 1, retentionInMb: 35 } }
    }
    dependsOn: [
      configAppSettings
    ]
  }
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-02-01' existing = if (!(empty(keyVaultName))) {
  name: keyVaultName
}

resource applicationInsights 'Microsoft.Insights/components@2020-02-02' existing = if (!empty(applicationInsightsName)) {
  name: applicationInsightsName
}

output identityPrincipalId string = managedIdentity ? appService.identity.principalId : ''
output name string = appService.name
output uri string = 'https://${appService.properties.defaultHostName}'
