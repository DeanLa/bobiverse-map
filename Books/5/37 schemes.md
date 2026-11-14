## 37. Schemes

Icarus

August 2321

Sentry System

You’d think the prospect of rotting in a holding cell would spur us to heights of creativity, but no. After several real-time hours of thinking, we still had nothing. I was sitting back, holding a coffee and staring into space, when Dae muttered, “You’d think the builders would have allowed for something like this.”

I sat up straight. “I bet they did!”

“Huh?”

“Like high-security areas back on Earth. If the fire alarms went off, everything unlocked so people could get out.”

Dae frowned. “Yeah, and wasn’t there a car that you could trick into unlocking by convincing it you were trying to get out?”

“Something like that,” I replied with a smile. “But the point is, there should be a procedure for handling nonroutine situations.”

“Sounds great, except for the powered-down spaceship over there.”

I waved a hand dismissively. “The ship probably just sat there until it shut down. The AMIs or whatever are running this station would have considered it a routine situation until it was too late. At that point, there was no further action required.”

“So we have to convince them we’re dying before we actually die.”

“Like that, yeah.”

“Except, and I feel like I shouldn’t need to point this out, we can’t even talk to them.”

“Well then, we need to start working on that.”

“Oh, this should be good.”

Over the next several hours, we tried numerous ways to get their attention. We sent TV signals; we streamed video over radio; we tried embedding graphics images in the packets; we even tried SCUT. There was one unencrypted channel where we got what I think was simply a reflexive ACK. I pegged that as the common channel for this civilization. But other than the ACK, the sentinels showed no signs of having heard us.

“This is not going well,” I muttered. “I think the problem is that decoding radio or SCUT requires problem-solving abilities and the desire to do so. The sentinels are simply ignoring anything they don’t recognize. Their lower-layer protocols may not even be passing our attempts up the chain, so they might not even know we’re attempting to communicate.”

“So give them something visual,” Dae said. “Presumably they use some kind of optical receptors, so they’d attempt to characterize anything they see.”

“Because … ” I replied.

“Because, Icky, that’s what visual intelligences do. Even AMIs will attempt to identify anything their visual systems pick up.”

“It’s not your worst theory.”

“Unlike yours, it hasn’t failed.”

“Yet.” Sniping aside, Dae’s idea sounded logical. But how to present an image to them?

Ah. We had a drone sitting outside, still being held in a tractor beam. It was fitted with a comms laser, which could work in any of several frequencies. Some of those frequencies were in the visual spectrum. Well, our visual spectrum. If one didn’t work, I’d try others—until I ran out of options.

I sent the drone a set of instructions, and it proceeded to light the side of my hull with a circle. After a few seconds, it switched to a triangle. It worked its way through the basic shapes: square, pentagon, hexagon, heptagon, octagon, nonagon, and decagon. Then it cycled back through the series. As it worked through the images, I transmitted radio packets with the same shapes embedded in a simple bit matrix as the payload.

Nothing.

“Well, hell.” I looked at Dae. “Any ideas?”

“Maybe make it explicitly pixelated. And put a pixelated frame around it to indicate your dimensions.”

“And match that in the packet!” I exclaimed. “Excellent.”

No sooner said than done. Now the drone was drawing images with pixels instead of vector graphics. I made sure the pixelation was clearly visible, which allowed the observer to count the pixels. The size of the packet allowed for a 1024-by-1024 image if I encoded the image on a bit-by-bit basis, but I didn’t want to complicate things any more than I had to, so I went with a much smaller image, one byte per pixel.

On the second time through the sequence, the sentry started echoing the packets back. Well, not quite echoing. It had changed the envelope slightly. And on each lap, it was changing the image size.

“It’s teaching us their graphical interchange format?” Dae said, half questioning.

“Let’s not confuse things. How about GEF? You know, graphical exchange format?”

“Sure thing. Don’t want to get sued by, uh … ”

“Compuserve, I think. Are they even still in business?”

Dae laughed. “I’m betting no. Anyway, whatever we call it, we’re communicating. So what’s next, oh wise one?”

“We establish math.”

Since we now had a standard image format, I abandoned the laser light show. I sent an image of the numeral zero, with a slash through it to indicate that it wasn’t just another circle GEF. Then one dot, with the numeral one beside it. Then two dots, and the numeral two. I went through the sequence up to twenty-one, which should indicate to the sentry that we used decimal, positional notation. I then jumped to one hundred dots, with the numerals one, zero, zero. I waited.

The sentry sent back a GEF of one hundred and six dots, with the proper numerals beside them.

I whooped, and Dae did a fist pump. “It’s getting it,” I exclaimed.

“More important, it’s willing to work with us,” he replied. “If it had ignored us, we might as well just turn off our power now.”

That statement was a total downer and took the celebration right out of the air. I cleared my throat (totally unnecessary in VR) and sent a new graphic. This one showed several examples for each of the four basic arithmetic operations. One plus four equals five, three times four equals twelve, eight minus one equals seven, twelve divided by three equals four, and so on. The sequence allowed only one interpretation for each of the math symbols. I deliberately used an asterisk for the multiply symbol, as I’d be needing the X later.

The sentry responded by sending back four math ops with different values and correct answers.

“Ladies and gentlemen, we are in business,” I crowed.

“Excellent. We can play math games. You have a long game plan?”

I gave Dae an eyebrow waggle in reply.

