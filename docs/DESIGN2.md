# Mehmaan — Complete Website Design & UX Direction

Act as a senior product designer, creative director and senior frontend engineer.

Your task is to redesign the entire Mehmaan website into a premium, vintage Indian heritage-inspired hospitality platform.

Do not create a generic SaaS website, generic travel booking platform or modern startup landing page.

The website should feel like entering a beautiful Indian haveli, exploring Indian traditions, discovering local experiences and being welcomed into someone's home.

The design must combine traditional Indian visual identity with modern, intuitive and frictionless UX.

## 1. Core Brand Identity

Brand: Mehmaan

Core philosophy: अतिथि देवो भव — The guest is God.

Welcome expression:
"आइए, पधारिए"
"Aaiye, padhariye — Come in, you are welcome."

Brand positioning:

Millions of Indian families preserve beautiful traditions, food, art, crafts and experiences. Mehmaan helps them share their culture and hospitality with travellers.

The website must communicate:
- Indian hospitality.
- Cultural richness.
- Warmth and belonging.
- Authentic local experiences.
- Trust and transparency.
- Traditional Indian craftsmanship.

Important: Atithi Devo Bhava represents hospitality shared across Indian families and communities. Do not portray it as a religious ritual. Never ask hosts to perform rituals for guests.

## 2. Visual References

Use all the uploaded reference images as visual inspiration.

Study their:
- Typography and font character.
- Ornamental borders.
- Indian miniature artwork.
- Mughal and Rajput architectural motifs.
- Traditional floral patterns.
- Vintage editorial layouts.
- Rich textile-inspired colour combinations.
- Image compositions.
- Decorative framing.
- Overall visual atmosphere.

Reference directions:

A. Vintage Indian luxury:
Inspired by the first reference, featuring ornate borders, heritage typography, dark maroon backgrounds and traditional product photography.

B. Rajasthani textile heritage:
Inspired by the colourful textile collage references, featuring traditional arches, miniature paintings, floral motifs, paisley and intricate Indian patterns.

C. Jaipur-inspired editorial design:
Inspired by the postcard reference, featuring vintage paper textures, heritage illustrations, traditional architecture and handcrafted visual elements.

D. Indian cultural editorial:
Inspired by the Durga Puja website reference, featuring oversized artistic typography, immersive photography, dark backgrounds and elegant visual storytelling.

Do not copy any existing website or reproduce its exact layout. Create an original and consistent Mehmaan identity using these references.

## 3. Typography — Mandatory

Use Google Fonts.

Display font:
Tiro Devanagari Hindi

Body font:
Mukta

Apply consistently across EVERY page.

Typography hierarchy:

- Hero headings: Tiro Devanagari Hindi, 56px desktop / 36px mobile.
- Page headings: Tiro Devanagari Hindi, 36px desktop / 28px mobile.
- Card titles: Mukta 700, 21px desktop / 19px mobile.
- Body: Mukta 400, 17px desktop / 16px mobile.
- Small labels: Mukta 600, 13px.

Use elegant typography with generous spacing.

Do not introduce random fonts or use generic geometric sans-serif fonts for headings.

## 4. Colour System — Haveli Dusk

Use these exact CSS variables as the primary design system:

:root {
  --bg: #FBF5EA;
  --surface: #FFFFFF;
  --text: #2A1E14;
  --text-muted: #6B5A48;
  --line: #EADCC4;

  --primary: #A4401C;
  --secondary: #23395B;
  --accent: #E8A317;

  --food: #E0A526;
  --craft: #3D5A80;
  --music: #B4532A;

  --ok-fg: #1E5B3A;
  --ok-bg: #E3F2E8;

  --wait-fg: #7A4B12;
  --wait-bg: #F7E6C4;

  --err-fg: #8E1B2E;
  --err-bg: #FBE9EC;

  --night: #1B1410;
  --night-text: #F5E6C8;
  --brass: #C9A227;

  --radius: 14px;
  --space: 16px;

  --font-display: "Tiro Devanagari Hindi", serif;
  --font-body: "Mukta", sans-serif;
}

Additional heritage shades such as deep maroon, emerald, mustard and indigo may be used in photography, artwork and decorative backgrounds.

Colour rules:
- Never use pure white as the main page background.
- Use sandstone and cream as the primary backgrounds.
- Use terracotta for primary buttons.
- Use indigo for secondary actions and links.
- Use marigold and brass mainly for decoration or on dark backgrounds.
- Do not use marigold or brass as text on light backgrounds.
- Avoid combining saffron, white and green as a dominant design combination.
- Maintain accessible colour contrast.

Use a 60-30-10 colour distribution:
60% warm neutral backgrounds.
30% imagery and heritage colours.
10% strong accent colours.

## 5. Overall Design Language

Create a vintage Indian heritage design system.

