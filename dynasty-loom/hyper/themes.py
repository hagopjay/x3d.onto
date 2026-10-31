"""themes.py: the Dynasty Loom v2 look system, one table for the hypersphere generator, its shaders and the page.

The four directions of the v2 style board (museum-atlas, documentary-night, editorial-clarity, heritage-glass) as look parameters only:
palette, backdrop, glass, fibers, line weight, type, chrome and the portrait overlay. Nothing here touches the data, the layout (radius = time),
the camera grammar or the flight timing. Read by:
  hyper/build_hypersphere.py --theme SLUG   the scene: dye colours, line widths, glow tints, backgrounds (style_block() for the GLSL constants)
  tapestry/tools/merge_views.py             the page: page_css() for DEFAULT_THEME, ALT_THEME and the PHONE_UI layer, look_json() for the script
Colours are sRGB hex unless a key says lin (linear light, for the dark direction's emission). The table came from the style board's styles.py
(proto/v2/styleboard); its fonts are named here as Google Fonts families (the Artifact CSP admits fonts.gstatic.com only, so the page links the
Google Fonts stylesheet and never ships WOFF2 itself). Deterministic: no clock, no randomness."""
import json

DEFAULT_THEME = 'museum-atlas'       # the page opens in it, and build_hypersphere.py builds it without --theme
ALT_THEME = 'documentary-night'      # the one alternate the page ships, behind a quiet switch in the header
PHONE_UI = 'editorial-clarity'       # on phones (max-width 720px) the interface takes this direction's layout and type (not its colours)

GOOGLE_FONTS = {   # family -> the axis spec of the Google Fonts css2 API (OFL 1.1 families)
    'EB Garamond': 'ital,wght@0,400;0,500;0,600;1,400',
    'Cormorant Garamond': 'ital,wght@0,500;0,600;1,500',
    'Jost': 'wght@400;500',
    'Source Serif 4': 'wght@400;600',
    'Source Sans 3': 'wght@400;600',
    'Marcellus': 'wght@400',
}
SERIF_FB = 'Georgia, "Iowan Old Style", "Times New Roman", serif'
SANS_FB = '"Segoe UI", "Helvetica Neue", Arial, system-ui, sans-serif'

