// Welcome door: once per browser session. The animation itself is CSS (entrance.css).
(() => {
  const root = document.documentElement;
  const door = document.getElementById("door");
  if (!door || !root.classList.contains("door-pending")) return;
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  let done = false;
  // motion.js listens: "opening" starts the hero intro, "entered" restarts smooth scroll
  const signal = (state) => {
    window.mehmaanDoor = state;
    document.dispatchEvent(new Event(`mehmaan:door-${state}`));
  };
  const behind = document.querySelectorAll("body > header, #main, body > footer");
  behind.forEach((el) => { el.inert = true; });

  const finish = () => {
    try { sessionStorage.setItem("mehmaan:entered", "1"); } catch (e) {}
    root.classList.remove("door-pending");
    behind.forEach((el) => { el.inert = false; });
    door.remove();
    document.getElementById("main")?.focus({ preventScroll: true });
    signal("entered");
  };
  const leave = (cls, ms, openingAt) => {
    if (done) return;
    done = true;
    door.classList.add(cls);
    setTimeout(() => signal("opening"), openingAt); // as the doors start to swing (DoorEntrance onOpening)
    setTimeout(finish, ms); // durations match entrance.css
  };
  const open = () => leave("opening", reduce ? 650 : 4400, reduce ? 0 : 1100);
  const skip = () => leave("closing", reduce ? 650 : 420, 0);

  door.querySelectorAll("[data-door-open]").forEach((b) => b.addEventListener("click", open));
  door.querySelector("[data-door-skip]").addEventListener("click", skip);
  door.addEventListener("keydown", (e) => { if (e.key === "Escape") skip(); });
  door.querySelector(".door-cta").focus();
})();
