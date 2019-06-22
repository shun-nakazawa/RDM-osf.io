'use strict';

var $ = require('jquery');
var m = require('mithril');
var ko = require('knockout');
var Raven = require('raven-js');
var osfHelpers = require('js/osfHelpers');
var language = require('js/osfLanguage').Addons.iqbrims;

var logPrefix = '[iqbrims] ';


function IQBRIMSWidget() {
  var self = this;
  self.baseUrl = window.contextVars.node.urls.api + 'iqbrims/';
  self.loading = ko.observable(true);
  self.loadFailed = ko.observable(false);
  self.loadCompleted = ko.observable(false);
  self.modeDeposit = ko.observable(false);
  self.modeCheck = ko.observable(false);
  self.modeAdmin = ko.observable(false);
  self.flowableTaskUrl = ko.observable(undefined);
  self.depositHelp = ko.observable(language.depositHelp);
  self.checkHelp = ko.observable(language.checkHelp);
  self.formEntries = ko.observableArray();

  self.isSubmitted = ko.pureComputed(function() {
      return this.modeDeposit() || this.modeCheck();
  }, this);

  self.updateFormEntries = function(status) {
    self.formEntries.removeAll();
    var laboList = status['labo_list'].map(function(labo) {
      return {'id': labo.substring(0, labo.indexOf(':')),
              'text': labo.substring(labo.indexOf(':') + 1)};
    }).filter(function(labo) {
      return labo['id'] == status['labo_id'];
    });
    if (status['labo_id']) {
      self.formEntries.push({'title': language.labo, 'value': laboList[0]['text']});
    }
    if (status['accepted_date']) {
      self.formEntries.push({'title': language.accepted_date, 'value': new Date(status['accepted_date'])});
    }
    if (status['journal_name']) {
      self.formEntries.push({'title': language.journal_name, 'value': status['journal_name']});
    }
    if (status['doi']) {
      self.formEntries.push({'title': language.doi, 'value': status['doi']});
    }
    if (status['publish_date']) {
      self.formEntries.push({'title': language.publish_date, 'value': new Date(status['publish_date'])});
    }
    if (status['volume']) {
      self.formEntries.push({'title': language.volume, 'value': status['volume']});
    }
    if (status['page_number']) {
      self.formEntries.push({'title': language.page_number, 'value': status['page_number']});
    }
    if (status['workflow_overall_state']) {
      self.formEntries.push({'title': language.workflow_overall_state, 'value': status['workflow_overall_state']});
    }
  };

  self.loadConfig = function() {
    var url = self.baseUrl + 'status';
    console.log(logPrefix, 'loading: ', url);

    return $.ajax({
        url: url,
        type: 'GET',
        dataType: 'json'
    }).done(function (data) {
      console.log(logPrefix, 'loaded: ', data);
      var status = data['data']['attributes'];
      self.modeAdmin(status['is_admin']);
      self.flowableTaskUrl(status['task_url']);
      if (status['state'] == 'deposit') {
        self.modeDeposit(true);
        self.modeCheck(false);
        self.updateFormEntries(status);
      } else if (status['state'] == 'check') {
        self.modeDeposit(false);
        self.modeCheck(true);
        self.updateFormEntries(status);
      } else {
        self.modeDeposit(false);
        self.modeCheck(false);
      }
      self.loading(false);
      self.loadCompleted(true);
    }).fail(function(xhr, status, error) {
      self.loading(false);
      self.loadFailed(true);
      Raven.captureMessage('Error while retrieving addon info', {
          extra: {
              url: url,
              status: status,
              error: error
          }
      });
    });
  };

  self.gotoCheckForm = function() {
    window.location.href = './iqbrims#check';
  };

  self.gotoDepositForm = function() {
    window.location.href = './iqbrims#deposit';
  };

  self.clearModal = function() {
    console.log('Clear Modal');
  };

}

var w = new IQBRIMSWidget();
osfHelpers.applyBindings(w, '#iqbrims-content');
w.loadConfig();