STYLES = [
  dict(
    slug='museum-atlas', short='Atlas', name='Museum Atlas',
    pitch='An engraved globe on warm ivory: the family drawn in fine ink, as a museum would hang it.',
    mood='A natural-history gallery: an engraved celestial globe under glass, a printed wall label beside it.',
    fonts=['EB Garamond'], display='EB Garamond', text='EB Garamond', ui='EB Garamond',
    swatches=[('Ivory ground', '#f3eee3'), ('Paper shadow', '#e6dccb'), ('Sepia ink', '#5b4a3a'), ('Oxblood', '#7b2d26'), ('Ochre', '#a2752a'),
              ('Slate', '#46607a'), ('Sage', '#5d7553'), ('In-law grey', '#9b8f7e')],
    # ---- scene
    ink=1, ground_top='#f3eee3', ground_bot='#e8dfcd', pool='#f8f4eb', pool_k=0.55, pool_w=1.1, mottle=0.03, stars=0.0, grain=0.006,
    dyes={'red': '#7b2d26', 'gold': '#a2752a', 'green': '#5d7553', 'blue': '#46607a'}, ecru='#9b8f7e', ecru_word='warm grey', dye_l=38.0, chroma=1.0, ink_value=1.0,
    engrave='#5b4a3a', outline_a=0.55, graticule=0.13, grat_back=0.05, shell_a=0.20, past='#7b5a3a', present='#4f5f6f', fell_c='#7b2d26', fell_a=0.0,
    frost='#ffffff', frost_a=0.0, body_a=0.0, rimdark='#3a3027', rimdark_a=0.0, refl=0.0, glint=0.0, halo_a=0.0,
    bleed_a=0.10, bleed_k=7.0, rest='#bdb2a0', rest_a=0.6, sheen=0.0, round=0.12,
    seed_ink='#3b2f25', ink_hue=0.35, ink_density=0.85,
    ring='#bfae7f', ring_amb=0.72, ring_diff=0.30, ring_spec=0.12,
    core_w=0.0016, core_px=(0.9, 2.4), glow_w={'fast': 0.0055, 'balanced': 0.006, 'ultra': 0.0065}, glow_px=(1.9, 5.0),
    seed_glow=dict(halo_tint=(0.55, 0.42, 0.30), core_tint=(0.35, 0.27, 0.20), exposure=0.8), bead_glow=dict(halo_tint=(0.48, 0.18, 0.15), core_tint=(0.40, 0.14, 0.12), exposure=0.9),
    # ---- screen-mode constants (unused in ink mode, kept at v3's values)
    rim_lin=(0.40, 0.56, 1.0), rim_gain=1.0, past_lin=(1.0, 0.60, 0.30), present_lin=(0.40, 0.55, 1.0), haze_lin=(0.42, 0.26, 0.78), haze_gain=1.0, flow=1.0,
    shell_front=2.2, white=0.12, white_ecru=0.3, pulse=1.6, front=1.1, tip=2.0, glow=0.8, rest_lin=(0.55, 0.62, 0.80), rest_glow=0.22, seed_centre=(1.0, 0.92, 0.8), seed_limb=(1.0, 0.55, 0.25),
    # ---- page
    brand='Dynasty Loom', brand_sub='An atlas of three families',
    css=dict(scene='#efe9dc', panel='rgba(251, 248, 241, .95)', ink='#2a211b', dim='#6d6052', accent='#7b2d26', line='rgba(91, 74, 58, .26)', chip='rgba(91, 74, 58, .06)',
             shadow='0 1px 0 rgba(255,255,255,.6) inset, 0 10px 28px rgba(70, 50, 30, .10)', radius='3px', blur='0px', status='#6d6052',
             lab_bg='transparent', lab_ink='#2f261f', lab_house='#7b2d26', lab_year='#7d705f', lab_sub='#1f1813', lab_halo='0 0 3px #f3eee3, 0 0 6px #f3eee3, 0 0 1px #f3eee3',
             vignette='radial-gradient(ellipse 85% 80% at 50% 48%, transparent 62%, rgba(120, 95, 60, .16) 100%)', ph_bg='#e7ddcb', ph_fg='#b8a78e'),
    labels='small caps serif, no box: sepia ink with a paper halo', caption='a museum wall label: square corners, a hairline rule, the title in the display face',
    portrait=dict(shape='oval', in0=0.55, in1=0.95, out_ms=700, scale0=0.97, blur=3, leader=0, w=176, h=220, pw=112, ph=140),
    portrait_note='An oval cameo, feathered like a vignetted albumen print, a hairline keyline; it dissolves in over the last 40 percent of the flight and holds still at the stop.',
    light='No lights read as light: the ground is paper, the globe is engraving, the dyes are pigment. A faint warm pool sits behind the opening view.',
    glass='The glass is an engraved globe: a fine sepia outline, 15-degree meridians and parallels (the far side at half strength), and the 50-year time shells as thin limb circles. No haze, no reflections.',
    lines='Ink lines 0.9 to 2.4 px with a 10 percent ink bleed for anti-aliasing; no bloom, no pulses, no energy front. Estimated years stay dashed.',
    motion='Flights keep v3\'s van Wijk zoom-and-pan with its quintic ease; nothing pulses. The selection eases in over 0.7 s as ink deepening, the rest fading to pencil.',
    chrome='Square-cornered ivory cards with a hairline rule; buttons as small-caps text links; the caption is a wall label.',
    risks=dict(perf='Cheap: no raymarched haze or reflection in the glass, only analytic lines; the paper mottle (fbm) in the backdrop makes it a little dearer than Editorial (Confirmed, SwiftShader, relative).',
               legible='Fine lines on ivory need 1x density screens to hold 0.9 px; the 1/16 dye steps sit close to the in-law grey (Suspected).',
               truth='Pigment metaphors carry no extra meaning; dashes for estimated years are kept. The oxblood/ochre/sage/slate remap keeps each family in its v3 hue family (Confirmed by the palette table).')),
  dict(
    slug='documentary-night', short='Night', name='Documentary Night',
    pitch='A warm key light in a deep navy room: the family as the title sequence of a well-shot documentary.',
    mood='A slow documentary opening: a lit object in a dark studio, film grain, gold and rose, nothing that blinks.',
    fonts=['Cormorant Garamond', 'Jost'], display='Cormorant Garamond', text='Jost', ui='Jost',
    swatches=[('Navy-charcoal', '#1b2230'), ('Deep ground', '#10141c'), ('Key warm', '#e8d3ad'), ('Muted gold', '#b8975a'), ('Rose', '#b06a6e'),
              ('Dusty blue', '#7c93b3'), ('Sage-teal', '#6f9a8a'), ('In-law warm grey', '#8f877b'), ('Parchment text', '#ece4d6')],
    ink=0, ground_top='#1b2230', ground_bot='#0f131b', pool='#2a3344', pool_k=0.7, pool_w=0.9, mottle=0.06, stars=0.10, grain=0.010,
    dyes={'red': '#b06a6e', 'gold': '#b8975a', 'green': '#6f9a8a', 'blue': '#7c93b3'}, ecru='#8f877b', ecru_word='warm grey', dye_l=54.0, chroma=0.72, ink_value=1.0, value_norm=0.45,
    engrave='#d8c7a5', outline_a=0.0, graticule=0.0, grat_back=0.0, shell_a=0.0, past='#d9a066', present='#8ea3c4', fell_c='#e8d3ad', fell_a=0.0,
    frost='#ffffff', frost_a=0.0, body_a=0.0, rimdark='#000000', rimdark_a=0.0, refl=0.55, glint=0.45, halo_a=0.0,
    bleed_a=0.0, bleed_k=6.0, rest='#6b7894', rest_a=0.0, sheen=0.0, round=0.0,
    seed_ink='#e8d3ad', ink_hue=0.5, ink_density=1.0,
    ring='#8c8170', ring_amb=0.04, ring_diff=0.22, ring_spec=0.28,
    core_w=0.0022, core_px=(0.7, 3.0), glow_w={'fast': 0.011, 'balanced': 0.014, 'ultra': 0.016}, glow_px=(2.2, 11.0),
    seed_glow=dict(halo_tint=(1.0, 0.74, 0.46), core_tint=(1.0, 0.92, 0.80), exposure=0.85), bead_glow=dict(halo_tint=(1.0, 0.80, 0.58), core_tint=(1.0, 0.95, 0.86), exposure=0.85),
    rim_lin=(0.78, 0.66, 0.48), rim_gain=0.4, past_lin=(0.85, 0.55, 0.30), present_lin=(0.42, 0.50, 0.66), haze_lin=(0.30, 0.28, 0.40), haze_gain=0.45, flow=0.35,
    shell_front=0.5, white=0.04, white_ecru=0.08, pulse=0.25, front=0.3, tip=0.8, glow=0.42, rest_lin=(0.42, 0.47, 0.58), rest_glow=0.14, seed_centre=(1.0, 0.90, 0.76), seed_limb=(0.95, 0.60, 0.36),
    brand='DYNASTY LOOM', brand_sub='Three families in time',
    css=dict(scene='#141a24', panel='rgba(14, 18, 26, .0)', ink='#ece4d6', dim='#a59b8b', accent='#d8bf8a', line='rgba(216, 191, 138, .28)', chip='rgba(236, 228, 214, .06)',
             shadow='none', radius='2px', blur='0px', status='#a59b8b',
             lab_bg='transparent', lab_ink='#e9e1d2', lab_house='#d8bf8a', lab_year='#9aa3b5', lab_sub='#fff3dc', lab_halo='0 1px 2px rgba(0,0,0,.85), 0 0 8px rgba(0,0,0,.55)',
             vignette='radial-gradient(ellipse 80% 75% at 50% 46%, transparent 55%, rgba(4, 6, 10, .55) 100%)', ph_bg='#2a2f38', ph_fg='#59606c'),
    labels='Jost caps, tracked, no box: parchment text with a soft shadow, gold for houses', caption='a lower third: no box, a gradient scrim, the title in Cormorant caps',
    portrait=dict(shape='plate', in0=0.40, in1=0.95, out_ms=1100, scale0=1.0, blur=0, leader=0, w=200, h=250, pw=120, ph=150, kenburns=1),
    portrait_note='A soft-edged plate (18 px feather on every side) that cross-dissolves in over the second half of the flight, then drifts 4 percent closer during the hold (a Ken Burns push); a lower-third name in italic.',
    light='One warm key from upper right (the glint and the seed), a cool fill from the navy room; ACES in-shader as v3, exposure lowered so nothing clips.',
    glass='A thin warm rim and a quiet room reflection; the time shells kept but softened (the pulse of the 12 s energy front cut to a quarter); haze at 45 percent.',
    lines='Fibers keep v3\'s two passes with a gentle bloom: glow gain 0.42 (was 0.8), cores mixed 4 percent to white (was 12), chroma 0.72 (was 1.4) and each dye kept nearer its own value instead of pushed to full brightness, for dusty gold and rose.',
    motion='Restrained: pulses at a sixth of v3, no running front on the glass. Portraits dissolve over the second half of a flight and leave over 1.1 s, like a slow cut.',
    chrome='No boxes: a gradient scrim carries the lower third; the rail is thin numerals; buttons are outlined in pale gold.',
    risks=dict(perf='About half of v3 (the nebula sky is gone) but the dearest of the four: the glass still raymarches its haze at Balanced and Ultra (Confirmed, SwiftShader, relative). The CSS film grain adds one blended layer (Likely).',
               legible='Parchment on navy reads well; the lower third over bright threads relies on the scrim (Likely). The 0.7 px core floor dims far threads.',
               truth='Bloom can suggest importance; it is uniform across lives so it carries no data (Likely). Desaturated dyes keep hue order (Confirmed by the palette table).')),
  dict(
    slug='editorial-clarity', short='Clarity', name='Editorial Clarity',
    pitch='Flat colour, thin precise lines and a clean humanist sans: the clarity of a top newspaper\'s interactive graphic.',
    mood='A data desk graphic: a white page, one accent colour per family, everything labelled, nothing decorative.',
    fonts=['Source Serif 4', 'Source Sans 3'], display='Source Serif 4', text='Source Sans 3', ui='Source Sans 3',
    swatches=[('Paper', '#f6f6f4'), ('Cool grey ground', '#eceef0'), ('Rule grey', '#9aa3ad'), ('Vermilion', '#b7412e'), ('Mustard', '#c08a12'),
              ('Green', '#2e7d4f'), ('Blue', '#2b6cb0'), ('In-law grey', '#a3a9b1'), ('Text', '#1a1d21')],
    ink=1, ground_top='#f7f7f5', ground_bot='#eceef0', pool='#fafafa', pool_k=0.0, pool_w=1.0, mottle=0.0, stars=0.0, grain=0.0,
    dyes={'red': '#b7412e', 'gold': '#c08a12', 'green': '#2e7d4f', 'blue': '#2b6cb0'}, ecru='#a3a9b1', ecru_word='grey', dye_l=50.0, chroma=1.1, ink_value=1.0,
    engrave='#7d8690', outline_a=0.75, graticule=0.0, grat_back=0.0, shell_a=0.16, past='#9aa3ad', present='#9aa3ad', fell_c='#b7412e', fell_a=0.0,
    frost='#ffffff', frost_a=0.0, body_a=0.0, rimdark='#000000', rimdark_a=0.0, refl=0.0, glint=0.0, halo_a=0.0,
    bleed_a=0.06, bleed_k=9.0, rest='#c9ced4', rest_a=0.7, sheen=0.0, round=0.0,
    seed_ink='#1d2329', ink_hue=0.2, ink_density=0.9,
    ring='#c5cad0', ring_amb=1.0, ring_diff=0.0, ring_spec=0.0,
    core_w=0.0014, core_px=(0.9, 1.8), glow_w={'fast': 0.004, 'balanced': 0.0042, 'ultra': 0.0045}, glow_px=(1.6, 3.6),
    seed_glow=dict(halo_tint=(0.20, 0.22, 0.25), core_tint=(0.10, 0.11, 0.13), exposure=0.7), bead_glow=dict(halo_tint=(0.25, 0.12, 0.08), core_tint=(0.20, 0.08, 0.05), exposure=0.9),
    rim_lin=(0.40, 0.56, 1.0), rim_gain=1.0, past_lin=(1.0, 0.60, 0.30), present_lin=(0.40, 0.55, 1.0), haze_lin=(0.42, 0.26, 0.78), haze_gain=1.0, flow=1.0,
    shell_front=2.2, white=0.12, white_ecru=0.3, pulse=1.6, front=1.1, tip=2.0, glow=0.8, rest_lin=(0.55, 0.62, 0.80), rest_glow=0.22, seed_centre=(1.0, 0.92, 0.8), seed_limb=(1.0, 0.55, 0.25),
    brand='Dynasty Loom', brand_sub='Three families, mapped in time',
    css=dict(scene='#f3f4f4', panel='#ffffff', ink='#1a1d21', dim='#5f6670', accent='#b7412e', line='#d9dde1', chip='#f3f4f5',
             shadow='0 1px 2px rgba(20, 24, 28, .06)', radius='4px', blur='0px', status='#5f6670',
             lab_bg='transparent', lab_ink='#2b3036', lab_house='#1a1d21', lab_year='#7d8690', lab_sub='#111417', lab_halo='0 0 2px #fff, 0 0 4px #fff, 0 0 6px #fff',
             vignette='none', ph_bg='#e9ecef', ph_fg='#b9c0c7'),
    labels='Source Sans 3, sentence case, white halo, no box; houses in semibold caps', caption='a white card with a 1 px rule: headline in Source Serif 4, text in Source Sans 3, tabular figures',
    portrait=dict(shape='circle', in0=0.70, in1=0.95, out_ms=300, scale0=1.0, blur=0, leader=1, w=150, h=150, pw=96, ph=96),
    portrait_note='A circle crop with a hairline and a white ring, tied to its life by a 1 px leader line; it appears quickly near the end of the flight (last 25 percent) and leaves in 0.3 s.',
    light='Flat: no light model at all. Colour is category (family) and lightness is descent (deeper = closer).',
    glass='The glass is a single crisp grey circle with the 50-year shells as faint limb rings; no graticule, no reflection, no haze. The armillary is a flat hairline.',
    lines='Hairlines 0.9 to 1.8 px, a 6 percent anti-alias halo, no bloom; the rest of the family drops to light grey when a person is selected.',
    motion='Functional: v3\'s flights unchanged; overlays snap in late and leave fast, so they never compete with the move.',
    chrome='White cards with 1 px rules and 4 px corners, no blur, tabular figures; the caption is a compact chart note with the detail behind a toggle.',
    risks=dict(perf='The cheapest scene with Heritage Glass: analytic lines only, a flat backdrop, no haze or reflections (Confirmed, SwiftShader, relative).',
               legible='Highest: dark text on white, labels with halos; thin 0.9 px lines fade on phones in sunlight (Suspected).',
               truth='The most literal: colour = family, lightness = descent, grey = in-law. Strong, saturated hues could read as ranking between families; they are categorical (Likely).')),
  dict(
    slug='heritage-glass', short='Glass', name='Heritage Glass',
    pitch='The orb as a real crystal heirloom in a quiet studio: frosted glass, silk threads in jewel tones, soft reflections.',
    mood='Product photography of a precious object: a soft grey sweep, a frosted crystal sphere, silk threads inside it.',
    fonts=['Marcellus', 'Source Sans 3'], display='Marcellus', text='Source Sans 3', ui='Source Sans 3',
    swatches=[('Studio light', '#f2f0eb'), ('Studio sweep', '#d4d0c9'), ('Studio floor', '#8c8882'), ('Frost', '#ffffff'), ('Ruby', '#9b1b3b'), ('Topaz', '#b07a1c'),
              ('Emerald', '#17694f'), ('Sapphire', '#24468c'), ('Pewter (in-law)', '#8b8781'), ('Ink', '#23262b')],
    ink=1, ground_top='#d4d0c9', ground_bot='#8c8882', pool='#f2f0eb', pool_k=0.85, pool_w=0.5, mottle=0.0, stars=0.0, grain=0.004,
    dyes={'red': '#9b1b3b', 'gold': '#b07a1c', 'green': '#17694f', 'blue': '#24468c'}, ecru='#8b8781', ecru_word='pewter', dye_l=38.0, chroma=1.15, ink_value=0.88,
    engrave='#4a4f57', outline_a=0.22, graticule=0.0, grat_back=0.0, shell_a=0.08, past='#6c7480', present='#6c7480', fell_c='#ffffff', fell_a=0.0,
    frost='#ffffff', frost_a=0.55, body_a=0.10, rimdark='#2f343c', rimdark_a=0.32, refl=0.35, glint=0.85, halo_a=0.18,
    bleed_a=0.12, bleed_k=8.0, rest='#c9c6c0', rest_a=0.55, sheen=0.22, round=0.28,
    seed_ink='#6e5a2e', ink_hue=0.55, ink_density=0.8,
    ring='#c8ccd2', ring_amb=0.30, ring_diff=0.55, ring_spec=0.9,
    core_w=0.0021, core_px=(1.1, 3.2), glow_w={'fast': 0.0065, 'balanced': 0.007, 'ultra': 0.0075}, glow_px=(2.2, 6.0),
    seed_glow=dict(halo_tint=(0.75, 0.62, 0.35), core_tint=(0.50, 0.40, 0.20), exposure=0.8), bead_glow=dict(halo_tint=(0.60, 0.15, 0.25), core_tint=(0.45, 0.10, 0.18), exposure=0.9),
    rim_lin=(0.40, 0.56, 1.0), rim_gain=1.0, past_lin=(1.0, 0.60, 0.30), present_lin=(0.40, 0.55, 1.0), haze_lin=(0.42, 0.26, 0.78), haze_gain=1.0, flow=1.0,
    shell_front=2.2, white=0.12, white_ecru=0.3, pulse=1.6, front=1.1, tip=2.0, glow=0.8, rest_lin=(0.55, 0.62, 0.80), rest_glow=0.22, seed_centre=(1.0, 0.92, 0.8), seed_limb=(1.0, 0.55, 0.25),
    brand='DYNASTY LOOM', brand_sub='A family heirloom in glass',
    css=dict(scene='#c4c0b9', panel='rgba(255, 255, 255, .58)', ink='#23262b', dim='#575c65', accent='#24468c', line='rgba(255, 255, 255, .75)', chip='rgba(255, 255, 255, .45)',
             shadow='0 12px 32px rgba(40, 38, 34, .16), 0 1px 0 rgba(255,255,255,.8) inset', radius='14px', blur='14px', status='#575c65',
             lab_bg='rgba(255, 255, 255, .62)', lab_ink='#23262b', lab_house='#24468c', lab_year='#575c65', lab_sub='#111317', lab_halo='none',
             vignette='none', ph_bg='#dcdad6', ph_fg='#a9a6a1'),
    labels='Source Sans 3 on frosted pills; houses in Marcellus caps', caption='a frosted glass card (backdrop blur), Marcellus title, Source Sans text',
    portrait=dict(shape='mount', in0=0.55, in1=0.95, out_ms=800, scale0=0.96, blur=6, leader=0, w=180, h=226, pw=112, ph=140),
    portrait_note='A frosted glass mount with a soft shadow; the portrait inside is feathered at the edge. It rises into focus (blur 6 px to 0, scale 96 to 100 percent) with the flight and settles as the camera lands.',
    light='A soft key behind and above (a pool of light on the sweep), a softbox glint on the glass, a darker floor. Ink-mode compositing: the threads are pigment, the glass is frost and reflection.',
    glass='Frosted crystal: milky at grazing angles, clear face-on; a dark refraction band just inside the limb; the sweep reflected at Fresnel; one soft softbox glint; a faint milky body.',
    lines='Silk: 1.1 to 3.2 px threads with a rounded cross-section and an anisotropic sheen from the key (Kajiya-Kay), in ruby, topaz, emerald and sapphire.',
    motion='Gentle: flights unchanged; portraits rise into focus with the camera (blur and scale tied to the flight\'s progress), settle at the stop, and dissolve out over 0.8 s.',
    chrome='Frosted glass cards (14 px backdrop blur, white hairline, soft shadow); pills for families and stops.',
    risks=dict(perf='The scene is as cheap as Editorial (frost and reflection are analytic, the raymarched haze is gone; Confirmed, SwiftShader, relative). The cost moves to the page: backdrop-filter blur on every panel and label costs compositing on phones (Likely).',
               legible='Frost over the threads lowers contrast at the rim; text on frosted glass depends on what is behind it (Likely).',
               truth='Realistic glass and jewel tones can read as precious or authoritative; the object metaphor is decoration, the encodings are unchanged (Likely).')),
]
BY_SLUG = {s['slug']: s for s in STYLES}

