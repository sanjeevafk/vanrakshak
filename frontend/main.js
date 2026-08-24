/**
 * VanRakshak Landing Page — main.js
 * Vanilla JS: count-up stats, mobile menu, entrance logic.
 */

(function () {
  "use strict";

  /* ============================================
     COUNT-UP STATS
     ============================================ */
  function easeOutCubic(t) {
    return 1 - Math.pow(1 - t, 3);
  }

  function animateStat(el) {
    var target = parseFloat(el.dataset.target);
    var suffix = el.dataset.suffix || "";
    var decimals = parseInt(el.dataset.decimals, 10) || 0;
    var valueEl = el.querySelector(".stat-value");
    var duration = 1500 + parseInt(el.dataset.index || 0, 10) * 80;
    var startTime = null;

    function step(timestamp) {
      if (!startTime) startTime = timestamp;
      var elapsed = timestamp - startTime;
      var progress = Math.min(elapsed / duration, 1);
      var eased = easeOutCubic(progress);
      var current = eased * target;
      valueEl.textContent = current.toFixed(decimals) + suffix;
      if (progress < 1) {
        requestAnimationFrame(step);
      }
    }

    requestAnimationFrame(step);
  }

  function initStats() {
    var stats = document.querySelectorAll(".stat");
    if (!stats.length) return;

    // Assign index for stagger
    stats.forEach(function (el, i) {
      el.dataset.index = String(i);
    });

    // Use IntersectionObserver to trigger when visible
    if ("IntersectionObserver" in window) {
      var observer = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (entry.isIntersecting) {
              var statEls = entry.target.querySelectorAll(".stat");
              statEls.forEach(function (el, i) {
                setTimeout(function () {
                  animateStat(el);
                }, 480 + i * 90);
              });
              observer.unobserve(entry.target);
            }
          });
        },
        { threshold: 0.25 }
      );
      var statsContainer = document.querySelector(".stats");
      if (statsContainer) observer.observe(statsContainer);
    } else {
      // Fallback: animate immediately
      stats.forEach(function (el, i) {
        setTimeout(function () {
          animateStat(el);
        }, 480 + i * 90);
      });
    }
  }

  /* ============================================
     MOBILE MENU
     ============================================ */
  function initMobileMenu() {
    var burger = document.querySelector(".burger");
    var overlay = document.querySelector(".overlay");
    var mobileMenu = document.querySelector(".mobile-menu");
    var mobileLinks = document.querySelectorAll(".mobile-link, .mobile-sign-in");

    if (!burger || !overlay || !mobileMenu) return;

    function openMenu() {
      burger.classList.add("open");
      burger.setAttribute("aria-expanded", "true");
      overlay.hidden = false;
      mobileMenu.hidden = false;
      document.body.classList.add("menu-open");
    }

    function closeMenu() {
      burger.classList.remove("open");
      burger.setAttribute("aria-expanded", "false");
      overlay.hidden = true;
      mobileMenu.hidden = true;
      document.body.classList.remove("menu-open");
    }

    function toggleMenu() {
      if (burger.classList.contains("open")) {
        closeMenu();
      } else {
        openMenu();
      }
    }

    burger.addEventListener("click", toggleMenu);

    // Close on overlay click
    overlay.addEventListener("click", closeMenu);

    // Close on link click
    mobileLinks.forEach(function (link) {
      link.addEventListener("click", closeMenu);
    });

    // Close on Escape
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && burger.classList.contains("open")) {
        closeMenu();
      }
    });

    // Close on resize > 720
    window.addEventListener("resize", function () {
      if (window.innerWidth > 720 && burger.classList.contains("open")) {
        closeMenu();
      }
    });
  }

  /* ============================================
     ACTIVE NAV LINK (hash-based)
     ============================================ */
  function initNavHighlight() {
    var navLinks = document.querySelectorAll(".nav-link");
    var mobileLinks = document.querySelectorAll(".mobile-link");

    function setActive(hash) {
      navLinks.forEach(function (link) {
        link.classList.toggle("active", link.getAttribute("href") === hash);
      });
      mobileLinks.forEach(function (link) {
        link.classList.toggle("active", link.getAttribute("href") === hash);
      });
    }

    // Default
    setActive("#home");

    navLinks.forEach(function (link) {
      link.addEventListener("click", function () {
        setActive(this.getAttribute("href"));
      });
    });

    mobileLinks.forEach(function (link) {
      link.addEventListener("click", function () {
        setActive(this.getAttribute("href"));
      });
    });
  }

  /* ============================================
     INIT
     ============================================ */
  document.addEventListener("DOMContentLoaded", function () {
    initStats();
    initMobileMenu();
    initNavHighlight();
  });
})();
