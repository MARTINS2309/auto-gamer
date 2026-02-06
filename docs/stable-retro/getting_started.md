# Getting Started[¶](https://stable-retro.farama.org/getting_started/#getting-started "Link to this heading")

Stable Retro requires one of the supported versions of Python (3,6 to 3.10). Please make sure to install the appropriate distribution for your OS beforehand. Please note that due to compatibility issues with some of the cores, 32-bit operating systems are not supported.

pip3 install stable-retro

See the section development if you want to build Stable Retro yourself (this is only useful if you want to change the C++ code, not required to integrate new games).

## Create a Retro Environment[¶](https://stable-retro.farama.org/getting_started/#create-a-retro-environment "Link to this heading")

After installing you can now create a [Gymnasium](https://gymnasium.farama.org/) environment in Python:

import stable\_retro
env \= stable\_retro.make(game\='Airstriker-Genesis-v0')

### Migration from gym-retro or older stable-retro[¶](https://stable-retro.farama.org/getting_started/#migration-from-gym-retro-or-older-stable-retro "Link to this heading")

If you’re migrating from gym-retro or an older version of stable-retro, note that the package import name has changed:

**Old way (deprecated but still works):**

import retro  \# Shows deprecation warning
env \= retro.make(game\='Airstriker-Genesis-v0')

**New way (recommended):**

import stable\_retro  \# Use the full new name
env \= stable\_retro.make(game\='Airstriker-Genesis-v0')

\# Or use an alias for easier migration:
import stable\_retro as retro  \# Keeps your code working with minimal changes
env \= retro.make(game\='Airstriker-Genesis-v0')

The old `import retro` syntax will continue to work with a deprecation warning to ease migration.

`Airstriker-Genesis` has a non-commercial ROM that is included by default.

Please note that other ROMs are not included and you must obtain them yourself. Most ROM hashes are sourced from their respective No-Intro SHA-1 sums. See [Importing ROMs](https://stable-retro.farama.org/getting_started/#importing-roms) for information about importing ROMs into Stable Retro.

## Example Usage[¶](https://stable-retro.farama.org/getting_started/#example-usage "Link to this heading")

Stable Retro is useful primarily as a means to train RL on classic video games, though it can also be used to control those video games from Python.

Here are some example ways to use Stable Retro:

### Interactive Script[¶](https://stable-retro.farama.org/getting_started/#interactive-script "Link to this heading")

There is a Python script that lets you interact with the game using the Gymnasium interface. Run it like this:

python3 \-m stable\_retro.examples.interactive \--game Airstriker-Genesis-v0

You can use the arrow keys and the `X` key to control your ship and fire. This Python script lets you try out an environment using only the Stable Retro Python API and is quite basic. For a more advanced tool, check out the [The Integration UI](https://stable-retro.farama.org/integration/#integration-ui).

### Random Agent[¶](https://stable-retro.farama.org/getting_started/#random-agent "Link to this heading")

A random agent that chooses a random action on each timestep looks much like the example random agent for [Gymnasium](https://gymnasium.farama.org/):

import stable\_retro as retro

def main():
    env \= retro.make(game\="Airstriker-Genesis")
    env.reset()
    while True:
        action \= env.action\_space.sample()
        observation, reward, terminated, truncated, info \= env.step(action)
        env.render()
        if terminated or truncated:
            env.reset()
    env.close()

if \_\_name\_\_ \== "\_\_main\_\_":
    main()

A more full-featured random agent script is available in the examples dir:

python3 \-m stable\_retro.examples.random\_agent \--game Airstriker-Genesis-v0

It will print the current reward and will exit when the scenario is done. Note that it will throw an exception if no reward or scenario data is defined for that game. This script is useful to see if a scenario is properly set up and that the reward function isn’t too generous.

### Brute[¶](https://stable-retro.farama.org/getting_started/#brute "Link to this heading")

There is a simple but effective reinforcement learning algorithm called “the Brute” from [“Revisiting the Arcade Learning Environment”](https://arxiv.org/abs/1709.06009) by Machado et al. which works on deterministic environments like Stable Retro games and is easy to implement. To run the example:

python3 \-m stable\_retro.examples.brute \--game Airstriker-Genesis-v0

This algorithm works by building up a sequence of button presses that do well in the game, it doesn’t look at the screen at all. It will print out the best reward seen so far while training.

### PPO[¶](https://stable-retro.farama.org/getting_started/#ppo "Link to this heading")

Using [“Proximal Policy Optimization”](https://arxiv.org/abs/1707.06347) by Schulman et al., you can train an agent to play many of the games, though it takes awhile and is much faster with a GPU.

This example requires installing [Stable Baselines](https://github.com/DLR-RM/stable-baselines3). Once installed, you can run it:

python3 \-m stable\_retro.examples.ppo \--game Airstriker-Genesis-v0

This will take awhile to train, but will print out progress as it goes. More information about PPO can be found in [Spinning Up](https://spinningup.openai.com/en/latest/algorithms/ppo.html).

## Integrations[¶](https://stable-retro.farama.org/getting_started/#integrations "Link to this heading")

What games have already been integrated? Note that this will display all defined environments, even ones for which ROMs are missing.

import stable\_retro
stable\_retro.data.list\_games()

The actual integration data can be see in the [Stable Retro Github repo](https://github.com/farama-foundation/stable-retro/tree/master/stable_retro/data/stable).

## Importing ROMs[¶](https://stable-retro.farama.org/getting_started/#importing-roms "Link to this heading")

If you have the correct ROMs on your computer (identified by the `rom.sha` file for each game integration), you can import them using the import script:

python3 \-m stable\_retro.import /path/to/your/ROMs/directory/

This will copy all matching ROMs to their corresponding Stable Retro game integration directories.

Your ROMs must be in the [Supported ROM Types](https://stable-retro.farama.org/integration/#supported-roms) list and must already have an integration. To add a ROM yourself, check out game-integration.

Many ROMs should be available from the [No-Intro Collection on Archive.org](https://archive.org/details/No-Intro-Collection_2016-01-03_Fixed) and the import script will search inside of zip files.