PANEL_SOLID = {'museum-atlas': 'rgba(251, 248, 241, .95)', 'documentary-night': 'rgba(12, 16, 23, .88)', 'editorial-clarity': '#ffffff', 'heritage-glass': 'rgba(255, 255, 255, .82)'}
THEME_DIR = 'theme/'   # an alternate theme's hypersphere scenes are published under theme/<slug>/ (the default theme's sit beside the page)


def theme(slug):
    if slug not in BY_SLUG: raise SystemExit('unknown theme %r (themes: %s)' % (slug, ', '.join(BY_SLUG)))
    return BY_SLUG[slug]


def scene_dir(slug):
    """where a theme's hypersphere scenes are published, relative to the page ('' for DEFAULT_THEME)"""
    return '' if slug == DEFAULT_THEME else THEME_DIR + slug + '/'


# ---------------------------------------------------------------- the shaders: one block of constants, spliced into common.glsl at //#include style
def _rgb(h): h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
def _v3g(c): return 'vec3(%.4f, %.4f, %.4f)' % tuple(c)
def _hexv(h): return _v3g(_rgb(h))
def _fl(x): s = '%.5f' % float(x); s = s.rstrip('0'); return s + '0' if s.endswith('.') else s


def style_block(S):
    pool_dir = (0.0, -0.12, 0.99)
    rows = [
        ('float', 'S_INK', _fl(S['ink']), '1: pigment on a light ground (straight alpha, no tone map); 0: light on a dark ground (screen or additive)'),
        ('vec3', 'S_GROUND_TOP', _hexv(S['ground_top']), 'the backdrop sweep (display sRGB)'), ('vec3', 'S_GROUND_BOT', _hexv(S['ground_bot']), ''),
        ('vec3', 'S_POOL', _hexv(S['pool']), 'a soft pool of light behind the opening view'), ('float', 'S_POOL_K', _fl(S['pool_k']), ''), ('float', 'S_POOL_W', _fl(S['pool_w']), 'radians'),
        ('vec3', 'S_POOL_DIR', 'normalize(vec3(%s, %s, %s))' % tuple(_fl(x) for x in pool_dir), ''),
        ('float', 'S_MOTTLE', _fl(S['mottle']), 'large-scale paper or smoke mottling'), ('float', 'S_STARS', _fl(S['stars']), 'dim hashed stars (dark direction only)'),
        ('float', 'S_GRAIN', _fl(S['grain']), 'film or paper grain, display units'),
        ('vec3', 'S_RIM', _v3g(S['rim_lin']), 'screen mode: glass rim (linear)'), ('float', 'S_RIM_GAIN', _fl(S['rim_gain']), ''),
        ('vec3', 'S_PAST_L', _v3g(S['past_lin']), 'screen mode: time shells, warm past to cool present (linear)'), ('vec3', 'S_PRESENT_L', _v3g(S['present_lin']), ''),
        ('vec3', 'S_HAZE', _v3g(S['haze_lin']), 'screen mode: haze (linear)'), ('float', 'S_HAZE_GAIN', _fl(S['haze_gain']), ''), ('float', 'S_FLOW', _fl(S['flow']), ''),
        ('float', 'S_REFL', _fl(S['refl']), 'reflection of the backdrop at Fresnel'), ('float', 'S_GLINT', _fl(S['glint']), 'the key softbox glint'),
        ('float', 'S_SHELL_FRONT', _fl(S['shell_front']), 'screen mode: the 12 s energy front on the shells'),
        ('vec3', 'S_ENGRAVE', _hexv(S['engrave']), 'ink mode: engraving ink (outline, graticule)'), ('float', 'S_OUTLINE_A', _fl(S['outline_a']), ''),
        ('float', 'S_GRATICULE', _fl(S['graticule']), '15 degree meridians and parallels, near side'), ('float', 'S_GRAT_BACK', _fl(S['grat_back']), 'far side'),
        ('float', 'S_SHELL_A', _fl(S['shell_a']), 'ink mode: 50-year shells as limb circles'), ('vec3', 'S_PAST', _hexv(S['past']), ''), ('vec3', 'S_PRESENT', _hexv(S['present']), ''),
        ('vec3', 'S_FROST', _hexv(S['frost']), 'ink mode: frosted glass'), ('float', 'S_FROST_A', _fl(S['frost_a']), ''), ('float', 'S_BODY_A', _fl(S['body_a']), ''),
        ('vec3', 'S_RIMDARK', _hexv(S['rimdark']), 'ink mode: the refraction band inside the limb'), ('float', 'S_RIMDARK_A', _fl(S['rimdark_a']), ''), ('float', 'S_HALO_A', _fl(S['halo_a']), ''),
        ('float', 'S_CHROMA', _fl(S['chroma']), 'fibers: chroma about the luminance'), ('float', 'S_INK_VALUE', _fl(S['ink_value']), ''),
        ('float', 'S_WHITE', _fl(S['white']), 'screen mode: a dyed core\'s mix toward white'), ('float', 'S_WHITE_ECRU', _fl(S['white_ecru']), ''),
        ('float', 'S_PULSE', _fl(S['pulse']), 'screen mode: pulses, the front, the newest years'), ('float', 'S_FRONT', _fl(S['front']), ''), ('float', 'S_TIP', _fl(S['tip']), ''),
        ('float', 'S_VALUE_NORM', _fl(S.get('value_norm', 1.0)), 'screen mode: 1 draws every dye at full value (v3), 0 keeps its own value'),
        ('float', 'S_GLOW', _fl(S['glow']), 'screen mode: the glow pass gain (bloom)'), ('vec3', 'S_REST_L', _v3g(S['rest_lin']), 'screen mode: the rest under a selection'), ('float', 'S_REST_GLOW', _fl(S['rest_glow']), ''),
        ('vec3', 'S_REST', _hexv(S['rest']), 'ink mode: the rest under a selection'), ('float', 'S_REST_A', _fl(S['rest_a']), ''),
        ('float', 'S_BLEED_A', _fl(S['bleed_a']), 'ink mode: the soft edge of a line'), ('float', 'S_BLEED_K', _fl(S['bleed_k']), ''),
        ('float', 'S_SHEEN', _fl(S['sheen']), 'ink mode: silk sheen (Kajiya-Kay) and a rounded cross-section'), ('float', 'S_ROUND', _fl(S['round']), ''),
        ('vec3', 'S_SEED_CENTRE', _v3g(S['seed_centre']), 'screen mode: the seed sun'), ('vec3', 'S_SEED_LIMB', _v3g(S['seed_limb']), ''), ('vec3', 'S_SEED_INK', _hexv(S['seed_ink']), 'ink mode: the seed dot'),
        ('float', 'S_INK_HUE', _fl(S['ink_hue']), 'ink mode: a glow (seed, bead) becomes pigment of this much of its own hue'), ('float', 'S_INK_DENSITY', _fl(S['ink_density']), ''),
        ('float', 'S_RING_AMB', _fl(S['ring_amb']), 'the armillary'), ('float', 'S_RING_DIFF', _fl(S['ring_diff']), ''), ('float', 'S_RING_SPEC', _fl(S['ring_spec']), ''),
    ]
    out = ['// THEME %s (hyper/themes.py, written by build_hypersphere.py --theme %s): look constants; the code below them is shared by every theme.' % (S['name'], S['slug'])]
    for t, n, v, c in rows: out.append('const %s %s = %s;%s' % (t, n, v, ('   // ' + c) if c else ''))
    return '\n'.join(out) + '\n'


