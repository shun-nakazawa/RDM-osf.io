var AzureBlobStorageUserConfig = require('./azureblobstorageRdmConfig.js').AzureBlobStorageUserConfig;

// Endpoint for AzureBlobStorage user settings
var institutionId = $('#azureblobstorageAddonScope').data('institution-id');
//var url = '/api/v1/settings/azureblobstorage/accounts/';
var url = '/addons/api/v1/settings/azureblobstorage/' + institutionId + '/accounts/';

var azureblobstorageUserConfig = new AzureBlobStorageUserConfig('#azureblobstorageAddonScope', url, institutionId);
