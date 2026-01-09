self.addEventListener("install", e => {
    e.waitUntil(
        caches.open("pdf-app").then(cache =>
            cache.addAll(["/", "/static/style.css", "/static/app.js"])
        )
    );
});