# ---------------------------------------------------------------- the page: fonts, constants for the script, and the style sheet
def page_slugs(): return [DEFAULT_THEME] + ([ALT_THEME] if ALT_THEME and ALT_THEME != DEFAULT_THEME else [])


def fonts_href(slugs=None, phone=PHONE_UI):
    fams = []
    for s in (slugs or page_slugs()) + ([phone] if phone else []):
        for f in theme(s)['fonts']:
            if f not in fams: fams.append(f)
    return 'https://fonts.googleapis.com/css2?' + '&amp;'.join('family=%s:%s' % (f.replace(' ', '+'), GOOGLE_FONTS[f]) for f in fams) + '&amp;display=swap'


def look_json(slugs=None, phone=PHONE_UI):
    slugs = slugs or page_slugs(); P = theme(phone)['portrait'] if phone else None
    themes = {s: dict(name=theme(s)['name'], short=theme(s)['short'], brand=theme(s)['brand'], brand_sub=theme(s)['brand_sub'], ink=bool(theme(s)['ink']), ecru=theme(s)['ecru_word'], dir=scene_dir(s), portrait=theme(s)['portrait'])
              for s in slugs}
    return json.dumps(dict(default=slugs[0], order=slugs, phone=phone, themes=themes, phone_portrait=dict(P, w=P['pw'], h=P['ph']) if P else None), sort_keys=True, separators=(',', ':'))


