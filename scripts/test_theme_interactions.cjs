const { readFileSync } = require("node:fs");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const source = readFileSync(
  require("node:path").join(__dirname, "../themes/tuhoy/assets/js/main.js"),
  "utf8",
);
async function test() {
  const events = {};
  let focuses = 0;
  const el = () => ({
    hidden: true,
    addEventListener(k, f) {
      this[k] = f;
    },
    setAttribute() {},
    querySelectorAll() {
      return [];
    },
  });
  const toggle = el(),
    drawer = el(),
    share = el(),
    copy = el(),
    status = {};
  share.getAttribute = () => null;
  const map = {
    "[data-menu-toggle]": toggle,
    "[data-drawer]": drawer,
    "[data-share-native]": share,
    "[data-copy-link]": copy,
    "[data-share-status]": status,
  };
  const document = {
    querySelector: (s) => map[s],
    querySelectorAll: () => [],
    activeElement: {
      focus() {
        focuses++;
      },
    },
    body: { style: {} },
    addEventListener: (k, f) => (events[k] = f),
  };
  const navigator = {};
  const window = {
    location: { href: "https://tuhoy.com/a/" },
    requestAnimationFrame: (f) => f(),
    dispatchEvent() {},
    setTimeout() {},
    clearTimeout() {},
  };
  vm.runInNewContext(source, {
    document,
    navigator,
    window,
    CustomEvent: function () {},
  });
  events.keydown({ key: "Escape" });
  assert.equal(focuses, 0);
  toggle.click();
  assert.equal(drawer.hidden, false);
  events.keydown({ key: "Escape" });
  assert.equal(focuses, 1);
  events.keydown({ key: "Escape" });
  assert.equal(focuses, 1);
  copy.click();
  assert.match(status.textContent, /barra/);
  navigator.clipboard = { writeText: () => Promise.resolve() };
  copy.click();
  await new Promise(setImmediate);
  assert.equal(status.textContent, "Enlace copiado");
  navigator.clipboard.writeText = () => Promise.reject(new Error());
  copy.click();
  await new Promise(setImmediate);
  assert.match(status.textContent, /No se pudo copiar/);
  navigator.share = () => Promise.reject({ name: "AbortError" });
  status.textContent = "";
  share.click();
  await new Promise(setImmediate);
  assert.equal(status.textContent, "");
  navigator.share = () => Promise.reject({ name: "NotAllowedError" });
  share.click();
  await new Promise(setImmediate);
  assert.match(status.textContent, /No se pudo compartir/);
  console.log(
    "PASS menu focus, clipboard unavailable/success/failure, share cancellation/failure",
  );
}
test().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
