(function () {
    var header = document.querySelector("[data-header]");
    var toggle = document.querySelector("[data-menu-toggle]");
    var drawer = document.querySelector("[data-drawer]");
    var drawerPanel = document.querySelector("[data-drawer-panel]");
    var closeBtn = document.querySelector("[data-menu-close]");
    var dateEl = document.querySelector("[data-today-date]");
    var previousFocus = null;

    if (dateEl && window.Intl && Intl.DateTimeFormat) {
        dateEl.textContent = new Intl.DateTimeFormat("es-ES", {
            weekday: "long",
            day: "numeric",
            month: "long",
            year: "numeric",
            timeZone: "America/New_York"
        }).format(new Date());
    }

    function openMenu() {
        if (!drawer || !toggle) return;
        previousFocus = document.activeElement;
        drawer.hidden = false;
        toggle.setAttribute("aria-expanded", "true");
        document.body.style.overflow = "hidden";
        window.requestAnimationFrame(function () {
            if (closeBtn) closeBtn.focus();
        });
    }

    function closeMenu() {
        if (!drawer || !toggle) return;
        drawer.hidden = true;
        toggle.setAttribute("aria-expanded", "false");
        document.body.style.overflow = "";
        if (previousFocus && previousFocus.focus) previousFocus.focus();
    }

    if (toggle) toggle.addEventListener("click", openMenu);
    if (closeBtn) closeBtn.addEventListener("click", closeMenu);
    if (drawer) {
        drawer.addEventListener("click", function (event) {
            if (event.target === drawer) closeMenu();
        });
        drawer.querySelectorAll("a").forEach(function (link) {
            link.addEventListener("click", closeMenu);
        });
    }
    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") closeMenu();
        if (event.key === "Tab" && drawer && !drawer.hidden && drawerPanel) {
            var focusable = drawerPanel.querySelectorAll("a[href], button:not([disabled])");
            if (!focusable.length) return;
            var first = focusable[0];
            var last = focusable[focusable.length - 1];
            if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
            }
        }
    });

    if (header) {
        var ticking = false;
        window.addEventListener("scroll", function () {
            if (ticking) return;
            ticking = true;
            window.requestAnimationFrame(function () {
                header.classList.toggle("is-compact", (window.scrollY || 0) > 150);
                ticking = false;
            });
        }, { passive: true });
    }

    var nativeShare = document.querySelector("[data-share-native]");
    var copyLink = document.querySelector("[data-copy-link]");
    var shareStatus = document.querySelector("[data-share-status]");

    function setShareStatus(message) {
        if (!shareStatus) return;
        shareStatus.textContent = message;
        window.setTimeout(function () {
            shareStatus.textContent = "";
        }, 2200);
    }

    if (nativeShare) {
        nativeShare.addEventListener("click", function () {
            var data = {
                title: nativeShare.getAttribute("data-share-title") || document.title,
                url: window.location.href
            };
            if (navigator.share) {
                navigator.share(data).catch(function () {});
            } else if (navigator.clipboard) {
                navigator.clipboard.writeText(data.url).then(function () {
                    setShareStatus("Enlace copiado");
                });
            }
        });
    }

    if (copyLink) {
        copyLink.addEventListener("click", function () {
            if (!navigator.clipboard) return;
            navigator.clipboard.writeText(window.location.href).then(function () {
                setShareStatus("Enlace copiado");
            });
        });
    }

    document.querySelectorAll("img").forEach(function (image) {
        image.addEventListener("error", function () {
            var media = image.closest(".th-media, .th-article-figure");
            if (media) media.classList.add("is-image-missing");
        });
    });
})();
