## 12. Tech Sleuthing

Icarus

September 2320

Alien System

“They have to have some kind of address identification,” I mused, staring at the map I’d created.

“How so?” Dae replied.

I gestured to the map we’d made of the hundreds of wormhole gates in their various orbits. “Otherwise, it’s just a bunch of random wormholes. What did the locals do—just pick one and hope? There must be street signs of some kind.”

Dae nodded. He had followed me through the wormhole and now was sitting in the patio chair he preferred when he was visiting my VR, my cat Spike in his lap and a coffee in his hand. “Theories?” he said.

“Every wormhole has a couple of stations or satellites, and every single one is aligned with the galactic axis. So that’s deliberate. Logic says they’re holding the wormholes open with some kind of negative energy or something. Logic also says they’ll provide the identification data.”

“Which we’ll be able to read right away, because everyone speaks English.”

“Shaddap. Also, no. But we’ve got, what? Three hundred and forty-two individual samples here to work with? If we can elicit a response at all from the satellites, we shouldn’t have any trouble extracting envelope, payload, and identification.”

“Or we squirt a radio signal at a satellite, and it considers that an attack and shoots us out of the sky.”

“Sure. Or that.” I paused. “Radio’s a good place to start, though. It’s directional; the signal strength falls off rapidly, making it perfect for selective activation. I bet it doesn’t even have to be a complex request.”

“A great theory,” Dae replied, “but if any old signal could elicit a response, the satellites would be constantly responding to random stellar fluctuations, don’t you think?”

It took several hours of experimentation to discover the frequency that the satellites were paying attention to—a frequency, not surprisingly, that didn’t match up with the emission spectrum of any element on the periodic table, and so wouldn’t be generated naturally. And the mechanism was simple. Beam that frequency at a satellite for more than five milliseconds, and it beamed back what appeared to be something like a network packet.

I looked at the window that displayed the response in a hex-dump format. “Okay, good. I’ll send a request to the same station several times to isolate timestamps and such while you try a bunch of different ones to map changes that are probably payload.”

“Aye aye, captain,” Dae replied. The wormholes were distributed around orbits starting just outside one AU, so he would have to fly a powered orbit to query all the satellites. To get it done properly would take about two days.

Once Dae had completed the circle, we updated my map with the street-sign data. Based on the results, this civilization used a ten-bit byte and a five-byte word. Not huge, but it still put the numeric value range in the quadrillions, which was probably good enough for one galaxy. The problem, of course, was that we had no way to interpret the address information.

“Dae, do me a favor and go back to the home system and get the address data from the wormholes there?”

“No prob. Be right back.”

While he was doing that, I began a concerted analysis of all the wormhole data I already had. It was possible that the data payload included sources as well as destination information, in which case all wormholes in this system would have an identical source address.

Of course, nothing is ever that easy, but I did quickly isolate the payload and identify the timestamp. Being that I was staring at a hex dump, I was feeling my eyes want to go out of focus when Dae grunted.

He flipped the window he’d been working on around so I could see it. A couple of fields were circled. “These fields are the same values, only swapped on the wormhole that brought us here and its mate on this side. Source and destination?”

“I believe you are correct. We can test that by sending drones through some other wormholes and getting a read on the far-side addresses. If we also take the time to identify the galactic locations, we might be able to identify their mapping strategy.”

“Assuming it’s not just something arbitrary, like ‘Main Street.’”

“You’re a real joy to work with, Dae—anyone ever tell you that?”

“Constantly.”

I snorted and pulled up my drone control. “Let’s start surveying.”

Three hundred and forty-two tunnels to other stars. It was a Trekkie’s dream. Or would have been, if it had been less tedious. The physical trips only took about three weeks total. The drone would fly through, read the address data from the satellite, take a spherical image for establishing a navigational fix, scan for other wormholes, and come back. It was difficult beyond belief to maintain discipline and not investigate each star system. The only concession to curiosity was letting the drone listen for radio traffic while doing the imaging.

I stared at the spreadsheet in the window. Values were slowly being filled in as our apps identified the locations of the various systems. We’d extracted all data fields that we could identify from their packets and placed them in spreadsheet columns with tentative titles.

Dae reached past me and pointed at two lines. “We know these systems are the same distance from the galactic core, based on our own measurements. See those values?”

I nodded. “That’s a radial value, then. Do you think they’re using the same coordinate system as we do?”

“Well, the same style. I doubt they have three hundred and sixty degrees in a circle.”

I waved off the objection. “Seriously, there are only so many ways to track locations in a galactic disk, and they all need three coordinates. Radial distance, angle from an arbitrary zero point, and distance above or below the galactic plane, which could be an angle or a distance value—unless they think truly differently, it makes sense.”

“So map them. We have radial distance, latitude, and altitude coordinates from our own measurements. Compare to what’s in the packets.”

I nodded and ran a couple of test conversions. On the third try, I had a match. “It’s close but not perfect. I imagine the proper motion of the individual systems is creating some drift from the published coordinates. Maybe they update them periodically.”

“Or maybe some of the stuff we haven’t been able to identify is time-based adjustment data.”

“Could be. Unfortunately, mapping the actual proper motion would take a lot longer. And does it matter?” I waved a hand and the window shrank, while a 3D image of the entire Milky Way popped up in my holotank. Most of it was just fog, of course, since we didn’t actually have a good map of the galaxy—especially the opposite side from Earth’s location. But the wormhole destination systems were all marked.

“Mostly relatively local. Except … ” Dae pointed. “Long-distance jumps. I bet if we follow this thing around, we could circumnavigate the galaxy.”

“Then let’s do that,” I said.

“Seriously?”

“Dae, we were on our way to the galactic center. Via sub-light. With no map. This seems less risky, somehow.”

“Well, assuming we don’t run into anyone.”

“Let’s try to stick to hubs. Speaking of which, I bet there’s data in the packet that identifies hubs versus local jumps. We just need more samples.”

“Sure, that’s why we’re doing it. Samples. That’s the ticket. Yeah.”

I chuckled and pointed to a destination that was about seven degrees around the galaxy, at the same distance from the core as our current position. “And that’s the leading candidate.”

*OceanofPDF.com*
