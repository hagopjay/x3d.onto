# Ontology + X3D scenarios, round 2, spec v1 (16 Nov 2026)

Ask (HagopJay, 16 Nov 15:05Z): "continue ideating and iterating and come up with 2-3 new example and practical and insightful scenarios and integrate and continue learning". At 15:07Z he picked building, warehouse, city and concert, then added "and fire code!!" and "and farm!!". At 15:08Z he wrote "take your time, make it properly. dont skimp".

The spine is the same as round 1: every scene object is DEF'd and flat under Root, so its world position is its translation. A domain graph in an open vocabulary is joined to the scene by DEF IRIs. Each case has three questions that need both graphs, one inference, and two SHACL checks with planted faults. Answers are checked by a Python oracle, a JS parity run and recorded calls to the real MCP server (data_ttl, PR #20).

## What round 1 taught (carried in)
- The tools could not join a domain graph, and the aggregate graph doubled rows on a/b paths. Both are fixed in PR #20. Round 2 is the first real use of `data_ttl` by many cases.
- Validate the profile: PhysicalMaterial needs `<component name='Shape' level='2'/>` under Immersive.
- Highlight by baseColor as well as emissive. Frame the overview to cover every object.
- Never use GROUP BY inside SHACL-SPARQL (the browser engine needs a workaround for it). Use FILTER NOT EXISTS for "nearest" and "none within".
- Keep numbers plain in SPARQL (seconds, metres), and keep the vocabulary's own terms beside them.

## S4 Building: "Floor 3 heats an empty room" (Brick)
- Scene: a floor with six rooms, the AHU, six VAV boxes, temperature and occupancy sensors, and windows.
- Questions: (1) rooms warmer than setpoint + 1 K while unoccupied (energy waste); (2) what loses air if AHU-1 trips (brick:feeds+); (3) rooms more than 2 K off setpoint.
- Checks: a temperature sensor must be drawn inside the room it is recorded for (fault: Sensor 303 is in Room 304, a classic commissioning error); every drawn room has a temperature point (fault: Room 306's point deleted).
- Inference: feeds chains AHU to VAV to zone to room.

## S5 Warehouse: "Recall lot L-2291 before lunch" (GS1 Web Vocabulary)
- Scene: three racks of bins, pallets in the bins, a cold room, and dock doors.
- Questions: (1) every pallet holding lot L-2291, including pallets that only hold its cases; (2) first-expiry-first-out pick order for one product; (3) empty bins for putaway.
- Checks: a chilled product (2 to 8 °C) must be drawn inside the cold room (fault: pallet P-07 is in Rack A); the bin the record assigns must match the drawn bin (fault: P-03 drawn one bin over).
- Inference: contains+ (pallet, case, lot), so the recall reaches mixed pallets.

## S6 City: "The block that knows its shadows" (GeoSPARQL 1.1)
- Scene: a city block with parcels, buildings, a park, a flood zone and a new transit stop.
- Questions: (1) buildings whose noon shadow on the December solstice reaches the park (elevation 25.9° at 40.7°N, shadow = h / tan); (2) buildings inside the flood zone; (3) buildings within 400 m of the stop.
- Checks: drawn height must not exceed the zoning district's maximum (fault: Tower 5 is drawn 48 m in a 36 m district); a building must lie inside its parcel (fault: Building 2 overhangs).
- Inference: sfWithin rolls parcels up to blocks and districts.
- Note: GeoSPARQL geof: functions are not run (no engine here has them); positions come from the X3D. The page says so.

## S7 Concert: "A stage plot that knows the setlist" (Music Ontology + Timeline + Event)
- Scene: a stage with performers, instruments, mics, wedges, two followspots and the FOH.
- Questions: (1) who is playing at 00:12:30 into the show; (2) which instruments change between songs 3 and 4 (the stage crew's list); (3) who the followspots track in song 4.
- Checks: every instrument that is played has a mic or DI drawn within 1.0 m (fault: the guitar amp mic is 2 m away); every performer has a wedge within 2.5 m (fault: the keys wedge is across the stage).
- Inference: event:sub_event+ (show, set, song), so "everything in Set 2" lights.
- It ties to LOOMSONG (x3d.music).

## S8 Fire code: "Can everyone get out of Floor 4?" (BOT + code clauses as data)
- Scene: an office floor with rooms, a corridor, doors and two exit stairs.
- Code values are read as we understand IBC 2021, and this is not a code review:
  - occupant load factor: business, 150 gross sq ft (13.94 m²) per person (Table 1004.5);
  - two exits above 49 occupants (Table 1006.2.1);
  - exit access travel distance: 300 ft (91.4 m), sprinklered B (Table 1017.2);
  - door clear width: 32 in (0.813 m) (1010.1.1).
- Questions: (1) occupant load per room from the drawn area; (2) straight-line distance from each room to the nearest open exit; (3) people per egress door.
- Checks: every egress door is drawn at least 0.813 m wide (fault: Door 412 is drawn 0.76 m); every room has an open exit within 91.4 m (fault: the record says Stair B is locked).
- Inference: reachability through doors (BOT interfaces).

## S9 Farm: "Greenhouse 2 waters what is thirsty" (AGROVOC + SOSA + QUDT)
- Scene: a greenhouse with beds, soil moisture sensors, irrigation valves, vents and a humidity sensor.
- AGROVOC broader chains are fetched live on 16 Nov:
  - tomatoes, fruit vegetables, vegetables, plant products;
  - lettuces, leaf vegetables, vegetables;
  - cucumbers, cucurbit vegetables, vegetables;
  - basil, culinary herbs, plant products (basil is not a vegetable).
- Questions: (1) beds below their crop's moisture threshold; (2) powdery mildew risk (RH above 85 % near tomato and cucumber beds); (3) which valve waters a given bed.
- Checks: a moisture sensor is drawn inside the bed it reports (fault: Sensor B2 is in Bed B3); every planted bed has a valve (fault: Bed C2's valve is missing).
- Inference: skos:broader+, so "all vegetable beds" lights and basil stays dark.

## Gates
- Private preview first; x3d.demo only on his word.
- Factory-style disclaimers: the data are invented examples. Real vocab terms are checked against the publishers' files.
- Leak sweep before publish.