Next, I sent four math statements with incorrect results using the not-equals sign—an equals sign with a diagonal slash through it.

Again, the sentry responded with confirmatory examples.

Now, time to start formal logic. I sent four plus two equals six with a check after it, then four plus two equals seven with an X after it. Again, the sentry responded.

“True and false?” Dae said.

“Yep. Or maybe agree and disagree.”

Over the next while, I went through logic symbols, such as AND, OR, NOT, and the mathematical operators. In C and C# tradition, I used single symbols for the math versions and double symbols for the logic versions. I was concerned that this might be confusing, but the sentry stayed with me.

“Hey, Icky?” Dae said slowly.

I felt a pang of panic at the tone. “What?”

“You have an audience.”

I’d been so preoccupied with my lessons that I hadn’t noticed several other sentries drifting over. Which was a little odd, since I’d stopped using the laser as soon as we agreed on the GEF packet format.

“Doesn’t this indicate a certain level of individuality?” Dae commented. “And curiosity?”

“Hmm. Might still be duty driven. They’re interested because they’ve decided it’s relevant to their jobs.”

“Don’t care. I’ll take it.”

“Yep. As long as they’re listening, we have a chance.”

Now I needed to start asking questions. I sent a simple math problem with a question mark for the answer, then the same problem with the answer showing. The sentry immediately sent back a different problem in the same format.

I paused and sat back. That completed the math and logic lessons. Well, I could do set theory and such, but I didn’t need it for what I wanted to do.

I carefully crafted an image of the alien probe, with lights on and little hydrogen atoms in the middle to indicate a working nuclear-fusion generator. I added navigation lights and lit-up portholes—total artistic license, but I had to make the point that it was alive and operating. I added one of the sentries holding it—again, using artistic license to portray the tractor beam.

I sent the image, then another with the lights dimmer and fewer atoms. Then a third with no lights and no power. I waited a moment, then sent the same sequence, but with our ships. Then a single question mark.

No response.

“They may be bumping this up the chain of command,” Dae commented.

“Or trying to. I bet they’re not getting any responses.”

At that moment, the sentry sent an image. I whooped and did a fist pump. The image portrayed our ships going back through the wormhole, followed by a question mark. I quickly sent back the same image with a check. Then I had an idea. I sent another image of us taking the alien probe vessel with us, and a question mark.

Again, no response.

When they finally responded, it was after exactly the same delay as the previous time. “Huh. Standard time-out, I guess. Then they have to make the decision themselves.” It was the same image I’d sent, but with a check. So we would be allowed to take the alien probe.

One small problem—no tractor beam.

“We can use drones,” Dae suggested. “Same process as moving small asteroids. No biggie.”

We were extremely careful over the next several hours to verify every move with the sentries. We didn’t want any misunderstandings or overreactions. But eventually, we found ourselves very slowly drifting through the gate while a couple of our drones very slowly pushed the alien probe through behind us.

“Want to send them a goodbye?” Dae asked. “Maybe a middle finger?”

I laughed. “It would be just our luck if they understood the intent and responded by blowing us out of the sky. Let’s just get out of town with our skin intact, okay?”

Soon, we found ourselves back at Hub Zero with a dead vessel from an unknown civilization. It was interesting, though, that the design of the ship was quite comprehensible. A SURGE drive was easily identifiable from our scan, as was a fusion reactor and a magnetic hydrogen scoop system. Other parts were less recognizable, like the computer system and what had to be their version of a 3D printer.

Interestingly, the ship did not seem to have a supply of drones, or roamers, or the makings of a full-on autofactory—just the one printer and a small supply of what might be maintenance bots. It was a stripped-down Von Neumann probe, without the capability to replicate. Really nothing more than an exploratory scout.

The immediate problem, though, was getting it operational. To do that, we would have to get the reactor going without a working ramscoop system to supply the reactor with fuel. To add insult to injury, Heaven vessels hadn’t been built with ramscoops since the end of the War for Earth, when we converted to Casimir systems. So we had no way to collect hydrogen for the ship even if we did have some other way to ram it into the reactor.

We went around and around for hours, but in the end, there was only one option. We’d have to install a Casimir generator. That would mean cutting into the ship and performing some surgery.

“I hope it’s not going to feel violated when it wakes up,” I said, “and discovers a new body part.”

“I’m sure there must be some B movie covering this kind of thing,” Dae replied, “but I’m coming up blank. Look, let’s just put it in and apologize afterward.”

It took a week all told, since we were extremely careful both in cutting our way into the vessel and in making sure that we got all the voltage and current requirements right. This must have been what Neil and Herschel felt like while deciphering the Others’ cargo ship.

“Activating,” I said, and pressed the button. In the monitor window, the generator went through boot-up, then came online. And the ship activated.

This was the moment of truth. We hadn’t detected any weapons in the ship, not even a rail gun. But you never knew.

The ship sent out a SUDDAR pulse, easily identifiable. It had scanned us. Hopefully it would see that we were at Hub Zero and would come to the obvious conclusion.

“You know we’re just going to have the same problem communicating with this guy,” I said. “No common format for radio comms, no common SCUT channels, no nothing. Assuming it even has SCUT. I didn’t see one.”

“So use the same solution. And hope this guy’s at least as smart as the sentries.”

Well, why not? I positioned myself in front of the alien ship, sent out a drone with a laser, and started the lesson.

*OceanofPDF.com*
