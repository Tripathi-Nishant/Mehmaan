Read DESIGN.md. I am upgrading the visual style to "Indian heritage": block-print borders,
Mughal floral frames, a museum painting in the hero, paper textures. 


Technical rules:
- Borders with CSS border-image (repeat: round), not separate images per side.
- Fonts from Google Fonts: Rozha One (main headings), Yatra One (decorative headings),
  Mukta (body). Keep body text Mukta.
- Hero painting inside the existing scalloped arch shape (clip-path or SVG mask).
- Textures as background-image with low opacity; text contrast at least 4.5:1.
- Payment, booking, cancel pages: parchment + one thin border only.
- Footer: credit line for the museum painting and the photos.
- Images WebP, max 300 KB each.
Do one section at a time, screenshot desktop + 375 px, and stop for my approval.


PAGE BACKGROUND
Feeling: warm, aged, handmade
Reference: cream parchment with soft texture
Material: parchment texture (Unsplash), very subtle, colour #F3E6CC
Rule: text must stay readable; texture opacity low

PAGE FRAME AND SECTION DIVIDERS
Feeling: festive, textile, crafted
Reference: red/yellow block-print border with triangles and flowers
Material: one horizontal border strip image, repeated with CSS border-image
Rule: max 32 px tall; only at the top of the page and between sections

HERO
Feeling: royal, welcoming, painted
Reference: Pichwai lotus painting inside a scalloped arch on maroon
Material: a CC0 museum painting inside the scalloped arch; maroon background
          (#5C1A1B) with mandala corners in gold; heading "आइए, पधारिए" in Rozha One, gold
Rule: one painting only; the button stays clearly visible

EXPERIENCE CARDS
Feeling: precious, like small framed paintings
Reference: cream card with thin Mughal floral border
Material: thin floral border (border-image), cream inside, host photo in arch shape
Rule: price and button stay plain and clear

"ATITHI DEVO BHAVA" BAND
Feeling: proud, sacred, warm
Reference: deep maroon with gold temple line art
Material: maroon paper texture, gold line pattern, text in Yatra One
Rule: one band only, between the hero and the listings

PAYMENT, BOOKING, CANCEL PAGES
Feeling: calm, trustworthy
Material: parchment background + one thin border; no paintings
Rule: no decoration near money or status information