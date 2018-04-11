from base_agent import BaseAgent
import observer
import network
hidden_layer_size = (3*observer.observation_size)//2

policy_spec = network.Policy.policy_spec(
            input_size=20,
            num_actions=800,
            max_episodes=2500,
            q_range=(30, 31),
            hidden_layer_size=30,
            base_explore_rate=0.1,                 
            min_explore_rate=0.01)
trainer_spec = network.Trainer.trainer_spec()


class Smart(BaseAgent):
    def __init__(self, name, parent, optimizer, episode, action_space, flags):
        policy_spec.update(action_space.action_spec)
        super().__init__(name, parent, optimizer, network, episode, policy_spec, trainer_spec)
        self.action_space = action_space
        self.flags = flags

    def process_observation(self, obs):
        return observer.process_observation(obs, self.action_space, self.flags)
