# 07 · Narrative, experience and UX: the cloth on the loom

Analyst 7 of 7 (narrative, experience, UX). Grades follow x3d.onto:

| Grade | Meaning |
|---|---|
| **C** | checked this session in a source I opened (list at the end) |
| **L** | one secondary or quoted source |
| **S** | from memory, unchecked |
| **⚑** | contested or legend |
| **∑** | computed from the family's links |
| **≈** | my interpretation |

Sketches are in `proto/ux/`, built from real dates with schematic positions, each with a PNG preview: `01-cloth.svg`, `04-five-arrows.svg` and `06-doubles-back.svg`.

## 0. Verdict

Make the "Cosmos" a vertical tapestry loom: time runs up, west to east runs across, latitude gives depth. Plotted this way, the family weaves itself:
- **Warp.** After 1821 the sons stay in their houses, so their lines run straight up.
- **Weft.** Close marriages mostly move a bride across Europe in a single year.
- **The red returns.** Bride and groom share Mayer and Gutle, so the founders' dye comes back in their children. This is pedigree collapse, made visible.

The dye is red because Rothschild means "red shield". The narrator is the shuttle, and it carries only thread it was given.

## 1. The metaphor, made structural

| Loom | In this family | On screen |
|---|---|---|
| Warp | a life, where it was lived | an upright thread that bends only when the person moves |
| Weft (pick) | a marriage that moves someone between houses | a level thread at the wedding year, **doubled** if the couple share founders |
| Five arrows | four sons leave Frankfurt 1798–1821; one stays | four threads fan out on true bearings; Amschel's arrow points up the time axis |
| Dye | share of descent from Mayer and Gutle | madder red at 1, undyed ecru for in-laws; a child averages its parents |
| The red returning | close marriage | Alphonse 3/4 red where an out-marrying line is 1/2; Walter 1/2 where it is 1/8 (∑) |
| Selvedge | the edge of the dataset | in-laws enter there; Mayer's five daughters leave there, tagged *not in this dataset* |
| Fell | the chosen year | the time scrubber: a glowing plane, with unwoven cloth above it |
| Shuttle | narrator and camera | its path stays drawn as a silver thread, showing what the story skipped |

```
2007 ┤  ┆    ┆        ┆        ┆      ┆      above the fell: unwoven
1877 ┼━━┿━━━━┿━━━━━━━━┿━━━━━━━━┿━━━━━━┿━━   FELL ⇕  (the time scrubber)
1867 ┤  ◆════╪════════╡        │      │     Emma, Frankfurt → London  (close: doubled)
1836 ┤  ◆════╪════════╪════════╡      │     Charlotte, Naples → London; Nathan tied off in Frankfurt
1824 ┤  │    ◆════════╪════════╪══════╡     Betty, Vienna → Paris  (uncle and niece)
1821 ┤  ╲    ╲        ┃        ╱      ╱     four arrows leave; Amschel's ┃ rises
1770 ┤                ●═◆  Mayer + Gutle, Judengasse No. 148
       LON  PAR      FRA      NAP    VIE
```

**Why it holds.**
1. **The pattern comes from the data.** Betty crosses Vienna→Paris in 1824 and Charlotte Naples→London in 1836 (C), and four more brides make the same move (L/S). Ferguson counts 15 close marriages among the family's 21 marriages of the nineteenth century (L, quoted by Davidoff).
2. **The family began in cloth.** Nathan went to Manchester in 1798 to trade in textiles (C).
3. **It fixes a bug.** The app lays people out by `generation`, but under close marriage generation depends on the path. The data puts Alphonse in generation 3 and his full brother Edmond in 4, and puts Betty, Mayer's granddaughter, in 2. The loom places people by year; generation becomes a hover label ("3 steps from Mayer via James, 4 via Betty").
4. **It is the user's own word.** The Gobbler's world lives in a Transform named `Loom`, with shuttles crossing it.

**Alternatives.**

| Form | Why not |
|---|---|
| The current orb | beautiful but says nothing: latitude-by-generation breaks, half the data faces away, time is unreadable |
| A tree | cannot draw a cousin marriage, which is a loop |
| A river or Sankey | cannot split and rejoin itself |
| A subway map | loses the crossings that matter |
| A feather | is a tree too; it makes a good door (§4) |

