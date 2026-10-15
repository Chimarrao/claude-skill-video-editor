import {makeProject} from '@motion-canvas/core';

import cena1 from './scenes/cena1?scene';
import audio from './audio/pronto.wav';

export default makeProject({
  scenes: [cena1],
  audio,
});
