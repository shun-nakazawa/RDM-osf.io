'use strict';
var $ = require('jquery');
var MySkeltonUserConfig = require('./myskeltonRdmConfig.js').MySkeltonUserConfig;

var institutionId = $('#myskeltonAddonScope').data('institution-id');
var url = '/addons/api/v1/settings/myskelton/' + institutionId + '/accounts/';
var myskeltonUserConfig = new MySkeltonUserConfig('#myskeltonAddonScope', url, institutionId);

// 'use strict';
// var ko = require('knockout');
// var $ = require('jquery');
// var OAuthAddonSettingsViewModel = require('../rdmAddonSettings.js').OAuthAddonSettingsViewModel;
// var oop = require('js/oop');
//
// var ViewModel = oop.extend(OAuthAddonSettingsViewModel, {
//     constructor: function(url, institutionId) {
//         this.super.constructor.call(this, 'myskelton', 'My Skelton', institutionId);
//     },
// });
//
// var institutionId = $('#myskeltonAddonScope').data('institution-id');
// var url = '/addons/api/v1/settings/myskelton/' + institutionId + '/accounts/';
//
// var viewModel = new ViewModel(url, institutionId);
// ko.applyBindings(viewModel, $('#myskeltonAddonScope')[0]);