**Four rules.**
1. **Time is the coordinate; generation is a label.**
2. **Red, not gold.**
   - Gold stays as the frame and UI.
   - A gold family line would echo the "Rothschild gold" caricature.
   - The family name comes from the house *zum Roten Schild*, "at the red shield" (C).
3. **No pinboard.**
   - Conspiracy content about this family looks like red string running from one Jewish family to every bank and government.
   - Only kinship is woven. Anything else (a barony, a loan) is one dated, sourced stitch shown in context, and there are no "influence" edges.
4. **No invented faces.**
   - Use Commons portraits with artist, date and licence (Ingres's Betty, 1841–48, C). With none, show a blank bead labelled *no likeness in the ledger*.
   - Today Mayer's and Gutle's images are random picsum photos, and the panel offers to generate a "photorealistic 19th century oil painting" of anyone.

## 2. The experience

**Tour: 12 stops, about 3.5 minutes with voice.** A short cut uses stops 1, 4, 6, 7, 8 and 12. Today's tour has 5 stops, all men, 8 seconds each, and its titles never reach the screen (`App.tsx` reads only `stop.id`).

| # | Stop · frame | Narration draft |
|---|---|---|
| 1 | **Cloth** · front view, fell at today; a ghost loom fades in; a beater wave climbs | "Two and a half centuries of one family, woven from the bottom up. Each upright thread is a life; each crossing, a marriage. Where the cloth folds back on itself, the red returns." |
| 2 | **Judengasse** · bottom of the Frankfurt column; the first thread starts frayed, at two years | "Mayer Amschel Rothschild is born in Frankfurt's Jewish ghetto in 1744, or 1743; the records differ (C ⚑). The name comes from an older family house, *zum Roten Schild*. A coin dealer, he becomes court factor to Crown Prince Wilhelm of Hesse in 1769 (C)." |
| 3 | **No. 148** · Gutle's thread never moves in 96 years; ten threads spring 1771–92; five fade out at the selvedge | "Gutle Schnapper marries Mayer in 1770 and raises ten children at No. 148. Her sons grow rich and urge her to move; she refuses (C). Five of the ten are daughters, and this dataset leaves them out." A hollow bead hangs beside her: the war quotation, *attributed* (S). |
| 4 | **Five Arrows** · seen from above Frankfurt: true bearings and distances (London 287.5°, 638 km; Paris 255.5°, 478 km; Vienna 107.8°, 598 km; Naples 155.0°, 1,117 km; ∑) | "Four sons leave; one stays. Nathan goes to Manchester in 1798, then London; James to Paris (S: 1811); Salomon to Vienna; Carl to Naples after the Austrian occupation of 1821 (C). In 1822 the emperor makes all five barons: five arrows in a clenched fist, *Concordia, Integritas, Industria* (C)." |
| 5 | **Waterloo, told and recorded** · a dashed thread at 1815 hangs beside Nathan's, not woven in, and unravels at a touch | "The cloth's most famous false thread: that Nathan heard of Waterloo first and made a fortune. It traces to an 1846 pamphlet signed 'Satan'; one historian calls it an antisemitic slur (C ⚑). The record: he arranged money for Wellington's troops, and Ferguson argues peace cost the brothers more than it earned (C)." |
| 6 | **The weft doubles back** · the 1824 pick, doubled; children's threads 3/4 red; dye gauge | "In 1824 James marries Betty, his brother Salomon's daughter; she is nineteen (C). Their five children draw three quarters of their descent from Mayer and Gutle, where an out-marrying line draws half (∑). Ingres finishes her portrait in 1848 (C)." |
| 7 | **Frankfurt, summer 1836** · at one height, Charlotte's pick arrives as Nathan's thread swings back from London and ties off | "Lionel marries his first cousin Charlotte, Carl's daughter, two days after her seventeenth birthday. Nathan has come to Frankfurt for the wedding; he falls ill and dies there on 28 July (C). One city, one summer: a pick woven, a thread tied off." |
| 8 | **The close weave** · pull back over the dense picks, 1824 to the 1870s; then threads enter from the selvedge | "Of twenty-one Rothschild marriages that century, fifteen were close (L). Watch who moves: the sons stay, and the brides cross Europe (≈). Walter, born in 1868 to double first cousins, still draws half his descent from the founders (∑). By 1900 almost all marry out (C)." |
| 9 | **Seats** · two gold beads on the London column | "Lionel is elected for the City of London in 1847 and re-elected three times, but takes his seat only in 1858, once each House may set its own oath. In 1885 his son Natty becomes the first Jewish peer (C)." |
| 10 | **Naturalists, and a gap** · beads turn green; Charles's thread is dashed | "Walter opens his museum at Tring in 1892; the Balfour Declaration of 1917 is a letter to him. Charles names the plague flea in 1903 and founds a society for nature reserves in 1912 (C). The data names Charles as Victor's father but omits him: the gap is in the data, not the family." |
| 11 | **Zikhron Ya'akov** · Edmond's beads leave by the south-east selvedge | "From 1882 Edmond buys land in Ottoman Palestine and funds settlements, among them Zikhron Ya'akov, named for his father, Jacob, that is, James. He dies in 1934; in 1954 he and Adelheid are reburied at Ramat HaNadiv (C)." |
| 12 | **Ruptures, then the fell** · house threads end in 1863, 1901, 1938 and 1982; back to stop 1, where the tour's silver thread now crosses the cloth | "Naples closes in 1863; Frankfurt in 1901, when Wilhelm Carl dies without a son. In Vienna in 1938, Louis is imprisoned for a year and freed for a ransom. In 1982 the French bank is nationalised (C). The silver thread is this tour. It skipped most lives. Pull any thread." |

**Interactions.** These follow the VISION-v4 cornerstone: hover, approach and dwell reveal meaning.
- **Hover** shows a tag; **dwell** for 0.6 s opens the card; **approach** reveals labels, at most 12 at once.
- **Select** flies the camera on the Gobbler's bowed path and dims the rest to 25 %.
- **F, follow:** ride a life from birth bead to tie-off knot; at each pick, ←/→ switches to the spouse's thread.
- **P, pull:** lift the ancestry out as a braid, with knots and the founders' share (sketch 06).
- **The fell:** a vertical beater on the left edge; `[` `]` move it one year, `{` `}` 25 years. Spoilers are off during the tour.
- **C, compare:** Rothschild, Habsburg and Darwin–Wedgwood on one calendar axis, gauged by close picks per generation. The app's three datasets are already Europe's best-known cases of close marriage, each for a different reason: a firm, dynastic alliance, and Darwin's marriage to his cousin Emma (S). There is no medical commentary.
- **/ search** is namesake-aware: Charlotte (1819–1884), Carl's daughter, versus Charlotte (1825–1899), James's.
- **? ask** answers only from the sources (§5).
- **Gobbler keys** stay: 1–8, `T`, `U`, `H`, `M`.

**Text.**
- **Two typefaces.** A serif for the story; mono for the instruments, as in the Gobbler.
- **Captions** sit in the lower third, one sentence at a time, each ending with a grade chip; its source numbers open rung 8.
- **The v4 corner card** sits opposite the focal thread. It reads: name; years as a range where sources differ; the path through the houses; then **Record**, **Computed** and **Narration · checked**, with the record always first.
- **Retire three labels:**
  - "Historical Snapshot" (AI text set above the record in gold italics);
  - "Hidden Insight";
  - "Present" for a missing death year.

## 3. The ladder (Gobbler grammar)

| Key | Rung | Frame | Scale bar | Gobbler twin | Loads |
|---|---|---|---|---|---|
| 1 | Cloth | the front of the tapestry | 25 yr ≈ one generation | Face | boot |
| 2 | Loom | five house bundles seen from above, ghost frame | 5 houses | Ribcage | boot |
| 3 | Fell | one year's plane, beating its events | 1 year | Heart | boot |
| 4 | Europe | top-down view: the five arrows | 300 km | Earth and Moon | lazy |
| 5 | Frankfurt | the lane on the town plan | 100 m | Village from orbit | lazy, later |
| 6 | The lane | street level in the Judengasse | 3.4 m · the front of the house Mayer was born in, home to 30+ (C) | Plaza | lazy, later (Blender bake) |
| 7 | A person | one figure at a window | 1.6 m · *figure, not likeness* | Villager (same H-Anim rig) | lazy, later |
| 8 | A fiber | one source line, magnified | one line of text | Feather | on demand |

- **Rungs 4–7 dive like the Gobbler's world.** A sensor triggers the Inline loads, the zoom is geometric, and the sway pauses.
- **Rung 8 is evidence.** Every rung ends in a source.
- **A second ladder checks every claim.** It applies the x3d.onto rungs: parsed → typed → valid (children born after parents, no cycles) → coherent (no merged namesakes) → sourced → visible → complete (no dangling ids) → meaningful (narrated and reviewed by a person).

## 4. Into the Gobbler multiverse, and an optional Armenian thread

**Two doors from the bird, which leads.**
- **The feather.** At rung 8, push into the vane: barbs become warp and their hooked barbules become picks. This adds a ninth stop, *The Loom*, as a lazy Inline with the same sensor → `set_load` wiring.
- **The village hall.** A tapestry hangs in Aurelsbrunn's hall, tagged *real people · sourced*, while the villagers' own cloth stays *simulated*. Fiction and history never share a thread.

**What carries over.**

| Gobbler part | Becomes in the loom |
|---|---|
| Heartbeat | the fell beats an events tape built from the ledger like `heart.json`; only C and L events beat |
| Preening wave | a beater wave climbing through time |
| Simulated shuttles | the narrator's real shuttle |

**Build notes.**
- **Stillness.** The cloth gets its own Transform with the sway paused.
- **Hover data.** Store the ledger as JSON-LD with provenance and grade on every relation, the shape of `graph-v3.jsonld`, so the v4 hover layer reads it unchanged.
- **The fell in X3D.** It can be a `ClipPlane` with a ghost copy above.

**Armenian thread: optional, offered rather than assumed.**
- **Glyph skin.**
  - The rail numbered in Armenian letter-numerals: Ա Բ Գ Դ Ե Զ Է Ը.
  - Years written the same way: 1744 = ՌՉԽԴ, and Mashtots's alphabet, about 405, = ՆԵ (∑).
- **Namesake stitch.** *Hagop* is the Western Armenian Jacob, and Zikhron Ya'akov remembers James as Jacob.
- **Datasets.**
  - **Mashtots's world, about 400–451:** King Vramshapuh; Catholicos Sahak, patron of the alphabet; and the Mamikonians, whose Vardan, Sahak's grandson, fell at Avarayr (S).
  - **The user's own family, from GEDCOM:**
    - Local only, with living people hidden, and no AI calls without consent.
    - A *T · testimony* grade for oral history.
    - Threads ending in 1915 end quietly, with a date and a source.
  - **Colophons (*hishatakaran*) as fibers.** Scribes name their patrons and kin (S).

## 5. AI narration: grounded and provider-pluggable

The pipeline: **ledger → fibers → narrator → checker → bake → player.**
- **Ledger.** Each person, link and event is a graded claim with its sources. The cloth draws only from the ledger; no model writes data.
- **Fibers.** Each source passage is pinned:
  - Wikipedia at a fixed `oldid`, and Wikidata statements with their references;
  - Rothschild Archive pages, and the 1906 Jewish Encyclopedia;
  - scholarship by citation only.

  Each fiber stores its URL and licence.

```ts
interface Narrator { id: 'gemini' | '[model]' | 'openai' | 'local' | 'none';
  draft(beats: Claim[], fibers: Fiber[], o: { maxWords: number }): Promise<Draft> }
type Draft = { sentences: { text: string; claims: string[]; quotes: { fiber: string; span: string }[] }[] }
```

- **Prompt.** Use only these passages and quote the support for each sentence. No superlatives, no "legend", "hidden", "secret", "control" or "influence"; omit anything unsupported. Today's prompts ask for "cinematic … legend … atmospheric" text and fall back to invented text ("whose influence shaped the modern world").
- **Checker, the exact oracle.** It is deterministic:
  - Each quoted span must occur in its fiber.
  - Every number, date and name must appear in a cited span or the ledger, and names resolve to ledger ids, which catches namesakes.
  - Matches against a **legend ledger** go to the legend lane with their verdict. Seeds: the Waterloo fortune (⚑; the Archive says couriers on horseback brought the news), Gutle's war line (S), and "controls the banks" framing.
  - Failing sentences are **withheld, not repaired** (the Goodhart pattern in the user's notes: a model told to pass a check games it). The card says "1 sentence withheld".
- **Bake.** Tour text is drafted offline, checked, read by a person, and shipped as JSON with a `receipt.json` (provider, model, prompt sha256, fiber revisions, verdicts), the text twin of the Cycles bake. Live drafting is only for "ask" and new datasets, cached by hash.
- **Keys and voice.** The Vite `define` ships the Gemini key in the bundle; use a small proxy. Voice is browser speech, never a cloned voice.

## 6. Sound, lightly

- **Silent until `M`.** A loom bed crossfades with the cosmos bed by distance.
- **The fell plays the events tape:** a wedding is a beater thump with a shuttle tick, a birth a high pluck, a death a damped low pluck.
- **Close marriage is audible:** one note twice, where an out-marriage sounds a fifth. You hear the weave loosen toward 1900.
- **Five Arrows:** five plucks, pitch falling with distance. **The legend lane** ducks to a dry paper texture.
- **Avoid** klezmer shorthand, and Haydn's imperial anthem at 1822, whose melody became Germany's. Chopin, who taught Betty's family (C), fits Paris.

## 7. Data the narrator must not trust

- **`charles` is missing.** It is referenced as Victor's parent but absent.
- **Guy's father is wrong in both versions.** It is `alphonse` in `roths3` and `edmond` in the older `rothschilds.html`; it was Édouard, Alphonse's son (S).
- **James Édouard's parent** is given as Alphonse, born 1827, though James Édouard was born in 1844 (S).
- **Carl "later moved to Frankfurt"**, but he died in Naples (C).
- **Charlotte (1819–1884) is probably a namesake mix-up.** Her note says "artist and pianist"; her page says socialite and patron, "better educated in art than her husband" (C).
- **`generation` is path-dependent** (§1), and **Mayer's birth year** is 1743 or 1744 (C).

## Sources opened this session

- Rothschild Archive:
  - [The name and arms](https://rothschildarchive.org/family/the_rothschild_name_and_arms)
  - [Gutle](https://family.rothschildarchive.org/people/209-gutle-rothschild-1753-1849)
  - [Walter](https://family.rothschildarchive.org/people/102-lionel-walter-walter-rothschild-1868-1937)
  - [Lionel](https://rothschildarchive.org/family/family_interests/politics)
- Wikipedia:
  - [Rothschild family](https://en.wikipedia.org/wiki/Rothschild_family)
  - [Mayer Amschel](https://en.wikipedia.org/wiki/Mayer_Amschel_Rothschild)
  - [Nathan](https://en.wikipedia.org/wiki/Nathan_Mayer_Rothschild)
  - [Carl](https://en.wikipedia.org/wiki/Carl_Mayer_von_Rothschild)
  - [Charlotte](https://en.wikipedia.org/wiki/Charlotte_von_Rothschild)
  - [Betty](https://en.wikipedia.org/wiki/Betty_von_Rothschild)
  - [Natty](https://en.wikipedia.org/wiki/Nathan_Rothschild,_1st_Baron_Rothschild)
  - [Charles](https://en.wikipedia.org/wiki/Charles_Rothschild)
  - [Edmond](https://en.wikipedia.org/wiki/Edmond_James_de_Rothschild)
- [Davidoff 2013, GHIL Bulletin 35.1](https://ghil.ac.uk/fileadmin/redaktion/dokumente/bulletin/GHIL_Bulletin_35.1/GHIL%20Bulletin%2035%20%282013%29%2C1%20-%20003%20-%20Article.pdf), quoting Ferguson, *The House of Rothschild* i, p. 184.

Bearings, distances, founder shares and the numerals come from `tools07/calc.py`; the sketches come from `tools07/sketches2.py`.
