param virtualNetworkId string
param isCn bool = false

resource privateDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.search.windows.net'
  location: 'global'
}

resource pDNSLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' =
  if (isCn) {
    name: 'vnet-link'
    location: 'global'
    parent: privateDnsZone
    properties: {
      registrationEnabled: false
      virtualNetwork: {
        id: virtualNetworkId
      }
    }
  }

output privateDNSZoneId string = privateDnsZone.id
