function setCache(key, value) {
  $.ajax({
    url: "/api/v1/cache_set",
    type: "POST",
    data: {"key": key, "value": value},
    success: function(response) {
      window.location.reload();
    },
    error: function(e) {
      alert('Error talking to cache! ' + e);
    }
  });
}

function deleteCache(key) {
  $.ajax({
    url: "/api/v1/cache_set",
    type: "POST",
    data: {"key": key, "value": null, "ttl": "1"},
    success: function(response) {
      window.location.reload();
    },
    error: function(e) {
      alert('Error talking to cache! ' + e);
    }
  });
}
