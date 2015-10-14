/**
 * Controller for the Add Contributor modal.
 */
'use strict';

var $ = require('jquery');
var ko = require('knockout');
var bootbox = require('bootbox');
var Raven = require('raven-js');

var oop = require('./oop');
var $osf = require('./osfHelpers');
var Paginator = require('./paginator');
var osfHelpers = require('js/osfHelpers');

var ProjectSettings = require('js/projectSettings.js');

var ctx = window.contextVars;

var NODE_OFFSET = 25;

var MESSAGES = {
    makeProjectPublicWarning: 'Please review your project for sensitive or restricted information before making it public.  ' +
                        'Once a project is made public, you should assume it will always be public. You can ' +
                        'return it to private later, but search engines or others may access files before you do so.  ' +
                        'Are you sure you would like to continue?',

    makeProjectPrivateWarning: 'Making a project private will prevent users from viewing it on this site, ' +
                        'but will have no impact on external sites, including Google\'s cache. ' +
                        'Would you like to continue?',

    makeComponentPublicWarning: '<p>Please review your component for sensitive or restricted information before making it public.</p>' +
                        'Once a component is made public, you should assume it will always be public. You can ' +
                        'return it to private later, but search engines or others may access files before you do so.  ' +
                        'Are you sure you would like to continue?',

    makeComponentPrivateWarning: 'Making a component private will prevent users from viewing it on this site, ' +
                        'but will have no impact on external sites, including Google\'s cache. ' +
                        'Would you like to continue?',

    makeRegistrationPublicWarning: 'Once a registration is made public, you will not be able to make the ' +
                        'registration private again.  After making the registration public, if you '  +
                        'discover material in it that should have remained private, your only option ' +
                        'will be to retract the registration.  This will eliminate the registration, ' +
                        'leaving only basic information of the project title, description, and '  +
                        'contributors with a notice of retraction.',
    addonWarning: 'The following addons will be effected by this change.  Are you sure you want to continue?'
};

// Initialize treebeard grid for notifications
var ProjectNotifications = require('js/nodePrivacySettingsTreebeard.js');
var $notificationsMsg = $('#configureNotificationsMessage');
var notificationsURL = ctx.node.urls.api  + 'subscriptions/';
// Need check because notifications settings don't exist on registration's settings page
if ($('#grid').length) {
    $.ajax({
        url: notificationsURL,
        type: 'GET',
        dataType: 'json'
    }).done(function(response) {
        new ProjectNotifications(response);
    }).fail(function(xhr, status, error) {
        $notificationsMsg.addClass('text-danger');
        $notificationsMsg.text('Could not retrieve notification settings.');
        Raven.captureMessage('Could not GET notification settings.', {
            url: notificationsURL, status: status, error: error
        });
    });
}



var NodesPublicViewModel = function() {
    var self = this;
    self.page = ko.observable('warning');
    self.pageTitle = ko.computed(function() {
        return {
            warning: 'Warning',
            select: 'Change Privacy Settings',
            addon: 'Addons Effected'
        }[self.page()];
    });
    self.message = ko.computed(function() {
        return {
            warning: MESSAGES.makeProjectPublicWarning,
            select: '',
            addon: MESSAGES.addonWarning
        }[self.page()];
    });
    self.message = ko.observable(MESSAGES.makeProjectPublicWarning);

    self.selectProjects =  function() {
        this.page('select');
    };

    self.addonWarning =  function() {
        this.page('addon');
    };

    self.confirmChanges =  function() {
         this.page('warning');
    };

    self.clear = function() {
         this.page('warning');
    };

};

function NodesPublic (selector, data, options) {
    var self = this;
    self.selector = selector;
    self.$element = $(self.selector);
    self.data = data;
    self.viewModel = new NodesPublicViewModel(self.data);
    self.init();
}

NodesPublic.prototype.init = function() {
    var self = this;
    osfHelpers.applyBindings(self.viewModel, this.selector);
};

module.exports = {
    _ProjectViewModel: NodesPublicViewModel,
    NodesPublic: NodesPublic
};
