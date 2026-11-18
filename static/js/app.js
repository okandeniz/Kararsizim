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

document.addEventListener("DOMContentLoaded", () => {
  autoHideMessages();
});
