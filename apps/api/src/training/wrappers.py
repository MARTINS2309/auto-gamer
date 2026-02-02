import gymnasium as gym
from gymnasium.wrappers import ResizeObservation, GrayscaleObservation, NormalizeObservation, FrameStackObservation
from stable_baselines3.common.monitor import Monitor

def make_retro_env(game, state, observation_type="image", action_space="filtered"):
    import retro
    
    # This is a bit simplified; typically we need a Render kwarg or something
    # But retro.make is the standard entry point.
    
    env = retro.make(
        game=game,
        state=state,
        render_mode="rgb_array" 
    )
    
    env = Monitor(env)
    
    if observation_type == "image":
        env = ResizeObservation(env, (84, 84))
        env = GrayscaleObservation(env)
        env = FrameStackObservation(env, stack_size=4)
        
    return env
