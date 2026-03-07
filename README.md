# Bobiverse Interactive Star Map

An interactive 2D star map and timeline viewer for Dennis E. Taylor's **Bobiverse** book series (Books 1-3). Track Bob replicants as they explore the galaxy, clone themselves, and encounter alien civilizations.

## Features

- **19 real star systems** plotted using actual astronomical coordinates (RA/Dec + distance)
- **50+ Bob replicants** with lineage-based color coding
- **Timeline slider** (2133-2263) with play/pause, step, and speed controls
- **Interpolated travel** - Bobs smoothly move between stars during transit
- **Spoiler-free** - select your current book and chapter to hide future events
- **Event log** - chronological list of major events, highlighted as the timeline progresses
- **Clustered labels** - stacked neatly when multiple Bobs share a location
- **Group markers** - unnamed Bob groups shown with count overlays

## Usage

Open `index.html` in any modern browser. No dependencies, no build step.

### Controls

| Control | Action |
|---------|--------|
| Space | Play / Pause |
| Left / Right arrows | Step backward / forward |
| +/- | Increase / decrease playback speed |
| Mouse wheel | Zoom in / out on star map |
| Click + drag | Pan the star map |

On first load, a configuration screen lets you pick your reading progress (book + chapter) to avoid spoilers. You can reopen it from the settings button.

## Data Sources

Star positions come from real astronomical catalogs. Timeline data was compiled from:

- [Bobiverse Timeline (Pastebin)](https://pastebin.com/nqMFMb5y)
- [Bobiverse Wiki](https://bobiverse.fandom.com/)
- [Bob family tree (GitHub)](https://github.com/Jeidnx/bobiverse-family-tree)

A few systems (GL 877, HIP 84051, Ragnarok, Odin) use estimated coordinates where real data was unavailable.

## Books Covered

1. **We Are Legion (We Are Bob)** - Chapters 1-61, events through ~2188
2. **For We Are Many** - Chapters 1-77, events through ~2221
3. **All These Worlds** - Chapters 1-76, events through ~2263

## Tech

Single self-contained HTML file. Vanilla JavaScript, Canvas API, no external dependencies.

## License

This project is licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). See [LICENSE](LICENSE) for details.
