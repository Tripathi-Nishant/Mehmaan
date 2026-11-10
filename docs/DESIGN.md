# DESIGN.md — Mehmaan visual and UX design

Status: Approved (Nancy, 2026-11-09). Build this **after** the core flow works (Nov 10 morning, time limit 4 hours).

## 1. Concept: अतिथि देवो भव (Atithi Devo Bhava): "the guest is God"

The site gives travelers the feeling of Indian hospitality: being welcomed as an honoured guest in a real home, from the first click to the goodbye. "Aaiye, padhariye" is the first words of that welcome.

- Present it as **Indian hospitality**, a value shared across families and faiths, not as a religious ritual. Never ask hosts to perform rituals for guests.
- The phrase is also used by the Ministry of Tourism's campaign: use the idea, never imitate government branding or logos.
- Pitch line: "Atithi Devo Bhava: in India, the guest is God. Millions of homes live this every day, but they're invisible online. Mehmaan lets them welcome the world, in their own voice."

| In a real Indian home | On Mehmaan |
|---|---|
| Met at the door | Door entrance, "आइए, पधारिए" |
| Addressed with respect ("ji", "aap") | Respectful copy: "Meena ji", "You are our guest" |
| Water offered before anything is asked | Listing answers questions first: what to expect, full price, refund rules |
| The guest's comfort first | **Booking form asks dietary needs and allergies** (optional, ≤ 200 chars); the host hears them in the booking voice note |
| The guest eats first | Interpreter puts the guest's turn first; host hears it slowly and clearly |
| Seen off at the door: "Phir aana" | COMPLETED page: "Phir zaroor aana: please come again, {name}." |
| A small gift when leaving | Keepsake card (v2) |

The site feels like being a guest in a real Indian home.

| Principle | On the site |
|---|---|
| Entering a home | Door entrance, warm colours inside, "you are invited" language |
| People first | Host photos, hands and voice come before the price |
| Calm interface, rich content | Neutral backgrounds; colour comes from photos and small accents (60-30-10) |
| Trust always visible | Fixed price, refund rules, "Location shared", "TEST PAYMENT" |
| Honest | Role-play hosts labelled; no fake reviews, no invented numbers |

Copy tone: warm and simple, like a host. A few Hindi words with English next to them ("Aaiye — come in"). Short sentences.

## 2. Locked decisions

| Item | Decision |
|---|---|
| Door style | **Red sandstone wall, scalloped (Rajput/Mughal) arch, dark wood double door with iron studs** |
| Door image | **Free-licence photo** (Unsplash or Pexels licence). Never Pinterest images. Credit the photographer in the footer |
| Palette | **Haveli Dusk** inside; **Festival Night** for the entrance and footer |
| Pages | Entrance, Browse, Listing, Payment, Booking (5 states), Cancel, Interpreter, Errors. **No "How it works" page** |
| Host voice (Timbre) | **Female** Hindi voice; respectful "aap" form |
| Confirmed celebration | **Marigold petals falling** on the booking page when the status becomes CONFIRMED |

## 3. Palette: Haveli Dusk (WCAG contrast checked)

```css
:root{
  /* ground and text */
  --bg:#FBF5EA;          /* sandstone */
  --surface:#FFFFFF;
  --text:#2A1E14;        /* ink brown, 15.0 on bg */
  --text-muted:#6B5A48;  /* 6.1 on bg */
  --line:#EADCC4;
  /* brand */
  --primary:#A4401C;     /* terracotta: buttons, white text 6.3 */
  --secondary:#23395B;   /* indigo: links, headings accents, 10.7 on bg */
  --accent:#E8A317;      /* marigold: decoration and on dark only */
  /* category accents (card art, badges) */
  --food:#E0A526; --craft:#3D5A80; --music:#B4532A;
  /* status */
  --ok-fg:#1E5B3A;  --ok-bg:#E3F2E8;    /* confirmed, Location shared */
  --wait-fg:#7A4B12; --wait-bg:#F7E6C4; /* waiting, TEST, role-play */
  --err-fg:#8E1B2E; --err-bg:#FBE9EC;   /* cancelled, errors */
  /* Festival Night (entrance, footer) */
  --night:#1B1410; --night-text:#F5E6C8; --brass:#C9A227;
  /* shape and type */
  --radius:14px; --space:16px;
  --font-display:"Tiro Devanagari Hindi",serif;
  --font-body:"Mukta",system-ui,sans-serif;
}
```

