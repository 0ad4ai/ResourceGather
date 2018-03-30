import common.parse_args
import os
from absl.flags import FLAGS
import sys
import threading
import numpy as np
import tensorflow as tf

from pysc2 import maps
from pysc2.env import sc2_env
from pysc2.lib import stopwatch
from time import sleep
from worker import Worker
from Action_Space import Action_Space
import agent

global _max_score, _running_avg_score, _steps, _episodes
# noinspection PyRedeclaration
_max_score = _running_avg_score = 0
# noinspection PyRedeclaration
_steps = _episodes = []

'''
FLAGS = flags.FLAGS
flags.DEFINE_bool("train", True, "Whether to train the agent or not during the loop.")
flags.DEFINE_bool("render", False, "Whether to render with pygame.")
flags.DEFINE_integer("screen_resolution", 84,
                     "Resolution for screen feature layers.")
flags.DEFINE_integer("minimap_resolution", 64,
                     "Resolution for minimap feature layers.")

flags.DEFINE_integer("max_agent_steps", 2500, "Total agent steps.")
flags.DEFINE_integer("game_steps_per_episode", 0, "Game steps per episode.")
flags.DEFINE_integer("step_mul", 8, "Game steps per agent step.")

flags.DEFINE_string("agent", "pysc2.agents.random_agent.RandomAgent",
                    "Which agent to run")
flags.DEFINE_enum("agent_race", "Z", sc2_env.races.keys(), "Agent's race.")
flags.DEFINE_enum("bot_race", None, sc2_env.races.keys(), "Bot's race.")
flags.DEFINE_enum("difficulty", None, sc2_env.difficulties.keys(),
                  "Bot's strength.")

flags.DEFINE_bool("profile", False, "Whether to turn on code profiling.")
flags.DEFINE_bool("trace", False, "Whether to trace the code execution.")
flags.DEFINE_integer("parallel", 1, "How many instances to run in parallel.")

flags.DEFINE_bool("save_replay", True, "Whether to save a replay at the end.")
flags.DEFINE_string("map", "AbyssalReefLE_RL", "Name of a map to use.")

# Network specific flags
flags.DEFINE_integer("max_mineral_cost", 300,
                     "Maximum mineral cost of any one thing.")
flags.DEFINE_integer("max_bases", 5,
                     "Maximum number of bases.")
'''


def main():
    max_episode_length = 300
    gamma = 0.99
    load_model = False
    model_path = './model'
    flags = common.parse_args.parse_args()
    print(vars(flags))
    stopwatch.sw.enabled = flags.profile or flags.trace
    stopwatch.sw.trace = flags.trace

    agent_cls = agent.Smart
    action_space = Action_Space()
    maps.get(flags.map)

    if not os.path.exists(model_path):
        os.makedirs(model_path)

    tf.reset_default_graph()
    config = tf.ConfigProto(allow_soft_placement=True)

    with tf.device("/cpu:0"):
        global_episodes = tf.Variable(0, dtype=tf.int32, name="global_episodes", trainable=False)
        optimizer = tf.train.AdamOptimizer(learning_rate=0.005)
        master_network = agent.network.Policy('global', global_episodes, agent.policy_spec)
        # num_workers = psutil.cpu_count()
        num_workers = 1 # Hardcoded to one for quicker testing

        global _max_score, _running_avg_score, _steps, _episodes
        _max_score = 0
        _running_avg_score = 0
        _steps = np.zeros(num_workers)
        _episodes = np.zeros(num_workers)
        workers = []
        # Initialize workers
        for i in range(num_workers):
            env = sc2_env.SC2Env(
                    map_name=flags.map,
                    agent_race=flags.agent_race,
                    bot_race=flags.bot_race,
                    difficulty=flags.difficulty,
                    step_mul=flags.step_mul,
                    game_steps_per_episode=flags.game_steps_per_episode,
                    screen_size_px=(flags.screen_resolution, flags.screen_resolution),
                    minimap_size_px=(flags.minimap_resolution, flags.minimap_resolution),
                    visualize=flags.render)

            workers.append(Worker(
                name=i,
                main=sys.modules[__name__],
                env=env,
                actions=action_space,
                agent_cls=agent_cls,
                optimizer=optimizer,
                model_path=model_path,
                global_episodes=global_episodes,
                flags=flags,
                buffer_min=150,
                buffer_max=300))
        saver = tf.train.Saver(max_to_keep=5)

    with tf.Session(config=config) as sess:
        coord = tf.train.Coordinator()
        if load_model:
            print("Loading Model...")
            ckpt = tf.train.get_checkpoint_state(model_path)
            saver.restore(sess, ckpt.model_checkpoint_path)
        else:
            sess.run(tf.global_variables_initializer())

        worker_threads = []
        for worker in workers:
            t = threading.Thread(target=(lambda: worker.work(max_episode_length, sess, coord, saver)))
            t.start()
            sleep(0.25)
            worker_threads.append(t)
        coord.join(worker_threads)


if __name__ == "__main__":
    FLAGS(sys.argv)
    main()
