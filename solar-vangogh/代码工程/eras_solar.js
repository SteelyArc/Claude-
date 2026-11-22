// How the solar system works — Van Gogh TikTok, 62 s, 1080x1920.
window.FILM_SIZE = [1080, 1920];
window.PUNCH = 0;
window.SCENE_LIBS = ['vg.js', 'scenes_solar.js'];
window.ERAS = [
  { id: 's01', dur: 4.5 }, { id: 's02', dur: 4.0 }, { id: 's03', dur: 4.0 }, { id: 's04', dur: 5.0 },
  { id: 's05', dur: 5.0 }, { id: 's06', dur: 7.0 }, { id: 's07', dur: 5.0 }, { id: 's08', dur: 4.0 },
  { id: 's09', dur: 5.5 }, { id: 's10', dur: 4.5 }, { id: 's11', dur: 3.0 }, { id: 's12', dur: 3.5 },
  { id: 's13', dur: 3.8 }, { id: 's14', dur: 3.2, transition: { type: 'swirl', dur: 0.6, cx: 540, cy: 900, punch: 0 } },
];
// [start, end, text, y]
window.CAPS = [
  [0.15, 2.4, 'POV: you finally get the solar system', 380],
  [2.4, 4.45, 'Step 1: lantern on a string', 380],
  [4.6, 6.0, 'Cut the string?', 380],
  [6.0, 8.45, 'It flies away. Bye bye.', 1500],
  [8.6, 10.4, 'Stop swinging?', 380],
  [10.45, 12.45, 'It falls. On you.', 1500],
  [12.6, 15.0, 'Planets do the SAME trick', 1480],
  [15.0, 17.45, 'but the string is GRAVITY', 1480],
  [17.6, 20.0, 'The Sun is 99.8% of EVERYTHING', 230],
  [20.0, 22.45, 'planets are basically crumbs', 230],
  [22.6, 24.8, 'Earth is falling at the Sun...', 300],
  [24.8, 27.0, '...and MISSING. Forever.', 300],
  [27.0, 29.45, '30 km every second, sideways', 300],
  [29.6, 32.0, 'Mercury: a year is 88 days', 1430],
  [32.0, 34.45, 'Venus: 465°C. Pizza oven.', 1430],
  [34.6, 38.45, 'Then a belt of space gravel', 230],
  [38.6, 41.0, 'Jupiter has a storm...', 1560],
  [41.0, 43.95, 'bigger than EARTH. Still going.', 1560],
  [44.1, 46.3, 'Saturn is so light...', 330],
  [46.3, 48.45, 'it would FLOAT in a bathtub', 330],
  [48.6, 51.45, 'Uranus rolls on its side. Probably got hit. Hard.', 330],
  [51.6, 54.95, 'Neptune: 1 year = 165 Earth years', 300],
  [55.1, 58.75, '8 planets. All falling. All missing.', 1450],
  [59.0, 62.0, 'Gravity: the original string', 380],
];
window.ERAS[0].init = () => U.assertGlyphs('LilitaOne-400', CAPS.map(c => c[2]).join('') + '0123456789°/km yrsYEARSBONKFALLMISS!', 'captions');
window.GLOBAL_OVERLAY = (c, t) => { for (const [a, b, txt, y] of CAPS) if (t >= a && t < b) VG.caption(c, txt, y, t - a, { size: 80, maxW: 860 }); };
