from utils import parse_args
import psutil
import os
import threading
import numpy as np
import tensorflow as tf

from pysc2 import maps
from pysc2.lib import stopwatch
from time import sleep
from worker import Worker
from dummy import Dummy
import agent

global _max_score, _running_avg_score, _steps, _episodes
# noinspection PyRedeclaration
_max_score = _running_avg_score = 0
# noinspection PyRedeclaration
_steps = _episodes = []


def main():
    max_episode_length = 300
    gamma = 0.99
    load_model = False
    model_path = './model'
    flags = parse_args()
    stopwatch.sw.enabled = flags.profile or flags.trace
    stopwatch.sw.trace = flags.trace

    agent_cls = agent.Smart
    maps.get(flags.map or Dummy.map_name)

    if not os.path.exists(model_path):
        os.makedirs(model_path)

    tf.reset_default_graph()
    config = tf.ConfigProto(
        allow_soft_placement=True,
        intra_op_parallelism_threads=flags.num_envs,
        inter_op_parallelism_threads=flags.num_envs)
    config.gpu_options.allow_growth = True

    global_episodes = tf.Variable(0, dtype=tf.int32, name="global_episodes", trainable=False)
    optimizer = tf.train.AdamOptimizer(learning_rate=0.001)
    master_network = agent.network.Policy('global', agent.network_spec)
    num_workers = psutil.cpu_count()

    global _max_score, _running_avg_score, _steps, _episodes
    _max_score = 0
    _running_avg_score = 0
    _steps = np.zeros(num_workers)
    _episodes = np.zeros(num_workers)
    workers = []
    # Initialize workers
    for i in range(num_workers):
        workers.append(Worker(i, agent_cls, optimizer, model_path, 30, global_episodes, flags.map_name, flags))
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
            t = threading.Thread(target=(lambda: worker.work(max_episode_length, gamma, sess, coord, saver)))
            t.start()
            sleep(0.25)
            worker_threads.append(t)
        coord.join(worker_threads)