def _fam(n): return "'%s', %s" % (n, SERIF_FB if n in ('EB Garamond', 'Cormorant Garamond', 'Source Serif 4', 'Marcellus') else SANS_FB)


def _vars(S):
    c, P = S['css'], S['portrait']
    v = dict(scene=c['scene'], panel=c['panel'], ink=c['ink'], dim=c['dim'], accent=c['accent'], line=c['line'], chip=c['chip'], shadow=c['shadow'], radius=c['radius'],
             blur=c['blur'], status=c['status'], **{'lab-bg': c['lab_bg'], 'lab-ink': c['lab_ink'], 'lab-house': c['lab_house'], 'lab-year': c['lab_year'], 'lab-sub': c['lab_sub'],
             'lab-halo': c['lab_halo'], 'ph-bg': c['ph_bg'], 'ph-fg': c['ph_fg'], 'panel-solid': PANEL_SOLID[S['slug']]}, vignette=c['vignette'],
             display=_fam(S['display']), text=_fam(S['text']), ui=_fam(S['ui']), pw='%dpx' % P['w'], gold=c['accent'], red=c['accent'], serif=_fam(S['text']), mono=_fam(S['ui']))
    v['color-scheme'] = 'light' if S['ink'] else 'dark'
    return '; '.join('%s%s: %s' % ('' if k == 'color-scheme' else '--', k, val) for k, val in v.items())


