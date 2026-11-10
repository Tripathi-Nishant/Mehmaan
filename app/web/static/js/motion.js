// Lovable motion, ported from design-ref (routes/index.tsx, site/ExperienceCard.tsx, site/SmoothScroll.tsx,
// lib/smooth-scroll.ts) onto GSAP 3.15.1 + ScrollTrigger + Lenis 1.3.27 loaded in base.html.
// Hidden start states are only ever set here: if the CDN fails or motion is reduced, nothing is hidden.
(() => {
  const { gsap, ScrollTrigger, Lenis } = window;
  if (!gsap || !ScrollTrigger || !Lenis) return;
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  gsap.registerPlugin(ScrollTrigger);

  const root = document.documentElement;
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => gsap.utils.toArray(s);
  const ease = "power4.out"; // close to cubic-bezier(0.22, 1, 0.36, 1) used throughout design-ref

  // 1. Lenis smooth scroll driven by the GSAP ticker (SmoothScroll.tsx)
  const lenis = new Lenis({ lerp: 0.1, wheelMultiplier: 0.9, anchors: { offset: -112 } });
  lenis.on("scroll", ScrollTrigger.update);
  gsap.ticker.add((time) => lenis.raf(time * 1000));
  gsap.ticker.lagSmoothing(0);

  // Door state comes from entrance.js: "closed" -> "opening" -> "entered" (lockScroll in smooth-scroll.ts)
  const door = () => window.mehmaanDoor || (root.classList.contains("door-pending") ? "closed" : "entered");
  if (door() !== "entered") {
    lenis.stop();
    document.addEventListener("mehmaan:door-entered", () => lenis.start(), { once: true });
  }

  // 2. Hero text and painting come in once the doors start to swing (index.tsx motion.div / motion.figure)
  const heroText = $("[data-hero-text]");
  const heroArt = $("[data-hero-art]");
  if (heroText && heroArt) {
    const intro = () => {
      gsap.fromTo(heroText, { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 1, ease });
      gsap.fromTo(heroArt, { opacity: 0, scale: 0.96 }, { opacity: 1, scale: 1, duration: 1.2, delay: 0.15, ease });
    };
    if (door() === "closed") {
      gsap.set(heroText, { opacity: 0, y: 30 });
      gsap.set(heroArt, { opacity: 0, scale: 0.96 });
      document.addEventListener("mehmaan:door-opening", intro, { once: true });
    } else {
      intro();
    }
  }

  // 3. Painting parallax ([data-parallax])
  if ($("[data-parallax]")) {
    gsap.to("[data-parallax]", {
      yPercent: -10,
      ease: "none",
      scrollTrigger: { trigger: "[data-hero]", start: "top top", end: "bottom top", scrub: true },
    });
  }

  // 4. Manifesto words light up one by one ([data-word])
  if ($("[data-manifesto]")) {
    gsap.fromTo("[data-word]", { opacity: 0.12 }, {
      opacity: 1,
      stagger: 0.1,
      ease: "none",
      scrollTrigger: { trigger: "[data-manifesto]", start: "top 75%", end: "bottom 55%", scrub: true },
    });
  }

  // 5. Gold thread grows down the journey ([data-thread])
  if ($("[data-journey]")) {
    gsap.fromTo("[data-thread]", { scaleY: 0 }, {
      scaleY: 1,
      ease: "none",
      scrollTrigger: { trigger: "[data-journey]", start: "top 70%", end: "bottom 70%", scrub: true },
    });
  }

  // 6. Journey steps rise in ([data-step])
  $$("[data-step]").forEach((el) => {
    gsap.from(el, { opacity: 0, y: 40, duration: 0.9, ease: "power3.out", scrollTrigger: { trigger: el, start: "top 82%" } });
  });

  // 7. Experience cards fade up, staggered across each row of 3 (ExperienceCard.tsx)
  $$("[data-card]").forEach((el, i) => {
    gsap.from(el, {
      opacity: 0, y: 28, duration: 0.7, delay: (i % 3) * 0.08, ease,
      scrollTrigger: { trigger: el, start: "top bottom-=60", once: true },
    });
  });

  // 8. Trust cards fade up in turn
  $$("[data-trust]").forEach((el, i) => {
    gsap.from(el, { opacity: 0, y: 20, duration: 0.6, delay: i * 0.07, scrollTrigger: { trigger: el, start: "top bottom", once: true } });
  });
})();
