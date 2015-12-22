function getIssues() {
  var url = "/api/v1/running_tests"
  return $.getJSON(url, { });
}

function outstandingIssues() {
  var url = "/api/v1/outstanding_issues"
  return $.getJSON(url, { });
}

function processIssues(issues) {
  var tableData = "";
  for(var x=0;x<issues.results.length;x++) {
    var keyName = issues.results[x].key
    var summary = issues.results[x].summary;
    tableData += "<div class='alert alert-danger' role='alert'><a target='_blank' href='https://jira.twitter.biz/browse/" + keyName + "'>" + keyName +"</a>: " + summary + "</div>";
  }
  return tableData;
}

function runUpdates() {
  $.when(getIssues())
    .done(function (issues) {
      $('#runningTests').empty();
      if(issues.results.length > 0) {
        $('#runningTests').append('<h3>Running Tests</h3>');
        $('#runningTests').append(processIssues(issues));
      }
    }
  );

  $.when(outstandingIssues())
    .done(function (issues) {
      $('#outstandingIssues').empty();
      if(issues.results.length > 0) {
        $('#outstandingIssues').append('<h3>Outstanding Issues</h3>');
        $('#outstandingIssues').append(processIssues(issues));
      }
    }
  );
}
