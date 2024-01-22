resource privateDnsZone 'Microsoft.Network/privateDnsZones@2020-01-01' = {
  name: 'privatelink.search.windows.net'
  location: 'global'
}

output privateDNSZoneId string = privateDnsZone.id
