"use strict";

/**
 * kararsızım — tüm etkileşimler bu dosyada.
 * Formlar JS olmadan da çalışır; buradaki kod yalnızca deneyimi iyileştirir.
 */

/** Çerezden değer okur (CSRF token için kullanılır). */
function getCookie(name) {
  const prefix = name + "=";
  for (const part of document.cookie.split(";")) {
    const cookie = part.trim();
    if (cookie.startsWith(prefix)) {
      return decodeURIComponent(cookie.slice(prefix.length));
    }
  }
  return null;
}

/** Django mesajlarını birkaç saniye sonra yumuşakça kaldırır. */
function autoHideMessages() {
  document.querySelectorAll(".message").forEach((el) => {
    setTimeout(() => {
      el.classList.add("message--hide");
      setTimeout(() => el.remove(), 400);
    }, 5000);
  });
}

/** maxlength'i olan [data-counted] alanların yanına "kalan N" sayacı ekler. */
function initCounters(root) {
  root.querySelectorAll("[data-counted]").forEach((input) => {
    const max = Number(input.getAttribute("maxlength"));
    if (!max) return;
    const counter = document.createElement("span");
    counter.className = "counter";
    counter.setAttribute("aria-hidden", "true");
    input.insertAdjacentElement("afterend", counter);

    const update = () => {
      const left = max - input.value.length;
      counter.textContent = "kalan " + left;
      counter.classList.toggle("counter--low", left <= 10);
    };
    input.addEventListener("input", update);
    input._updateCounter = update;
    update();
  });
}

/**
 * Anket oluşturma formu: boş fazla seçenek kutularını gizler, "+ Seçenek ekle" ve × butonlarını açar.
 * HTML'de 5 kutu da bulunur; JS yokken hepsi görünür ve boş olanlar sunucuda yok sayılır.
 */
function initPollForm() {
  const form = document.querySelector("[data-poll-form]");
  if (!form) return;

  const MIN_VISIBLE = 2;
  const rows = Array.from(form.querySelectorAll("[data-option-row]"));
  const addButton = form.querySelector("[data-add-option]");
  const inputOf = (row) => row.querySelector("input");

  let lastFilled = -1;
  rows.forEach((row, index) => {
    if (inputOf(row).value.trim() !== "") lastFilled = index;
  });
  let visible = Math.max(MIN_VISIBLE, lastFilled + 1);

  function render() {
    rows.forEach((row, index) => {
      row.hidden = index >= visible;
      row.querySelector("[data-remove-option]").hidden = visible <= MIN_VISIBLE;
    });
    addButton.hidden = visible >= rows.length;
  }

  function refreshCounters() {
    rows.forEach((row) => inputOf(row)._updateCounter && inputOf(row)._updateCounter());
  }

  addButton.addEventListener("click", () => {
    if (visible >= rows.length) return;
    visible += 1;
    render();
    inputOf(rows[visible - 1]).focus();
  });

  rows.forEach((row, index) => {
    row.querySelector("[data-remove-option]").addEventListener("click", () => {
      if (visible <= MIN_VISIBLE) return;
      // Alttakileri yukarı kaydır; renkler kutunun sırasına bağlı olduğu için sıra bozulmaz.
      for (let i = index; i < visible - 1; i += 1) {
        inputOf(rows[i]).value = inputOf(rows[i + 1]).value;
      }
      inputOf(rows[visible - 1]).value = "";
      visible -= 1;
      render();
      refreshCounters();
      inputOf(rows[Math.min(index, visible - 1)]).focus();
    });
  });

  // Çift tıklamayla aynı anketin iki kez oluşmasını önle. Geri tuşuyla dönülürse buton açılır.
  const submitButton = form.querySelector('button[type="submit"]');
  form.addEventListener("submit", () => {
    submitButton.disabled = true;
  });
  window.addEventListener("pageshow", () => {
    submitButton.disabled = false;
  });

  initCounters(form);
  render();
}

/** Sonuç çubuklarını 0'dan hedef genişliğe doldurur (CSS transition 600ms). */
function animateBars(scope) {
  const bars = scope.querySelectorAll(".result__bar");
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  bars.forEach((bar) => {
    bar.style.width = "0";
  });
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      bars.forEach((bar) => {
        bar.style.width = bar.dataset.width + "%";
      });
    });
  });
}

function showVoteError(body, message) {
  let box = body.querySelector(".vote-error");
  if (!box) {
    box = document.createElement("p");
    box.className = "vote-error";
    box.setAttribute("role", "alert");
    body.prepend(box);
  }
  box.textContent = message;
}

/**
 * Oy formları: sayfa yenilemeden fetch ile oy verir ve sunucudan gelen sonuç parçasını kartın
 * içine koyar. JS yoksa form normal POST ile çalışır (sunucu yönlendirir).
 */
function initVoting() {
  document.addEventListener("submit", async (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || !form.matches("[data-vote-form]")) return;

    const card = form.closest("[data-poll-card]");
    const body = card && card.querySelector("[data-poll-body]");
    if (!body) return; // Beklenmedik yapı: normal form gönderimi devam etsin.
    event.preventDefault();
    const buttons = form.querySelectorAll("button");
    const data = new FormData(form);
    const submitter = event.submitter;
    if (submitter && submitter.name) data.set(submitter.name, submitter.value);

    body.querySelector(".vote-error")?.remove();
    buttons.forEach((button) => {
      button.disabled = true;
    });

    try {
      const response = await fetch(form.action, {
        method: "POST",
        headers: { "X-CSRFToken": getCookie("csrftoken") || "", "X-Requested-With": "fetch" },
        body: data,
        credentials: "same-origin",
      });
      const text = await response.text();

      if (!response.ok) {
        // Sunucu kısa Türkçe düz metin döner; başka bir şey gelirse (ör. CSRF sayfası) genel mesaj.
        const isPlain = (response.headers.get("Content-Type") || "").startsWith("text/plain");
        showVoteError(body, isPlain && text ? text : "Bir şeyler ters gitti, tekrar dene.");
        if (response.status === 409) {
          // Başka sekme/cihazdan zaten oy verilmiş: butonlar kapalı kalsın, sayfa sonuçları göstersin.
          setTimeout(() => window.location.reload(), 1500);
          return;
        }
        buttons.forEach((button) => {
          button.disabled = false;
        });
        return;
      }

      body.innerHTML = text;
      const results = body.querySelector("[data-results]");
      const totalEl = card.querySelector("[data-vote-total]");
      if (results && totalEl) totalEl.textContent = results.dataset.total + " oy";
      animateBars(body);
      // Tıklanan buton DOM'dan kalktı; odağı sonuçlara taşı (ekran okuyucu için).
      if (results) results.focus({ preventScroll: true });
    } catch {
      showVoteError(body, "Bağlantı hatası, tekrar dene.");
      buttons.forEach((button) => {
        button.disabled = false;
      });
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  autoHideMessages();
  initPollForm();
  initVoting();
});
