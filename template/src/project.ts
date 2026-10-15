import {makeProject} from '@motion-canvas/core';

import scene1 from './scenes/scene1?scene';
import audio from './audio/pronto.wav';

export default makeProject({
  scenes: [scene1],
  audio,
});
