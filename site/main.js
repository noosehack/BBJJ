// BlawkOps — main.js

(function () {
  'use strict';

  // Mobile nav toggle
  var toggle = document.querySelector('.nav-toggle');
  var links = document.querySelector('.nav-links');

  if (toggle && links) {
    toggle.addEventListener('click', function () {
      links.classList.toggle('open');
    });

    // Close menu on link click
    links.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', function () {
        links.classList.remove('open');
      });
    });
  }

  // Animate stats on scroll
  var observed = false;
  var statsSection = document.querySelector('.stats-strip');

  if (statsSection && 'IntersectionObserver' in window) {
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting && !observed) {
          observed = true;
          animateStats();
        }
      });
    }, { threshold: 0.5 });

    observer.observe(statsSection);
  }

  function animateStats() {
    document.querySelectorAll('.stat-num').forEach(function (el) {
      var text = el.textContent.trim();
      var num = parseInt(text.replace(/,/g, ''), 10);

      if (isNaN(num) || num <= 0) return;

      var duration = 1200;
      var start = performance.now();
      var formatted = text;

      function step(now) {
        var elapsed = now - start;
        var progress = Math.min(elapsed / duration, 1);
        var eased = 1 - Math.pow(1 - progress, 3);
        var current = Math.round(num * eased);

        if (text.includes(',')) {
          el.textContent = current.toLocaleString();
        } else {
          el.textContent = current;
        }

        if (progress < 1) {
          requestAnimationFrame(step);
        } else {
          el.textContent = formatted;
        }
      }

      requestAnimationFrame(step);
    });
  }

  // Subtle fade-in for sections
  if ('IntersectionObserver' in window) {
    var sections = document.querySelectorAll('.section, .stats-strip');
    sections.forEach(function (s) {
      s.style.opacity = '0';
      s.style.transform = 'translateY(20px)';
      s.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
    });

    var sectionObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.style.opacity = '1';
          entry.target.style.transform = 'translateY(0)';
          sectionObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1 });

    sections.forEach(function (s) {
      sectionObserver.observe(s);
    });
  }

  // Active nav link highlighting
  var navLinks = document.querySelectorAll('.nav-links a[href^="#"]');
  var sectionEls = [];

  navLinks.forEach(function (link) {
    var id = link.getAttribute('href').slice(1);
    var el = document.getElementById(id);
    if (el) sectionEls.push({ link: link, el: el });
  });

  if (sectionEls.length > 0) {
    window.addEventListener('scroll', function () {
      var scrollY = window.scrollY + 100;
      var current = null;

      sectionEls.forEach(function (item) {
        if (item.el.offsetTop <= scrollY) {
          current = item;
        }
      });

      navLinks.forEach(function (l) { l.style.color = ''; });
      if (current) {
        current.link.style.color = '#e4e4e8';
      }
    });
  }
})();