Rules:
- Marigold and brass are never text on a light background (contrast fails). They're for decoration, or for text on `--night`.
- Status always has a word or icon too, never colour alone.
- Do not combine saffron + white + green (it reads as the national flag). Use warm off-white backgrounds, never pure white as the page ground.

## 4. Typography

| Use | Font | Size (desktop / phone) |
|---|---|---|
| Hero heading | Tiro Devanagari Hindi | 56 / 36 px |
| Page heading | Tiro Devanagari Hindi | 36 / 28 px |
| Card title | Mukta 700 | 21 / 19 px |
| Body | Mukta 400 | 17 / 16 px, line height 1.5 |
| Small labels, badges | Mukta 600 | 13 px |

Both fonts support Hindi and English. Load them from Google Fonts.

## 5. Components

- **Button:** primary terracotta, white text, radius 999px, min height 44 px. One primary button per page.
- **Badge:** pill, 13 px; "Location shared" (ok colours), "Demo host (role-play)" (wait colours), category badge.
- **Experience card:** photo (4:3) → badges → title → host line → meta line → price + View. 3D tilt on hover (desktop only).
- **Status box:** large, coloured by status, with an icon and one sentence.
- **Arch frame:** the scalloped arch shape as a mask on hero and listing photos (CSS `clip-path` or an SVG mask). This is the repeated motif.
- **Pattern:** one subtle block-print pattern, only on empty areas (footer, empty states).

## 6. Pages

| # | Page | Main content | Main action | States |
|---|---|---|---|---|
| 1 | Entrance (first visit only) | Real door photo, "आइए, पधारिए / Aaiye, padhariye", sound choice | Enter with sound / Enter quietly | Skip if seen (localStorage) or reduced motion |
| 2 | Browse `/` | Hero (arch-masked photo, parallax), search, category chips, cards | Open listing | Empty: "No experiences match. Try another day." |
| 3 | Listing `/listings/{id}` | Photo gallery in arch frames, host voice clip with subtitles, what you do, duration, guests, food type, area only, refund rules, badges | Pick slot + guests → Book | Slot full → message + other slots |
| 4 | Payment `/pay/mock/{order}` | Summary, total, refund rules, "TEST PAYMENT — no real money" | Pay (TEST) | Fail link |
| 5 | Booking `/b/{token}` | Status box + details; map + landmark only when confirmed | Interpreter / Cancel | See §7 |
| 6 | Cancel `/b/{token}/cancel` | "You get ₹2,400 back. Meena keeps ₹600." + the rule | Confirm cancel | After start → "Report a problem" (v2) |
| 7 | Interpreter | Two large buttons (host: terracotta, traveler: indigo), both texts per turn | Hold to speak | Outside window → message |
| 8 | Errors | Slot full, reservation expired, link not found | Back / book again | — |

Emails (3): same palette, single column, booking link button, "TEST" note.

## 7. Booking page states

| Status | Look | Message |
|---|---|---|
| PAID_PENDING_HOST | wait colours, gentle pulse on the icon | "Meena will confirm soon. This page updates by itself." |
| CONFIRMED | ok colours + **marigold petals falling** (once, ~3 s) | "Confirmed! Meena is expecting you." + map, time, interpreter |
| CANCELLED | neutral | "Cancelled. ₹X refunded (test)." |
| EXPIRED | neutral | "Your reservation time ended." |
| COMPLETED | warm | "Phir zaroor aana: please come again, {name}." |

Petals: 25–35 small marigold shapes (orange `#F28C1B`, yellow `#F7C23A`), CSS keyframes falling with slight rotation and sideways drift, then removed. Not shown with `prefers-reduced-motion`. Only when the status *changes* to CONFIRMED, not on every page load.

## 8. Entrance (door) build

1. Choose a free-licence photo (criteria in §9). Save the original and its licence/credit in `docs/assets.md`.
2. In Photopea (free web editor) or GIMP, cut 3 layers, same canvas size:
   - `door_frame.webp`: wall + arch, with the door area transparent (or dark)
   - `door_left.png`: left leaf only, transparent around it (keep the arched top)
   - `door_right.png`: right leaf only
