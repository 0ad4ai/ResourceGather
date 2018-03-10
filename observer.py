import actions
import numpy as np
from pysc2.env import environment
observation_size = 0


def process_observation(env_obs, flags=None):
    reward = env_obs.observation.reward
    available_actions = np.array([actions.check_available(env_obs.observation['available_actions'])])
    minerals = np.array([min(env_obs.raw_obs.player_common.minerals, flags.max_mineral_cost) / flags.max_mineral_cost])
    food_available = np.array([env_obs.raw_obs.player_common.food_cap - env_obs.raw_obs.player_common.food_used])
    bases = GetUnits(86, env_obs)
    number_of_bases = np.array([len(bases) / flags.max_bases])
    larva_by_base = np.array(get_larva_by_base(env_obs, bases, flags))
    obs = np.concatenate([available_actions, minerals, food_available, number_of_bases, larva_by_base])
    episode_end = (env_obs.observation.step_type == environment.StepType.LAST)
    return reward, obs, episode_end



def get_larva_by_base(env_obs, bases, flags=None):
    larva = [0]*flags.max_bases
    return larva