Use:
- Ornamental Indian borders.
- Scalloped Mughal/Rajput arches.
- Subtle block-print textures.
- Traditional floral illustrations.
- Miniature painting-inspired illustrations.
- Vintage paper textures.
- Heritage-inspired section dividers.
- Decorative corner motifs.
- Elegant serif typography.
- Large immersive photographs.
- Asymmetrical editorial layouts.

Important:
Decorations must never interfere with usability.

Use decorative patterns selectively in empty spaces, section backgrounds, hero areas and footers.

Avoid putting ornamental borders around every card.

Avoid excessive decoration, visual clutter and unnecessary animations.

The result should look premium, artistic, authentic and professionally designed.

## 6. Important UX Decisions — READ CAREFULLY

I DO NOT WANT:

- No door-opening animation.
- No animated door interaction.
- No opening-door transition.
- No voice features.
- No voice recordings.
- No host voice clips.
- No voice notes.
- No text-to-speech.
- No speech-to-text.
- No automatic music.
- No autoplay audio.
- No unnecessary onboarding steps.
- No forced animations.
- No artificial loading screens.

The entrance must be a beautiful STATIC visual experience.

The first screen can feature a photograph of a traditional Indian haveli entrance, a scalloped arch, traditional typography and a warm welcome message.

Example:

"आइए, पधारिए"

"India has a beautiful way of welcoming guests. Discover it, one home at a time."

CTA: "Explore Experiences"

A subtle fade-in or gentle image transition is acceptable, but do not animate a door.

There must be no audio anywhere in the user journey.

Remove the previously proposed voice-based interpreter functionality. If language assistance is needed, build it as a simple text-based translation interface.

## 7. Website Pages and Design Requirements

### PAGE 1: Homepage / Entrance

This is the main brand introduction.

Design:
- Large immersive heritage photography.
- Scalloped arch-inspired image framing.
- Vintage Indian typography.
- Warm sandstone background.
- Ornamental borders.
- A subtle heritage-inspired visual treatment.

Hero copy:

"आइए, पधारिए"

"Discover the warmth of Indian homes, traditions and unforgettable experiences."

Primary CTA:
"Explore Experiences"

Secondary CTA:
"Discover Our Heritage"

Below the hero:
- Featured experiences.
- Popular destinations.
- Discover Indian traditions.
- Meet local hosts.
- Cultural experience categories.

The homepage should immediately communicate what Mehmaan offers.

Do not force users to complete a separate entrance interaction before exploring the website.

### PAGE 2: Browse Experiences

Route: /

Design a premium editorial-style discovery page.

Include:
- Search bar.
- Category filters.
- Location filters.
- Date and guest filters.
- Featured experiences.
- Experience cards.
- Popular cultural experiences.
- Featured hosts.

Experience cards should include:
- Beautiful 4:3 photography.
- Experience title.
- Host name.
- Location.
- Duration.
- Category badge.
- Price.
- View experience CTA.

Use elegant image framing, subtle hover effects and consistent spacing.

Desktop: Use a visually balanced grid.

Mobile: Use a clean single-column layout or appropriate compact cards.

Filters must work correctly.

### PAGE 3: Experience Listing

Route: /listings/{id}

Design this page like a premium heritage travel editorial.

Include:
- Large photography gallery.
- Arch-inspired image frames.
- Experience description.
- Host introduction.
- Host photographs.
- What guests will experience.
- Duration.
- Guest capacity.
- Food information.
- Dietary information.
- General location/area.
- Exact price breakdown.
- Refund and cancellation policy.
- Availability and booking slots.

The host must feel like a real person, not a product listing.

Primary CTA:
"Book This Experience"

Avoid unnecessary information and make the booking decision easy.

### PAGE 4: Payment

Route: /pay/mock/{order}

Design:
- Minimal, trustworthy checkout.
- Heritage styling in the background and accents.
- Clear booking summary.
- Guest information.
- Total price.
- Refund policy.
- Payment status.

Display clearly:

"TEST PAYMENT — No real money will be charged."

The payment interface must be simple and familiar.

Never hide charges or refund conditions.

### PAGE 5: Booking Confirmation

Route: /b/{token}

Create a beautiful confirmation experience.

When booking becomes CONFIRMED:
- Display an elegant confirmation status.
- Show the experience details.
- Show host information.
- Show booking date and time.
- Show guest count.
- Show location-sharing status.
- Provide cancellation options.
- Provide text-based language assistance if required.

A gentle marigold petal animation is allowed ONLY when booking becomes CONFIRMED.

It should be subtle, short and respect reduced-motion settings.

Confirmation copy:

"Your place is ready."

"We look forward to welcoming you."

After the experience is completed:

"Phir zaroor aana — Please come again, {name}."

### PAGE 6: Cancellation

Route: /b/{token}/cancel

Create a clear and transparent cancellation experience.

Show:
- Original booking amount.
- Refund amount.
- Host's retained amount.
- Cancellation policy.
- Confirmation action.

Example:

"You will receive ₹2,400 back. Meena ji keeps ₹600."

Use actual booking calculations. Never invent prices.

### PAGE 7: Language Assistance

No voice functionality.

If the existing interpreter feature is required, redesign it as a TEXT-ONLY translation interface.

Include:
- Original message.
- Translated message.
- Language selector.
- Copy translation.
- Clear conversation history.

Keep the experience accessible and straightforward.

### PAGE 8: Error States

Create beautifully designed but functional error pages.

Examples:
- Slot unavailable.
- Booking expired.
- Payment failed.
- Listing not found.
- Network error.

Use short, friendly and reassuring copy.

Provide a clear next action.

## 8. Navigation

Create a consistent premium navigation bar.

Include:
- Mehmaan logo.
- Explore.
- Experiences.
- Destinations.
- About.
- Login/Profile.

Keep navigation elegant and uncluttered.

On desktop, use a refined horizontal navigation.

On mobile, create a proper responsive navigation menu.

Do not use oversized decorative elements that make navigation difficult.

## 9. Interaction and Animation

The website should feel smooth, responsive and alive without becoming distracting.

Allowed:
- Subtle fade-in.
- Gentle image parallax.
- Smooth scrolling.
- Elegant hover effects.
- Small card elevation.
- Subtle page transitions.
- Marigold petals on booking confirmation only.

Not allowed:
- Door opening.
- Audio or music.
- Voice interactions.
- Long loading animations.
- Excessive floating elements.
- Distracting cursor effects.
- Animations that block user actions.

Respect prefers-reduced-motion.

## 10. Smooth User Experience Principles

Design for actual users, not just screenshots.

Every page must:
- Have one clear primary action.
- Provide intuitive navigation.
- Load quickly.
- Work on mobile.
- Have readable typography.
- Show clear prices.
- Explain booking conditions.
- Provide visible feedback after actions.
- Have meaningful empty, error and loading states.
- Avoid unnecessary steps.

The booking process should be as short as possible.

Allow users to optionally specify dietary preferences and allergies in a field of no more than 200 characters.

Do not ask for unnecessary personal information.

Trust must be visible throughout the journey.

Use real host photos and honest descriptions. Label demo hosts clearly as role-play. Never invent reviews, ratings, host identities or booking numbers.

## 11. Footer

Create a beautiful dark Festival Night footer.

Use:
- Background: #1B1410.
- Text: #F5E6C8.
- Decorative brass elements: #C9A227.
- Subtle traditional Indian block-print pattern.

Include:
- Mehmaan brand story.
- Explore experiences.
- Host information.
- Contact.
- Privacy policy.
- Terms and conditions.
- Cancellation policy.
- Photographer credits for licensed photography.

## 12. Technical Implementation Instructions

Before changing anything:

1. Inspect the complete existing project.
2. Understand its frontend framework and backend architecture.
3. Identify existing routes, components, APIs and database logic.
4. Preserve working backend functionality.
5. Reuse existing components and data wherever appropriate.
6. Do not break authentication, booking, payment or listing functionality.

Implement the design as a reusable design system.

Create reusable components for:
- Navbar.
- Footer.
- Buttons.
- Experience cards.
- Arch image frames.
- Section headings.
- Category badges.
- Status boxes.
- Search and filters.
- Form fields.
- Loading states.
- Empty states.

Use CSS variables for colours, typography, spacing and border radius.

Avoid duplicated CSS and inconsistent component styling.

Optimize images, lazy-load below-the-fold images and avoid unnecessary dependencies.

Use properly licensed photography from Unsplash or Pexels. Do not use Pinterest images as production assets. Record photographer credits where required.

## 13. Responsive Design

The website must be fully responsive.

Desktop:
- Rich editorial compositions.
- Large hero imagery.
- Multi-column layouts.
- Generous whitespace.

Tablet:
- Adapted grids.
- Comfortable typography.
- Balanced image sizes.

Mobile:
- Single-column layouts where appropriate.
- Easy-to-tap buttons.
- No horizontal overflow.
- Readable headings.
- Proper mobile navigation.
- Optimized images.
- Simplified decorative elements.

Do not simply shrink the desktop layout.

## 14. Final Quality Standard

The final result should feel like:

"A beautifully designed digital heritage experience inspired by Indian havelis, miniature paintings, traditional textiles and the warmth of Indian hospitality."

It should combine the artistic richness of vintage Indian websites with the usability and engineering quality of a modern premium product.

Do not stop after designing the homepage.

Apply the same consistent design language to ALL pages and states.

First inspect the project, then propose a short implementation plan, then implement the changes.

Finally test:
- All routes.
- All buttons and links.
- Search and filters.
- Booking flow.
- Payment flow.
- Cancellation flow.
- Responsive layouts.
- Error states.
- Accessibility.
- No audio or voice functionality.
- No door-opening animation.

Prioritize a beautiful but genuinely usable product. Design quality and user experience are equally important.