BASE_CSS = '''  /* ---- the v2 look (hyper/themes.py via merge_views.py): one style sheet for both views; a theme is :root[data-look="<slug>"] */
  * { box-sizing: border-box; }
  html, body { margin: 0; height: 100%; overflow: hidden; }
  body { background: var(--scene); color: var(--ink); font: 15px/1.45 var(--text); }
  x3d-canvas { position: fixed; inset: 0; width: 100vw; height: 100vh; height: 100dvh; display: block; background: var(--scene); }
  #vignette { position: fixed; inset: 0; pointer-events: none; background: var(--vignette); }
  #grain { position: fixed; inset: 0; width: 100%; height: 100%; pointer-events: none; display: none; }
  .panel { background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow); backdrop-filter: blur(var(--blur)); -webkit-backdrop-filter: blur(var(--blur)); }
  header { position: fixed; top: calc(12px + env(safe-area-inset-top, 0px)); left: 16px; right: 16px; display: flex; flex-wrap: wrap; gap: 4px 14px; align-items: center; padding: 8px 14px; z-index: 5; }
  header .brand { font: 600 17px/1.2 var(--display); color: var(--ink); white-space: nowrap; letter-spacing: 0; }
  header .brand small { font: 400 13px/1.2 var(--text); color: var(--dim); margin-left: 10px; letter-spacing: 0; text-transform: none; }
  header .sub { font: 12.5px/1.3 var(--ui); color: var(--dim); }
  #fams { display: flex; gap: 4px; margin-left: auto; flex-wrap: wrap; }
  button, select, .btn { font: 13px/1 var(--ui); color: var(--ink); background: var(--chip); border: 1px solid var(--line); border-radius: var(--radius); padding: 6px 10px; cursor: pointer; min-height: 30px; }
  select { padding: 4px 6px; }
  button:hover, button.on { border-color: var(--accent); color: var(--accent); }
  button:focus-visible, select:focus-visible, input:focus-visible, a:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  #views button.on { border-color: var(--accent); color: var(--accent); }
  #look-t { min-height: 26px; padding: 3px 8px; font-size: 12px; opacity: .8; }
  #look-t[aria-pressed="true"] { opacity: 1; }
  #rail { position: fixed; right: 16px; top: calc(var(--header-h, 64px) + 10px); display: flex; flex-direction: column; gap: 4px; align-items: flex-end; max-height: calc(100vh - var(--header-h, 64px) - 210px); overflow-y: auto; z-index: 2; }
  #rail button { display: flex; gap: 6px; align-items: center; padding: 3px 8px; min-height: 24px; font-size: 12px; background: var(--panel); font-variant-numeric: tabular-nums; }
  #rail button .t { display: none; }
  #rail button.on .t, #rail button:hover .t { display: inline; }
  #cap { position: fixed; left: 16px; right: auto; bottom: calc(14px + env(safe-area-inset-bottom, 0px)); width: min(780px, calc(100vw - 32px)); padding: 10px 16px; max-height: 20vh; overflow: hidden; z-index: 4; }
  #cap.open { max-height: min(62vh, 560px); overflow-y: auto; }
  #cap .head { display: flex; flex-wrap: wrap; gap: 2px 10px; align-items: baseline; font: 13px/1.3 var(--ui); color: var(--dim); font-variant-numeric: lining-nums tabular-nums; }
  #cap .head b { font: 600 19px/1.2 var(--display); color: var(--ink); }
  #shotchip { font: 11px/1 var(--ui); padding: 3px 6px; border: 1px solid var(--line); border-radius: var(--radius); color: var(--dim); display: none; }
  #cap.open #shotchip { display: inline-block; }
  #more-t { margin-left: auto; background: none; border: 0; padding: 2px 0; min-height: 0; color: var(--accent); text-decoration: underline; text-underline-offset: 3px; }
  #narr { margin: 4px 0 0; font: 15.5px/1.42 var(--text); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
  #cap.open #narr { display: block; }
  #more { display: none; }
  #cap.open #more { display: block; }
  #comp, #scale { font: 13px/1.45 var(--ui); color: var(--dim); margin: 6px 0 0; }
  #scale b { color: var(--ink); font-weight: 600; }
  .g { display: inline-block; font: 600 10px/1 var(--ui); padding: 2px 4px; margin-left: 3px; border-radius: 3px; border: 1px solid var(--line); color: var(--dim); vertical-align: 1px; }
  .ctl { display: flex; flex-wrap: wrap; gap: 6px 10px; align-items: center; margin-top: 8px; }
  .ctl label { font: 13px/1 var(--ui); color: var(--dim); display: flex; gap: 6px; align-items: center; }
  .ctl input[type=range] { width: 160px; accent-color: var(--accent); }
  output { font: 13px/1 var(--ui); font-variant-numeric: tabular-nums; }
  #tiers { display: inline-flex; gap: 4px; align-items: center; }
  #fps, #where { font: 12px/1 var(--ui); color: var(--dim); font-variant-numeric: tabular-nums; }
  .keys { font: 12px/1.3 var(--ui); color: var(--dim); }
  #card { position: fixed; z-index: 6; top: calc(var(--header-h, 64px) + 10px); right: 96px; width: min(380px, calc(100vw - 32px)); max-height: calc(100vh - var(--header-h, 64px) - 210px); overflow-y: auto; padding: 14px 16px; }
  #card h2 { margin: 0; font: 600 20px/1.2 var(--display); padding-right: 28px; }
  #card .yrs { font: 13px/1.4 var(--ui); color: var(--dim); margin-top: 3px; font-variant-numeric: lining-nums; }
  #card h3 { margin: 12px 0 3px; font: 600 11px/1.2 var(--ui); letter-spacing: .12em; text-transform: uppercase; color: var(--dim); }
  #card p, #card li { margin: 3px 0; font-size: 14px; }
  #card ul { margin: 2px 0; padding-left: 18px; font: 12.5px/1.4 var(--ui); }
  #card a { color: var(--accent); word-break: break-word; }
  #card .x { position: absolute; top: 8px; right: 8px; padding: 3px 8px; }
  #card .chead { display: flex; gap: 12px; align-items: flex-start; }
  #card .cthumb { flex: 0 0 76px; margin: 0; }
  #card .cthumb .frame { width: 76px; }
  #card .cthumb figcaption { font: italic 10.5px/1.25 var(--ui); color: var(--dim); margin-top: 4px; }
  header .sub .sw { display: inline-block; width: 9px; height: 9px; vertical-align: -1px; border: 0; }
  header .sub .ramp { display: inline-flex; gap: 1px; margin: 0 3px 0 0; border-radius: 2px; overflow: hidden; vertical-align: -1px; }
  header .sub > .sw { border-radius: 2px; margin: 0 2px; }
  #card .sw { display: inline-block; width: 10px; height: 10px; border-radius: 2px; vertical-align: -1px; margin-right: 4px; border: 1px solid var(--line); }
  #tag { position: fixed; z-index: 7; pointer-events: none; padding: 4px 8px; font: 13px/1.2 var(--ui); transform: translate(12px, -130%); white-space: nowrap; background: var(--panel-solid); }
  #toast { position: fixed; left: 50%; top: calc(var(--header-h, 64px) + 8px); transform: translateX(-50%); padding: 6px 12px; font: 13px/1.3 var(--ui); opacity: 0; transition: opacity .25s; pointer-events: none; z-index: 8; background: var(--panel-solid); }
  #toast.on { opacity: 1; }
  #status { position: fixed; left: 50%; top: 42%; transform: translate(-50%, -50%); font: 14px/1.4 var(--ui); color: var(--status); text-align: center; padding: 0 16px; }
  #labels { position: fixed; inset: 0; pointer-events: none; overflow: hidden; }
  .lab { position: absolute; left: 0; top: 0; white-space: nowrap; font: 13px/1.25 var(--ui); padding: 2px 6px; border-radius: var(--radius); background: var(--lab-bg); color: var(--lab-ink); text-shadow: var(--lab-halo); will-change: transform; }
  .lab.house { color: var(--lab-house); letter-spacing: .1em; font-size: 12px; }
  .lab.year { color: var(--lab-year); font-size: 12px; font-variant-numeric: tabular-nums; }
  .lab.subject { color: var(--lab-sub); font-weight: 600; }
  .lab[hidden] { display: none; }
  [hidden] { display: none !important; }
  /* the portrait overlay: camera-anchored, its opacity, scale and blur interpolated from the flight's progress; the label sits under it */
  #portrait { position: fixed; left: 0; top: 0; z-index: 3; margin: 0; width: var(--pw); pointer-events: none; opacity: 0; visibility: hidden; transform-origin: 50% 60%; will-change: transform, opacity; }
  #portrait .frame { pointer-events: auto; cursor: pointer; }
  .frame { position: relative; }
  .ph { position: relative; width: 100%; aspect-ratio: 4 / 5; overflow: hidden; }
  .ph img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; display: block; transform-origin: 50% 42%; }
  .ph .mono { position: absolute; inset: 14% 10%; border-radius: 50%; display: flex; align-items: center; justify-content: center; font: 500 30px/1 var(--display); letter-spacing: .04em; background: var(--ph-bg); color: var(--ink); }
  #portrait figcaption { margin-top: 8px; font: 13px/1.3 var(--ui); color: var(--ink); text-shadow: var(--lab-halo); }
  #portrait figcaption b { display: block; font: 600 15px/1.25 var(--display); }
  #portrait figcaption span { display: block; color: var(--dim); font-variant-numeric: lining-nums; }
  #portrait figcaption .plab { font: italic 11.5px/1.3 var(--ui); color: var(--dim); margin-top: 2px; letter-spacing: 0; text-transform: none; }
  #lead { position: fixed; left: 0; top: 0; height: 1px; background: var(--ink); transform-origin: 0 50%; pointer-events: none; opacity: 0; z-index: 2; }
  #lead::before { content: ''; position: absolute; left: -3px; top: -3px; width: 7px; height: 7px; border-radius: 50%; background: var(--ink); }
  body:has(#card:not([hidden])) #rail .t { display: none; }
  body[data-ui="none"] header, body[data-ui="none"] #rail, body[data-ui="none"] #cap, body[data-ui="none"] #card, body[data-ui="none"] #tag, body[data-ui="none"] #labels, body[data-ui="none"] #portrait, body[data-ui="none"] #lead { display: none !important; }
  /* the loom view keeps v3's dark scene, so its chrome sits on solid panels in every theme */
  body[data-view="loom"] { background: #0f0d0c; }
  body[data-view="loom"] x3d-canvas { background: #0f0d0c; }
  body[data-view="loom"] header.panel, body[data-view="loom"] #cap.panel, body[data-view="loom"] #rail button { background: var(--panel-solid); }
  body[data-view="loom"] #status { color: #c9bfae; }
'''

