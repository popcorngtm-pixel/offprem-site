// OffPrem — live ticker loader
// Fetches data/ticker.json (rebuilt weekly by scripts/fetch_roundup.py) and
// populates the scrolling wire at the top of every page. Every headline
// links back to its original publisher. If the fetch fails for any reason,
// the static fallback headlines already in the HTML stay put.
(function () {
  var track = document.getElementById("tickerTrack");
  if (!track) return;

  fetch("data/ticker.json", { cache: "no-store" })
    .then(function (res) {
      if (!res.ok) throw new Error("ticker fetch failed: " + res.status);
      return res.json();
    })
    .then(function (data) {
      var items = data && data.items ? data.items : [];
      if (!items.length) return; // keep static fallback

      var html = items
        .map(function (item) {
          var safeTitle = escapeHtml(item.title);
          var safeSource = escapeHtml(item.source || "");
          return (
            '<span><a href="' +
            item.link +
            '" target="_blank" rel="noopener">' +
            safeTitle +
            (safeSource ? " — " + safeSource : "") +
            "</a></span>"
          );
        })
        .join("");

      // duplicate once so the CSS keyframe (-50%) loops seamlessly
      track.innerHTML = html + html;
    })
    .catch(function () {
      // silent — static fallback markup already in the page stays visible
    });

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
})();