3. Stack them in one full-screen container (`object-fit: cover`, same position for all three). Leaves rotate with `rotateY(±110deg)` and `transform-origin` on their outer hinge edge. The frame fades out after the leaves open.
4. Sound (Web Audio, already in the prototype): temple bell ×2 → wooden creak during opening → thud → tanpura.
5. Size: each image ≤ 300 KB (WebP for the frame; PNG/WebP with alpha for the leaves).

Fallback if cutting takes too long: use the full photo, split exactly down the centre into two halves, and rotate the halves (the arch frame rotates too, which is acceptable).

## 9. Photo criteria (door and hero)

- Straight-on view, symmetric, both leaves fully visible and closed
- Red sandstone, scalloped arch, dark wood with iron studs
- Even light, no people, no watermark, no text
- At least 2000 px tall
- Licence: Unsplash licence or Pexels licence (free for websites). Record the photographer and URL

## 10. Motion and sound

Only these move: door entrance, parallax hero, card tilt, status pulse, marigold petals. Everything respects `prefers-reduced-motion`. Sound only after the visitor chooses it; a mute button is always visible.

## 11. Host voice (Telegram)

- `GNANI_TTS_VOICE_HI` = a **female** Hindi Timbre voice (pick the warmest one in the Gnani console).
- Always "aap" form, short sentences, numbers repeated clearly.

## 12. Guest journey: one welcome moment per step

Rules: use names ("Meena is expecting you, Sophie"); the host's real voice is the thread; make the high point (confirmation, arrival) and the end strong. Only real voices and photos; respectful, never "exotic".

| # | Stage | Welcome moment | Build |
|---|---|---|---|
| 1 | Arrive at site | Door opens: bell, creak, tanpura. "आइए, पधारिए — come in." | Now |
| 2 | Discover | Cards lead with the host: "Hosted by Meena", host face/hands photo | Now |
| 3 | Meet the host | Listing page: "Hear Meena" plays her consented onboarding voice clip with English subtitles (from the transcript + translation) | Now |
| 4 | Decide | "What to expect" in 3 short steps (arrive → do together → eat/finish together); refund rules visible | Now |
| 5 | Book | Button text: "Request to visit Meena's home". Optional field "Dietary needs or allergies" → stored on the booking → added to the host's booking voice note ("Sophie ko mungfali se allergy hai"; translate with the LLM, show the original English in the host's text message too) | Now (small backend change: one nullable column + note text) |
| 6 | Wait | "Meena has received your request. She'll reply soon." Live status | Now |
| 7 | Confirmed | Marigold petals; "Meena is expecting you, {traveler first name}." + "Hear Meena" button | Now |
| 8 | Prepare | Confirmation email section "Before you go": 5 Hindi words with meaning (Namaste, Dhanyavaad, Haan / Nahi, Bahut swadisht, Phir milenge); home customs (shoes off at the door, right hand for food, ask before photos); what to bring | Now (static text per category) |
| 9 | Arrive at home | Interpreter opens with a "first words" card: "Namaste, {host} ji. Aapka ghar bahut sundar hai." with a play button (Timbre) | Now (small) |
| 10 | Experience | Push-to-talk interpreter | Now |
| 11 | Goodbye | Host thank-you voice note, translated for the guest | v2 |
| 12 | After | Downloadable keepsake card (host photo, experience, date, thank-you); recipe for food experiences | v2 |
| 13 | Remember | Review "What will you remember?"; host hears it in Hindi | v2 |

Host side: listing live → "Badhai ho! Aapka anubhav website pe aa gaya hai." Booking request names the guest and country. v2: after "haan", the host may record a short welcome message for the guest → translated → shown on the guest's booking page (strongest welcome moment; mention in the pitch).

Customs text must be polite and factual; do not present the culture as strange. Payment, cancel and error screens stay plain: warmth never hides information.

## 13. Build order (Nov 10 morning)

1. `style.css` with the tokens in §3 + fonts → apply to all pages (1 h)
2. Browse + listing visual design, arch-masked photos (1 h)
3. Booking page states + marigold petals (45 min)
4. Door entrance with the real photo layers + sound (1 h)
5. Phone-width check on every page (15 min)

Stop when the time limit ends. A plain page that works is better than a beautiful page that doesn't.