EXTRA_CSS = {
 'museum-atlas': '''  /* Museum Atlas: a printed wall label beside an engraved globe */
  header.panel { background: transparent; border: 0; box-shadow: none; border-bottom: 1px solid var(--line); border-radius: 0; padding: 6px 2px 8px; }
  header .brand { font: 500 22px/1.1 var(--display); font-variant: small-caps; letter-spacing: .06em; }
  header .brand small { font-style: italic; font-size: 15px; }
  button { background: transparent; border: 0; border-bottom: 1px solid transparent; border-radius: 0; font: 15px/1 var(--ui); padding: 5px 4px; }
  button.on, button:hover { border-bottom-color: var(--accent); }
  #fams button, #views button { font-variant: small-caps; letter-spacing: .04em; font-size: 16px; }
  #rail button { background: transparent; font-size: 14px; }
  #cap.panel { border: 0; border-top: 2px solid var(--ink); box-shadow: 0 10px 28px rgba(70, 50, 30, .10); }
  #cap .head b { font-size: 22px; font-weight: 500; }
  #narr { font-size: 17px; }
  .lab { font-size: 14.5px; font-variant: small-caps; letter-spacing: .03em; padding: 0 2px; }
  .lab.house { font-size: 14px; letter-spacing: .16em; }
  .lab.subject { font-style: italic; font-variant: normal; font-size: 16px; }
  #portrait .frame { border: 1px solid rgba(91, 74, 58, .55); border-radius: 50%; padding: 5px; background: rgba(251, 248, 241, .55); }
  #portrait .ph { border-radius: 50%; -webkit-mask-image: radial-gradient(ellipse 50% 50% at 50% 50%, #000 66%, transparent 100%); mask-image: radial-gradient(ellipse 50% 50% at 50% 50%, #000 66%, transparent 100%); }
  #portrait figcaption { text-align: center; font-style: italic; }
  #portrait figcaption b { font-style: normal; font-variant: small-caps; letter-spacing: .04em; font-size: 17px; }
  .cthumb .frame { border: 1px solid rgba(91, 74, 58, .5); border-radius: 50%; padding: 3px; } .cthumb .ph { border-radius: 50%; }
  body[data-view="loom"] header.panel { border: 1px solid var(--line); border-radius: var(--radius); padding: 6px 12px 8px; background: var(--panel-solid); }   /* ink on the loom's dark ground needs its paper */
  body[data-view="loom"] #rail button { background: var(--panel-solid); padding: 2px 8px; border-radius: var(--radius); }
''',
 'documentary-night': '''  /* Documentary Night: a lower third and a title card in a dark room */
  #grain { display: block; opacity: .07; mix-blend-mode: overlay; }
  header.panel { background: transparent; border: 0; box-shadow: none; padding: 6px 2px; }
  header .brand { font: 600 15px/1.2 var(--display); letter-spacing: .34em; }
  header .brand small { font: italic 500 16px/1.2 var(--display); letter-spacing: .02em; }
  button { background: transparent; border-color: rgba(216, 191, 138, .32); border-radius: 2px; font: 500 12px/1 var(--ui); letter-spacing: .08em; text-transform: uppercase; }
  #rail button { background: rgba(10, 13, 19, .35); border-color: transparent; }
  #rail button.on { border-color: var(--accent); }
  #cap.panel { left: 0; bottom: 0; width: 100%; max-height: 20vh; border: 0; border-radius: 0; box-shadow: none; padding: 30px max(28px, env(safe-area-inset-left, 0px)) 16px;
    background: linear-gradient(to top, rgba(7, 9, 14, .86) 0%, rgba(7, 9, 14, .62) 62%, rgba(7, 9, 14, 0) 100%); }
  #cap.panel.open { max-height: min(62vh, 560px); background: rgba(9, 12, 18, .9); }
  #cap .head, #narr, #cap .ctl, #more { max-width: 820px; }
  #cap .head b { font: 600 21px/1.15 var(--display); letter-spacing: .14em; text-transform: uppercase; }
  #narr { font: 15.5px/1.5 var(--text); color: #ddd5c6; }
  #card.panel, #tag.panel, #toast.panel { background: rgba(12, 16, 23, .86); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); box-shadow: 0 16px 40px rgba(0, 0, 0, .45); }
  .lab { font: 500 11px/1.25 var(--ui); letter-spacing: .14em; text-transform: uppercase; padding: 0 2px; }
  .lab.subject { font: italic 600 17px/1.2 var(--display); letter-spacing: .02em; text-transform: none; }
  .lab.year { letter-spacing: .06em; }
  #portrait .ph { -webkit-mask-image: linear-gradient(to right, transparent, #000 18px, #000 calc(100% - 18px), transparent), linear-gradient(to bottom, transparent, #000 18px, #000 calc(100% - 18px), transparent);
    -webkit-mask-composite: source-in; mask-image: linear-gradient(to right, transparent, #000 18px, #000 calc(100% - 18px), transparent), linear-gradient(to bottom, transparent, #000 18px, #000 calc(100% - 18px), transparent); mask-composite: intersect; }
  #portrait .ph img { filter: sepia(.25) saturate(.85); }
  #portrait figcaption { border-left: 2px solid var(--accent); padding-left: 10px; }
  #portrait figcaption b { font: italic 600 19px/1.15 var(--display); }
  #portrait figcaption span { font: 500 11px/1.3 var(--ui); letter-spacing: .14em; text-transform: uppercase; }
  body[data-view="loom"] #cap.panel { background: rgba(9, 12, 18, .9); }
''',
 'editorial-clarity': '''  /* Editorial Clarity: a newspaper's interactive graphic */
  header.panel { left: 0; right: 0; top: 0; border-radius: 0; border-width: 0 0 1px; padding: 10px 20px; box-shadow: none; }
  header .brand { font: 600 19px/1.2 var(--display); }
  #fams button { border-radius: 999px; }
  button.on { background: var(--ink); color: #fff; border-color: var(--ink); }
  #rail button { border-radius: 999px; }
  #rail button.on { background: var(--ink); color: #fff; border-color: var(--ink); }
  #cap .head b { font: 600 19px/1.2 var(--display); }
  #capn { font-weight: 600; color: var(--accent); text-transform: uppercase; letter-spacing: .06em; font-size: 12px; }
  #narr { font: 16px/1.42 var(--text); color: #2b3036; }
  .lab { font-size: 13px; padding: 0 2px; }
  .lab.house { font-weight: 600; letter-spacing: .08em; text-transform: uppercase; font-size: 11.5px; }
  .lab.subject { font-weight: 600; font-size: 14px; }
  #portrait .frame { width: 104px; padding: 3px; background: #fff; border-radius: 50%; box-shadow: 0 0 0 1px #c5cad0, 0 2px 8px rgba(20, 24, 28, .12); }
  #portrait .ph { aspect-ratio: 1; border-radius: 50%; }
  #portrait figcaption { margin-top: 6px; } #portrait figcaption b { font: 600 14px/1.25 var(--ui); }
  #lead { background: #2b3036; } #lead::before { background: #2b3036; }
  .cthumb .frame { border-radius: 50%; box-shadow: 0 0 0 1px #c5cad0; overflow: hidden; } .cthumb .ph { aspect-ratio: 1; }
''',
 'heritage-glass': '''  /* Heritage Glass: a crystal heirloom in a studio, frosted cards */
  header .brand { font: 400 16px/1.2 var(--display); letter-spacing: .24em; }
  header .brand small { font-family: var(--ui); }
  header.panel { border-radius: 999px; padding: 7px 10px 7px 20px; }
  #fams button, #rail button, .ctl button { border-radius: 999px; }
  button { background: rgba(255, 255, 255, .5); }
  button.on { background: rgba(36, 70, 140, .1); }
  #cap .head b { font: 400 21px/1.2 var(--display); letter-spacing: .05em; }
  .lab { font-size: 12.5px; border-radius: 999px; padding: 2px 9px; backdrop-filter: blur(6px); -webkit-backdrop-filter: blur(6px); box-shadow: 0 2px 8px rgba(40, 38, 34, .10); }
  .lab.house { font: 400 12px/1.25 var(--display); letter-spacing: .14em; }
  #portrait .frame { padding: 10px; border-radius: 16px; background: rgba(255, 255, 255, .5); border: 1px solid rgba(255, 255, 255, .85); box-shadow: 0 14px 34px rgba(40, 38, 34, .18); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); }
  #portrait .ph { border-radius: 10px; -webkit-mask-image: radial-gradient(ellipse 62% 60% at 50% 46%, #000 70%, transparent 100%); mask-image: radial-gradient(ellipse 62% 60% at 50% 46%, #000 70%, transparent 100%); }
  #portrait figcaption { padding: 0 4px; } #portrait figcaption b { font: 400 16px/1.25 var(--display); letter-spacing: .04em; }
  .cthumb .frame { padding: 4px; border-radius: 10px; background: rgba(255, 255, 255, .6); } .cthumb .ph { border-radius: 7px; }
''',
}

