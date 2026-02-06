# Python API[¶](https://stable-retro.farama.org/python/#python-api "Link to this heading")

## RetroEnv[¶](https://stable-retro.farama.org/python/#retroenv "Link to this heading")

The Python API consists primarily of [`stable_retro.make()`](https://stable-retro.farama.org/python/#stable_retro.make "stable_retro.make"), [`stable_retro.RetroEnv`](https://stable-retro.farama.org/python/#stable_retro.RetroEnv "stable_retro.RetroEnv"), and a few enums. The main function most users will want is [`stable_retro.make()`](https://stable-retro.farama.org/python/#stable_retro.make "stable_retro.make").

stable\_retro.make(_game_, _state\=State.DEFAULT_, _inttype\=stable\_retro.data.Integrations.DEFAULT_, _\*\*kwargs_)[\[source\]](https://stable-retro.farama.org/_modules/stable_retro/#make)[¶](https://stable-retro.farama.org/python/#stable_retro.make "Link to this definition")

Create a Gym environment for the specified game

_class_ stable\_retro.RetroEnv(_game_, _state\=retro.State.DEFAULT_, _scenario\=None_, _info\=None_, _use\_restricted\_actions\=retro.Actions.FILTERED_, _record\=False_, _players\=1_, _inttype\=retro.data.Integrations.STABLE_, _obs\_type\=retro.Observations.IMAGE_, _render\_mode\='human'_)[\[source\]](https://stable-retro.farama.org/_modules/stable_retro/retro_env/#RetroEnv)[¶](https://stable-retro.farama.org/python/#stable_retro.RetroEnv "Link to this definition")

Gym Retro environment class

Provides a Gym interface to classic video games

If you want to specify either the default state named in the game integration’s `metadata.json` or specify that you want to start from the initial power on state of the console, you can use the [`stable_retro.State`](https://stable-retro.farama.org/python/#stable_retro.State "stable_retro.State") enum:

_class_ stable\_retro.State(_value_)[\[source\]](https://stable-retro.farama.org/_modules/stable_retro/enums/#State)[¶](https://stable-retro.farama.org/python/#stable_retro.State "Link to this definition")

Special values for setting the restart state of the environment. You can also specify a string that is the name of the `.state` file

DEFAULT _\= \-1_[¶](https://stable-retro.farama.org/python/#stable_retro.State.DEFAULT "Link to this definition")

Start the game at the default savestate from `metadata.json`

NONE _\= 0_[¶](https://stable-retro.farama.org/python/#stable_retro.State.NONE "Link to this definition")

Start the game at the power on screen for the emulator

## Actions[¶](https://stable-retro.farama.org/python/#actions "Link to this heading")

There are a few possible action spaces included with [`stable_retro.RetroEnv`](https://stable-retro.farama.org/python/#stable_retro.RetroEnv "stable_retro.RetroEnv"):

_class_ stable\_retro.Actions(_value_)[\[source\]](https://stable-retro.farama.org/_modules/stable_retro/enums/#Actions)[¶](https://stable-retro.farama.org/python/#stable_retro.Actions "Link to this definition")

Different settings for the action space of the environment

ALL _\= 0_[¶](https://stable-retro.farama.org/python/#stable_retro.Actions.ALL "Link to this definition")

MultiBinary action space with no filtered actions

DISCRETE _\= 2_[¶](https://stable-retro.farama.org/python/#stable_retro.Actions.DISCRETE "Link to this definition")

Discrete action space for filtered actions

MULTI\_DISCRETE _\= 3_[¶](https://stable-retro.farama.org/python/#stable_retro.Actions.MULTI_DISCRETE "Link to this definition")

MultiDiscete action space for filtered actions

You can also create your own action spaces derived from these. For an example, see [discretizer.py](https://github.com/farama-foundation/stable-retro/blob/master/stable_retro/examples/discretizer.py). This file shows how to use `stable_retro.Actions.Discrete` as well as how to make a custom wrapper that reduces the action space from `126` actions to `7`

## Observations[¶](https://stable-retro.farama.org/python/#observations "Link to this heading")

The default observations are RGB images of the game, but you can view RAM values instead (often much smaller than the RGB images and also your agent can observe the game state more directly). If you want variable values, any variables defined in `data.json` will appear in the `info` dict after each step.

_class_ stable\_retro.Observations(_value_)[\[source\]](https://stable-retro.farama.org/_modules/stable_retro/enums/#Observations)[¶](https://stable-retro.farama.org/python/#stable_retro.Observations "Link to this definition")

Different settings for the observation space of the environment

IMAGE _\= 0_[¶](https://stable-retro.farama.org/python/#stable_retro.Observations.IMAGE "Link to this definition")

Use RGB image observations

RAM _\= 1_[¶](https://stable-retro.farama.org/python/#stable_retro.Observations.RAM "Link to this definition")

Use RAM observations where you can see the memory of the game instead of the screen

## Multiplayer Environments[¶](https://stable-retro.farama.org/python/#multiplayer-environments "Link to this heading")

A small number of games support multiplayer. To use this feature, pass `players=<n>` to [`stable_retro.RetroEnv`](https://stable-retro.farama.org/python/#stable_retro.RetroEnv "stable_retro.RetroEnv"). Here is an example random agent that controls both paddles in `Pong-Atari2600`:

import stable\_retro as retro

def main():
    env \= retro.make(game\="Pong-Atari2600", players\=2)
    env.reset()
    while True:
        \# action\_space will by MultiBinary(16) now instead of MultiBinary(8)
        \# the bottom half of the actions will be for player 1 and the top half for player 2
        obs, rew, terminated, truncated, info \= env.step(env.action\_space.sample())
        \# rew will be a list of \[player\_1\_rew, player\_2\_rew\]
        \# done and info will remain the same
        env.render()
        if terminated or truncated:
            env.reset()
    env.close()

if \_\_name\_\_ \== "\_\_main\_\_":
    main()

## Replay files[¶](https://stable-retro.farama.org/python/#replay-files "Link to this heading")

Stable Retro can create [.bk2](http://tasvideos.org/Bizhawk/BK2Format.html) files which are recordings of an initial game state and a series of button presses. Because the emulators are deterministic, you will see the same output each time you play back this file. Because it only stores button presses, the file can be about 1000 times smaller than storing the full video.

In addition, if you wish to use the stored button presses for training, they may be useful. For example, there are [replay files for each Sonic The Hedgehog level](https://github.com/openai/retro-movies) that were made available for the [Stable Retro Contest](https://openai.com/blog/retro-contest/).

You can create and view replay files using the [The Integration UI](https://stable-retro.farama.org/integration/#integration-ui) (Game > Play Movie…). If you want to use replay files from Python, see the following sections.

### Record[¶](https://stable-retro.farama.org/python/#record "Link to this heading")

If you have an agent playing a game, you can record the gameplay to a `.bk2` file for later processing:

import stable\_retro

env \= stable\_retro.make(game\='Airstriker-Genesis-v0', record\='.')
env.reset()
while True:
    \_, \_, terminate, truncate, \_ \= env.step(env.action\_space.sample())
    if terminate or truncate:
        break

### Playback[¶](https://stable-retro.farama.org/python/#playback "Link to this heading")

Given a `.bk2` file you can load it in python and either play it back or use the actions for training.

import stable\_retro

movie \= stable\_retro.Movie('Airstriker-Genesis-Level1-000000.bk2')
movie.step()

env \= stable\_retro.make(
    game\=movie.get\_game(),
    state\=None,
    \# bk2s can contain any button presses, so allow everything
    use\_restricted\_actions\=stable\_retro.Actions.ALL,
    players\=movie.players,
)
env.initial\_state \= movie.get\_state()
env.reset()

while movie.step():
    keys \= \[\]
    for p in range(movie.players):
        for i in range(env.num\_buttons):
            keys.append(movie.get\_key(i, p))
    env.step(keys)

### Render to Video[¶](https://stable-retro.farama.org/python/#render-to-video "Link to this heading")

This requires [ffmpeg](https://www.ffmpeg.org/) to be installed and writes the output to the directory that the input file is located in.

python3 \-m stable\_retro.scripts.playback\_movie Airstriker-Genesis-Level1-000000.bk2