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

  initCounters(form);
  render();
}

document.addEventListener("DOMContentLoaded", () => {
  autoHideMessages();
  initPollForm();
});
