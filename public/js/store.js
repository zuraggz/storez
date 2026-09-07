/**
 * Progressive enhancement for the server-rendered storefront.
 *
 * Every control here already works without JavaScript — the tabs, filters,
 * search, sort and pager are ordinary links and forms that the server renders.
 * This file upgrades them to in-place swaps, and adds the two things that are
 * genuinely client-side: the hero carousel and the cart.
 */
(function () {
  'use strict';

  var $ = function (selector, scope) {
    return (scope || document).querySelector(selector);
  };
  var $$ = function (selector, scope) {
    return Array.prototype.slice.call((scope || document).querySelectorAll(selector));
  };

  var PLACEHOLDER = '/images/products/placeholder.svg';

  /** "$ 30.00 USD" — the price treatment used everywhere in the design. */
  function formatPrice(value) {
    return '$ ' + Number(value).toFixed(2) + ' USD';
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, function (character) {
      return {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
      }[character];
    });
  }

  // ---------------------------------------------------------------- header
  function initHeader() {
    var header = $('[data-header]');
    if (!header) return;

    var onScroll = function () {
      header.classList.toggle('site-header--scrolled', window.scrollY > 12);
    };

    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });

    var toggle = $('[data-menu-toggle]');
    var menu = $('[data-mobile-nav]');

    if (toggle && menu) {
      toggle.addEventListener('click', function () {
        var open = menu.hidden;
        menu.hidden = !open;
        toggle.setAttribute('aria-expanded', String(open));
        toggle.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
        $('[data-menu-icon="open"]', toggle).hidden = open;
        $('[data-menu-icon="close"]', toggle).hidden = !open;
      });
    }
  }

  // ------------------------------------------------------------------ hero
  function initHero() {
    var hero = $('[data-hero]');
    if (!hero) return;

    var slides = $$('[data-hero-slide]', hero);
    var dots = $$('[data-hero-dot]', hero);
    if (slides.length < 2) return;

    var index = 0;
    var timer = null;
    var INTERVAL = 6000;

    function show(next) {
      index = (next + slides.length) % slides.length;

      slides.forEach(function (slide, position) {
        slide.hidden = position !== index;
      });

      dots.forEach(function (dot, position) {
        dot.setAttribute('aria-current', String(position === index));
      });

      // Replay the entry animation the way remounting used to.
      var active = slides[index];
      active.style.animation = 'none';
      void active.offsetWidth;
      active.style.animation = '';
    }

    function start() {
      stop();
      timer = window.setInterval(function () {
        show(index + 1);
      }, INTERVAL);
    }

    function stop() {
      if (timer) window.clearInterval(timer);
      timer = null;
    }

    $('[data-hero-prev]', hero).addEventListener('click', function () {
      show(index - 1);
      start();
    });

    $('[data-hero-next]', hero).addEventListener('click', function () {
      show(index + 1);
      start();
    });

    dots.forEach(function (dot, position) {
      dot.addEventListener('click', function () {
        show(position);
        start();
      });
    });

    hero.addEventListener('mouseenter', stop);
    hero.addEventListener('mouseleave', start);
    hero.addEventListener('focusin', stop);
    hero.addEventListener('focusout', start);

    start();
  }

  // ------------------------------------------------------------------ cart
  var STORAGE_KEY = 'qlonil.cart.v1';

  function readCart() {
    try {
      var raw = window.localStorage.getItem(STORAGE_KEY);
      var parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
      // Private mode, blocked storage, or corrupt JSON: start empty.
      return [];
    }
  }

  function writeCart(lines) {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(lines));
    } catch (error) {
      // Storage unavailable: the cart still works for this session.
    }
  }

  var cart = {
    lines: readCart(),

    count: function () {
      return this.lines.reduce(function (total, line) {
        return total + line.quantity;
      }, 0);
    },

    subtotal: function () {
      return this.lines.reduce(function (total, line) {
        return total + line.price * line.quantity;
      }, 0);
    },

    add: function (item, quantity) {
      var existing = this.lines.filter(function (line) {
        return line.slug === item.slug;
      })[0];

      if (existing) existing.quantity += quantity;
      else this.lines.push({
        slug: item.slug,
        name: item.name,
        price: item.price,
        imageUrl: item.imageUrl,
        quantity: quantity,
      });

      this.save();
    },

    setQuantity: function (slug, quantity) {
      if (quantity <= 0) return this.remove(slug);

      this.lines.forEach(function (line) {
        if (line.slug === slug) line.quantity = quantity;
      });

      this.save();
    },

    remove: function (slug) {
      this.lines = this.lines.filter(function (line) {
        return line.slug !== slug;
      });
      this.save();
    },

    clear: function () {
      this.lines = [];
      this.save();
    },

    save: function () {
      writeCart(this.lines);
      renderCart();
    },
  };

  function renderCart() {
    var badge = $('[data-cart-count]');
    var opener = $('[data-cart-open]');
    var body = $('[data-cart-body]');
    var foot = $('[data-cart-foot]');
    var count = cart.count();

    if (badge) {
      badge.textContent = String(count);
      badge.hidden = count === 0;
    }

    if (opener) opener.setAttribute('aria-label', 'Cart, ' + count + ' items');
    if (!body || !foot) return;

    if (cart.lines.length === 0) {
      body.innerHTML =
        '<div class="state">' +
        '<p class="state__title">Your cart is empty</p>' +
        '<p>Add something you like and it will show up here.</p>' +
        '<a class="btn" href="/shop" style="margin-top: 20px">Browse the shop</a>' +
        '</div>';
      foot.hidden = true;
      return;
    }

    body.innerHTML = cart.lines
      .map(function (line) {
        var name = escapeHtml(line.name);
        return (
          '<div class="cart-line">' +
          '<img src="' + escapeHtml(line.imageUrl) + '" alt="" loading="lazy" ' +
          'onerror="this.onerror=null;this.src=\'' + PLACEHOLDER + '\'" />' +
          '<div>' +
          '<a href="/product/' + encodeURIComponent(line.slug) + '" class="cart-line__name">' + name + '</a>' +
          '<p class="cart-line__price">' + line.quantity + ' × ' + formatPrice(line.price) + '</p>' +
          '<button type="button" class="cart-line__remove" data-cart-remove="' + escapeHtml(line.slug) + '">Remove</button>' +
          '</div>' +
          '<div class="qty">' +
          '<button type="button" data-cart-decrease="' + escapeHtml(line.slug) + '" aria-label="Decrease quantity of ' + name + '">−</button>' +
          '<span>' + line.quantity + '</span>' +
          '<button type="button" data-cart-increase="' + escapeHtml(line.slug) + '" aria-label="Increase quantity of ' + name + '">+</button>' +
          '</div>' +
          '</div>'
        );
      })
      .join('');

    foot.hidden = false;
    $('[data-cart-subtotal]').textContent = formatPrice(cart.subtotal());
  }

  function initCart() {
    var drawer = $('[data-cart-drawer]');
    var backdrop = $('[data-cart-backdrop]');
    if (!drawer || !backdrop) return;

    function setOpen(open) {
      drawer.hidden = !open;
      backdrop.hidden = !open;
      document.body.style.overflow = open ? 'hidden' : '';
    }

    var opener = $('[data-cart-open]');
    if (opener) opener.addEventListener('click', function () { setOpen(true); });

    $('[data-cart-close]').addEventListener('click', function () { setOpen(false); });
    backdrop.addEventListener('click', function () { setOpen(false); });

    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && !drawer.hidden) setOpen(false);
    });

    $('[data-cart-clear]').addEventListener('click', function () { cart.clear(); });

    drawer.addEventListener('click', function (event) {
      var target = event.target.closest('[data-cart-remove], [data-cart-increase], [data-cart-decrease]');
      if (!target) return;

      var slug = target.getAttribute('data-cart-remove');
      if (slug) return cart.remove(slug);

      slug = target.getAttribute('data-cart-increase') || target.getAttribute('data-cart-decrease');
      var line = cart.lines.filter(function (item) { return item.slug === slug; })[0];
      if (!line) return;

      cart.setQuantity(slug, line.quantity + (target.hasAttribute('data-cart-increase') ? 1 : -1));
    });

    renderCart();

    // ------------------------------------------------- product detail page
    var buy = $('[data-add-to-cart]');
    if (!buy) return;

    var stock = Number(buy.getAttribute('data-stock')) || 0;
    var quantity = 1;
    var value = $('[data-qty-value]', buy);
    var down = $('[data-qty-down]', buy);
    var up = $('[data-qty-up]', buy);

    function renderQuantity() {
      value.textContent = String(quantity);
      down.disabled = quantity <= 1;
      up.disabled = quantity >= stock;
    }

    down.addEventListener('click', function () {
      quantity = Math.max(1, quantity - 1);
      renderQuantity();
    });

    up.addEventListener('click', function () {
      quantity = Math.min(Math.max(stock, 1), quantity + 1);
      renderQuantity();
    });

    $('[data-add]', buy).addEventListener('click', function () {
      cart.add(
        {
          slug: buy.getAttribute('data-slug'),
          name: buy.getAttribute('data-name'),
          price: Number(buy.getAttribute('data-price')),
          imageUrl: buy.getAttribute('data-image'),
        },
        quantity
      );

      var note = $('[data-added]');
      if (note) note.hidden = false;
    });

    renderQuantity();
  }

  // --------------------------------------------------------------- gallery
  function initGallery() {
    var gallery = $('[data-gallery]');
    if (!gallery) return;

    var main = $('.pdp__main-image img', gallery);

    gallery.addEventListener('click', function (event) {
      var thumb = event.target.closest('[data-gallery-thumb]');
      if (!thumb) return;

      main.src = thumb.getAttribute('data-gallery-thumb');

      $$('[data-gallery-thumb]', gallery).forEach(function (other) {
        other.setAttribute('aria-current', String(other === thumb));
      });
    });
  }

  // ------------------------------------------------------------ home tabs
  function initHomeTabs() {
    var panel = $('[data-tab-panel]');
    if (!panel) return;

    document.addEventListener('click', function (event) {
      var tab = event.target.closest('[data-tab]');
      if (!tab || event.metaKey || event.ctrlKey) return;

      event.preventDefault();
      var name = tab.getAttribute('data-tab');

      $$('[data-tab]').forEach(function (other) {
        other.setAttribute('aria-selected', String(other === tab));
      });

      fetch('/partials/home-products?tab=' + encodeURIComponent(name), {
        headers: { 'X-Requested-With': 'fetch' },
      })
        .then(function (response) { return response.text(); })
        .then(function (html) {
          panel.innerHTML = html;
          window.history.replaceState({}, '', '/?tab=' + encodeURIComponent(name));
        })
        .catch(function () {
          window.location.href = tab.getAttribute('href');
        });
    });
  }

  // ------------------------------------------------------------------ shop
  function initShop() {
    var results = $('[data-shop-results]');
    if (!results) return;

    var pending = null;

    function load(url, push) {
      var partial = url.replace(/^\/shop/, '/partials/shop-results');

      results.setAttribute('aria-busy', 'true');

      if (pending) pending.abort();
      pending = new AbortController();

      fetch(partial, { headers: { 'X-Requested-With': 'fetch' }, signal: pending.signal })
        .then(function (response) { return response.text(); })
        .then(function (html) {
          results.innerHTML = html;
          results.removeAttribute('aria-busy');
          if (push) window.history.pushState({ shop: url }, '', url);
        })
        .catch(function (error) {
          if (error.name === 'AbortError') return;
          window.location.href = url;
        });
    }

    function markActiveFilters(url) {
      var params = new URLSearchParams(url.split('?')[1] || '');
      var category = params.get('category') || 'all';

      $$('.filters__item').forEach(function (link) {
        var linkCategory =
          new URLSearchParams((link.getAttribute('href') || '').split('?')[1] || '').get('category') || 'all';
        link.setAttribute('aria-pressed', String(linkCategory === category));
      });
    }

    // Filter links, pager links and the "clear filters" button.
    document.addEventListener('click', function (event) {
      var link = event.target.closest('a[href^="/shop"]');
      if (!link || event.metaKey || event.ctrlKey || event.shiftKey) return;
      if (link.getAttribute('aria-disabled') === 'true') {
        event.preventDefault();
        return;
      }
      if (!link.closest('.filters, [data-shop-results]')) return;

      event.preventDefault();
      var url = link.getAttribute('href');
      load(url, true);
      markActiveFilters(url);
      refreshHiddenInputs(url);

      if (link.closest('[data-pagination]')) window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    // The sort <select> and the "on sale" checkbox submit their own form.
    document.addEventListener('change', function (event) {
      var form = event.target.closest('form[data-auto-submit]');
      if (!form) return;

      event.preventDefault();
      var url = '/shop?' + new URLSearchParams(new FormData(form)).toString();
      load(url, true);
      refreshHiddenInputs(url);
    });

    // Debounced search: the box stays instant, the URL settles behind it.
    var search = $('[data-shop-search] input');
    if (search) {
      var timer = null;

      $('[data-shop-search]').addEventListener('submit', function (event) {
        event.preventDefault();
      });

      search.addEventListener('input', function () {
        window.clearTimeout(timer);
        timer = window.setTimeout(function () {
          var params = new URLSearchParams(window.location.search);

          if (search.value.trim()) params.set('search', search.value.trim());
          else params.delete('search');
          params.delete('page');

          var query = params.toString();
          var url = '/shop' + (query ? '?' + query : '');
          load(url, true);
          refreshHiddenInputs(url);
        }, 350);
      });
    }

    /** Keep the sort/offer forms carrying the filters that are now in the URL. */
    function refreshHiddenInputs(url) {
      var params = new URLSearchParams(url.split('?')[1] || '');

      $$('form[data-auto-submit]').forEach(function (form) {
        $$('input[type="hidden"]', form).forEach(function (input) {
          input.remove();
        });

        ['search', 'category', 'sort', 'onSale'].forEach(function (key) {
          if (form.elements[key] && form.elements[key].type !== 'hidden') return;
          var value = params.get(key);
          if (!value) return;

          var input = document.createElement('input');
          input.type = 'hidden';
          input.name = key;
          input.value = value;
          form.appendChild(input);
        });
      });
    }

    window.addEventListener('popstate', function () {
      load(window.location.pathname + window.location.search, false);
      markActiveFilters(window.location.pathname + window.location.search);
    });
  }

  // ------------------------------------------------------------ newsletter
  function initNewsletter() {
    var form = $('[data-newsletter]');
    if (!form) return;

    var note = $('[data-newsletter-note]');

    form.addEventListener('submit', function (event) {
      event.preventDefault();

      var email = form.elements.email.value.trim();
      var button = form.querySelector('button');
      button.disabled = true;

      fetch('/api/newsletter', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email }),
      })
        .then(function (response) {
          return response.json().then(function (body) {
            return { ok: response.ok, body: body };
          });
        })
        .then(function (result) {
          if (result.ok) {
            note.textContent = result.body.message;
            note.className = 'form-note form-note--ok';
            form.reset();
          } else {
            var errors = result.body.errors || {};
            note.textContent =
              (errors.email && errors.email[0]) ||
              result.body.title ||
              'Could not subscribe right now.';
            note.className = 'form-note form-note--error';
          }
          note.hidden = false;
        })
        .catch(function () {
          note.textContent = 'Could not subscribe right now.';
          note.className = 'form-note form-note--error';
          note.hidden = false;
        })
        .finally(function () {
          button.disabled = false;
        });
    });
  }

  // --------------------------------------------------------------- contact
  function initContactForm() {
    var form = $('[data-contact-form]');
    if (!form) return;

    var RULES = [
      {
        field: 'name',
        test: function (value) { return value.trim().length > 0; },
        message: 'Please tell us your name.',
      },
      {
        field: 'email',
        test: function (value) { return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value.trim()); },
        message: 'That does not look like a valid email address.',
      },
      {
        field: 'message',
        test: function (value) { return value.trim().length >= 10; },
        message: 'Messages need to be at least 10 characters.',
      },
    ];

    function showError(field, message) {
      var slot = form.querySelector('[data-error-for="' + field + '"]');
      var input = form.elements[field];

      if (slot) {
        slot.textContent = message || '';
        slot.hidden = !message;
      }

      if (input) {
        if (message) input.setAttribute('aria-invalid', 'true');
        else input.removeAttribute('aria-invalid');
      }
    }

    form.addEventListener('input', function (event) {
      if (event.target.name) showError(event.target.name, '');
    });

    // The same rules the server applies, checked first so the page does not
    // have to round-trip to say "that email is missing an @".
    form.addEventListener('submit', function (event) {
      var failed = false;

      RULES.forEach(function (rule) {
        var input = form.elements[rule.field];
        var valid = rule.test(input ? input.value : '');
        showError(rule.field, valid ? '' : rule.message);
        if (!valid) failed = true;
      });

      if (failed) event.preventDefault();
    });
  }

  function init() {
    initHeader();
    initHero();
    initCart();
    initGallery();
    initHomeTabs();
    initShop();
    initNewsletter();
    initContactForm();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