PHONE_CSS = '''  /* phones: the %(name)s interface (layout and type only; the colours stay the theme's) */
  @media (max-width: 720px) {
    :root[data-look] { --display: %(display)s; --text: %(text)s; --ui: %(ui)s; --serif: %(text)s; --mono: %(ui)s; --pw: %(pw)dpx; }
    :root[data-look] header.panel { left: 0; right: 0; top: 0; border-radius: 0; border-width: 0 0 1px; border-style: solid; border-color: var(--line); padding: calc(8px + env(safe-area-inset-top, 0px)) 16px 8px; gap: 4px 8px; box-shadow: none; background: var(--panel-solid); }
    :root[data-look] header .brand { font: 600 17px/1.2 var(--display); letter-spacing: 0; font-variant: normal; text-transform: none; }
    :root[data-look] header .sub, :root[data-look] header .brand small { display: none; }
    :root[data-look] button, :root[data-look] #fams button, :root[data-look] #views button { font: 13px/1 var(--ui); letter-spacing: 0; text-transform: none; font-variant: normal; border: 1px solid var(--line); border-radius: 999px; padding: 5px 9px; min-height: 30px; }
    :root[data-look] #more-t { border: 0; padding: 2px 0; min-height: 0; }
    :root[data-look] #rail { display: none; }
    :root[data-look] #cap.panel { left: 16px; right: 16px; width: auto; bottom: calc(10px + env(safe-area-inset-bottom, 0px)); padding: 8px 12px; max-height: 24vh; border: 1px solid var(--line); border-radius: 4px; background: var(--panel-solid); }
    :root[data-look] #cap.panel.open { max-height: 62vh; }
    :root[data-look] #cap .head b { font: 600 17px/1.2 var(--display); letter-spacing: 0; text-transform: none; }
    :root[data-look] #narr { font: 14.5px/1.42 var(--text); -webkit-line-clamp: 3; }
    :root[data-look] .keys, :root[data-look] #fps { display: none; }
    :root[data-look] .ctl { margin-top: 6px; }
    :root[data-look] .ctl input[type=range] { width: 110px; }
    :root[data-look] #card { top: auto; right: 16px; left: 16px; width: auto; bottom: calc(10px + env(safe-area-inset-bottom, 0px)); max-height: 58vh; z-index: 9; border-radius: 4px; }
    :root[data-look] .lab { font: 13px/1.25 var(--ui); letter-spacing: 0; text-transform: none; font-variant: normal; padding: 0 2px; }
    :root[data-look] .lab.house { font-weight: 600; letter-spacing: .08em; text-transform: uppercase; font-size: 11.5px; }
    :root[data-look] .lab.subject { font-weight: 600; font-style: normal; font-size: 14px; }
    :root[data-look] #portrait .frame { width: %(pw)dpx; padding: 3px; border: 0; border-radius: 50%%; background: var(--panel-solid); box-shadow: 0 0 0 1px var(--line), 0 2px 8px rgba(20, 24, 28, .12); backdrop-filter: none; }
    :root[data-look] #portrait .ph { aspect-ratio: 1; border-radius: 50%%; -webkit-mask-image: radial-gradient(circle at 50%% 46%%, #000 58%%, transparent 71%%); mask-image: radial-gradient(circle at 50%% 46%%, #000 58%%, transparent 71%%); -webkit-mask-composite: source-over; mask-composite: add; }
    :root[data-look] #portrait figcaption { margin-top: 6px; border: 0; padding: 0; text-align: left; font: 12px/1.3 var(--ui); }
    :root[data-look] #portrait figcaption b { font: 600 13.5px/1.25 var(--ui); font-style: normal; font-variant: normal; letter-spacing: 0; text-transform: none; }
    :root[data-look] #portrait figcaption span { font: 11.5px/1.3 var(--ui); letter-spacing: 0; text-transform: none; }
  }
'''


def _prefix(css, pre):
    """prefix every selector of a flat rule list (one level of @media allowed) with pre"""
    out = []
    for line in css.split('\n'):
        s = line.strip()
        if not s or s.startswith('/*') or s.startswith('@') or s == '}' or '{' not in s or s.startswith('background:') or s.startswith('-webkit-mask-composite'):
            out.append(line); continue
        sel, rest = line.split('{', 1)
        ind = sel[:len(sel) - len(sel.lstrip())]
        parts = []   # several rules on one line: 'a { x } b { y }'
        chunk = line.strip()
        while chunk:
            i = chunk.find('{'); j = chunk.find('}', i)
            if i < 0: parts.append(chunk); break
            sels = ', '.join(pre + ' ' + x.strip() if not x.strip().startswith(':root') else x.strip().replace(':root', pre, 1) for x in chunk[:i].split(','))
            parts.append(sels + ' ' + chunk[i:j + 1] if j >= 0 else sels + ' ' + chunk[i:])
            chunk = chunk[j + 1:].strip() if j >= 0 else ''
        out.append(ind + ' '.join(parts))
    return '\n'.join(out)


def page_css(slugs=None, phone=PHONE_UI):
    slugs = slugs or page_slugs()
    out = ['  :root, :root[data-look="%s"] { %s; }' % (slugs[0], _vars(theme(slugs[0])))]
    out += ['  :root[data-look="%s"] { %s; }' % (s, _vars(theme(s))) for s in slugs[1:]]
    out.append(BASE_CSS)
    for s in slugs:
        out.append(_prefix(EXTRA_CSS[s], ':root[data-look="%s"]' % s))
        if theme(s)['ink']: out.append('  :root[data-look="%s"] #poster { display: none !important; }   /* the loading still is a dark render: ink themes load on their own ground */\n' % s)
    if phone:
        P = theme(phone)
        out.append(PHONE_CSS % dict(name=P['name'], display=_fam(P['display']), text=_fam(P['text']), ui=_fam(P['ui']), pw=P['portrait']['pw']))
    return '\n'.join(out)


FONTS_MARK, CSS_MARK, LOOK_MARK = '<!--@FONTS@-->', '/*@THEME_CSS@*/', '/*@LOOK@*/null'


def fonts_link(slugs=None, phone=PHONE_UI):
    return '<link rel="stylesheet" href="%s">' % fonts_href(slugs, phone)


def fill_page(page, slugs=None, phone=PHONE_UI):
    """the page source carries three marks; a build fills them for the themes it ships (each mark must occur once)"""
    for mark, val in ((FONTS_MARK, fonts_link(slugs, phone)), (CSS_MARK, page_css(slugs, phone)), (LOOK_MARK, look_json(slugs, phone))):
        n = page.count(mark)
        if n != 1 and not (mark == LOOK_MARK and n >= 1): raise SystemExit('page: mark %s occurs %d times' % (mark, n))   # the look may be read in two scripts
        page = page.replace(mark, val)
    return page
