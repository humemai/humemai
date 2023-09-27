"""DQN Agent for the RoomEnv2 environment."""
import datetime
import os
import random
import shutil
from copy import deepcopy
from typing import Dict, List, Tuple

import gymnasium as gym
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn.functional as F
import torch.optim as optim
from IPython.display import clear_output
from tqdm.auto import tqdm, trange

from explicit_memory.memory import (
    EpisodicMemory,
    SemanticMemory,
    ShortMemory,
    MemorySystems,
)
from explicit_memory.nn import LSTM
from explicit_memory.policy import (
    answer_question,
    encode_observation,
    manage_memory,
    explore,
)
from explicit_memory.utils import ReplayBuffer, is_running_notebook, write_yaml
from ..handcrafted import HandcraftedAgent


class DQNAgent(HandcraftedAgent):
    """DQN Agent interacting with environment.

    Based on https://github.com/Curt-Park/rainbow-is-all-you-need/blob/master/01.dqn.ipynb
    """

    def __init__(
        self,
        env_str: str = "room_env:RoomEnv-v2",
        num_iterations: int = 1000,
        replay_buffer_size: int = 102400,
        warm_start: int = 102400,
        batch_size: int = 1024,
        target_update_rate: int = 10,
        epsilon_decay_until: float = 2048,
        max_epsilon: float = 1.0,
        min_epsilon: float = 0.1,
        gamma: float = 0.65,
        capacity: dict = {
            "episodic": 16,
            "semantic": 16,
            "short": 16,
        },
        pretrain_semantic: bool = False,
        nn_params: dict = {
            "hidden_size": 64,
            "num_layers": 2,
            "n_actions": 5,
            "embedding_dim": 32,
            "v1_params": None,
            "v2_params": {},
        },
        run_validation: bool = True,
        run_test: bool = True,
        num_samples_for_results: int = 10,
        plotting_interval: int = 10,
        train_seed: int = 5,
        test_seed: int = 0,
        device: str = "cpu",
        memory_management_policy: str = "generalize",
        qa_policy: str = "episodic_semantic",
        explore_policy: str = "avoid_walls",
        room_size: str = "dev",
        question_prob: float = 1.0,
        terminates_at: int = 99,
    ):
        """Initialization.

        Args
        ----
        env_str: This has to be "room_env:RoomEnv-v2"
        num_iterations: The number of iterations to train the agent.
        replay_buffer_size: The size of the replay buffer.
        warm_start: The number of samples to fill the replay buffer with, before
            starting
        batch_size: The batch size for training This is the amount of samples sampled
            from the replay buffer.
        target_update_rate: The rate to update the target network.
        epsilon_decay_until: The iteration index until which to decay epsilon.
        max_epsilon: The maximum epsilon.
        min_epsilon: The minimum epsilon.
        gamma: The discount factor.
        capacity: The capacity of each human-like memory systems.
        pretrain_semantic: Whether or not to pretrain the semantic memory system.
        nn_params: The parameters for the DQN (function approximator).
        run_validation: Whether or not to run validation.
        run_test: Whether or not to run test.
        num_samples_for_results: The number of samples to validate / test the agent.
        plotting_interval: The interval to plot the results.
        train_seed: The random seed for train.
        test_seed: The random seed for test.
        device: The device to run the agent on. This is either "cpu" or "cuda".
        memory_management_policy: Memory management policy. Choose one of "generalize",
            "random", "rl", or "neural"
        qa_policy: question answering policy Choose one of "episodic_semantic",
            "random", "rl", or "neural"
        explore_policy: The room exploration policy. Choose one of "random",
            "avoid_walls", "rl", or "neural"
        room_size: The room configuration to use. Choose one of "dev", "xxs", "xs",
            "s", "m", or "l".
        question_prob: The probability of a question being asked at every observation.
        terminates_at: The maximum number of steps to take in an episode.

        """
        self.all_params = deepcopy(locals())
        del self.all_params["self"]
        del self.all_params["__class__"]
        self.room_size = room_size
        self.question_prob = question_prob
        self.terminates_at = terminates_at
        env_config = {
            "seed": train_seed,
            "question_prob": self.question_prob,
            "terminates_at": self.terminates_at,
            "room_size": self.room_size,
        }
        self.memory_management_policy = memory_management_policy
        self.qa_policy = qa_policy
        self.explore_policy = explore_policy

        super().__init__(
            env_str=env_str,
            env_config=env_config,
            memory_management_policy=self.memory_management_policy,
            qa_policy=self.qa_policy,
            explore_policy=self.explore_policy,
            num_samples_for_results=num_samples_for_results,
            capacity=capacity,
        )
        self.train_seed = train_seed
        self.test_seed = test_seed

        self.val_filenames = []
        self.is_notebook = is_running_notebook()
        self.num_iterations = num_iterations
        self.plotting_interval = plotting_interval
        self.run_validation = run_validation
        self.run_test = run_test
        self.device = torch.device(device)
        print(f"Running on {self.device}")

        self.replay_buffer_size = replay_buffer_size
        self.batch_size = batch_size
        self.epsilon = max_epsilon
        self.max_epsilon = max_epsilon
        self.min_epsilon = min_epsilon
        self.epsilon_decay_until = epsilon_decay_until
        self.target_update_rate = target_update_rate
        self.gamma = gamma
        self.warm_start = warm_start
        assert self.batch_size <= self.warm_start <= self.replay_buffer_size

        self.nn_params = nn_params
        self.nn_params["capacity"] = self.capacity
        self.nn_params["device"] = self.device
        self.nn_params["entities"] = self.env.entities
        self.nn_params["relations"] = self.env.relations

        # networks: dqn, dqn_target
        self.dqn = LSTM(**self.nn_params)
        self.dqn_target = LSTM(**self.nn_params)
        self.dqn_target.load_state_dict(self.dqn.state_dict())
        self.dqn_target.eval()

        self.replay_buffer = ReplayBuffer(
            observation_type="dict", size=replay_buffer_size, batch_size=batch_size
        )

        # optimizer
        self.optimizer = optim.Adam(self.dqn.parameters())

        # transition to store in replay buffer
        self.transition = list()

        self.pretrain_semantic = pretrain_semantic
        self.action_explore2str = {
            0: "north",
            1: "east",
            2: "south",
            3: "west",
            4: "stay",
        }

    def select_action(self, state: dict, greedy: bool = False) -> int:
        """Select an action from the input state using epsilon greedy policy

        Args
        ----
        state: The current state of the memory systems. This is NOT what the gym env
            gives you. This is made by the agent.
        greedy: always pick greedy action if True

        Returns
        -------
        selected_action: The selected action.


        """
        if self.epsilon < np.random.random() or greedy:
            selected_action = self.dqn(np.array([state])).argmax()
            selected_action = selected_action.detach().cpu().numpy().item()

        else:
            selected_action = self.action_space.sample()

        return selected_action

    def step(self, action: int) -> Tuple[int, bool]:
        """Take an action and return reward, done.

        Args
        ----
        action: The action to take.

        Returns
        -------
        reward: The reward for the action.
        done: Whether or not the episode ends.

        """
        pass

    def update_model(self) -> torch.Tensor:
        """Update the model by gradient descent."""
        samples = self.replay_buffer.sample_batch()

        loss = self._compute_dqn_loss(samples)

        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        return loss.item()

    def train(self):
        """Train the agent."""
        pass

    def choose_best_val(self, filenames: list):
        scores = []
        for filename in filenames:
            scores.append(int(filename.split("val-score=")[-1].split(".pt")[0]))
        return filenames[scores.index(max(scores))]

    def validate(self) -> None:
        """Validate the agent."""
        pass

    def test(self, checkpoint: str = None) -> None:
        """Test the agent.

        Args
        ----
        checkpoint: The checkpoint to load the model from. If None, the model from the
            best validation is used.

        """
        pass

    def _compute_dqn_loss(self, samples: Dict[str, np.ndarray]) -> torch.Tensor:
        """Return dqn loss.

        Args
        ----
        samples: A dictionary of samples from the replay buffer.
            obs: np.ndarray,
            act: np.ndarray,
            rew: float,
            next_obs: np.ndarray,
            done: bool,
        """
        state = samples["obs"]
        next_state = samples["next_obs"]
        action = torch.LongTensor(samples["acts"].reshape(-1, 1)).to(self.device)
        reward = torch.FloatTensor(samples["rews"].reshape(-1, 1)).to(self.device)
        done = torch.FloatTensor(samples["done"].reshape(-1, 1)).to(self.device)

        # G_t   = r + gamma * v(s_{t+1})  if state != Terminal
        #       = r                       otherwise
        curr_q_value = self.dqn(state).gather(1, action)
        next_q_value = self.dqn_target(next_state).max(dim=1, keepdim=True)[0].detach()
        mask = 1 - done
        target = (reward + self.gamma * next_q_value * mask).to(self.device)

        # calculate dqn loss
        loss = F.smooth_l1_loss(curr_q_value, target)

        return loss

    def _target_hard_update(self):
        """Hard update: target <- local."""
        self.dqn_target.load_state_dict(self.dqn.state_dict())

    def _plot(self):
        """Plot the training progresses."""
        clear_output(True)
        plt.figure(figsize=(20, 8))

        if self.scores["train"]:
            plt.subplot(234)
            plt.title(
                f"iteration {self.iteration_idx} out of {self.num_iterations}. "
                f"training score: {self.scores['train'][-1]} out of "
                f"{self.max_total_rewards}"
            )
            plt.plot(self.scores["train"])
            plt.xlabel("episode")

        if self.scores["validation"]:
            plt.subplot(235)
            val_means = [
                round(np.mean(scores).item()) for scores in self.scores["validation"]
            ]
            plt.title(
                f"validation score: {val_means[-1]} out of {self.max_total_rewards}"
            )
            plt.plot(val_means)
            plt.xlabel("episode")

        if self.scores["test"]:
            plt.subplot(236)
            plt.title(
                f"test score: {np.mean(self.scores['test'])} out of "
                f"{self.max_total_rewards}"
            )
            plt.plot(round(np.mean(self.scores["test"]).item(), 2))
            plt.xlabel("episode")

        plt.subplot(231)
        plt.title("training loss")
        plt.plot(self.training_loss)
        plt.xlabel("update counts")

        plt.subplot(232)
        plt.title("epsilons")
        plt.plot(self.epsilons)
        plt.xlabel("update counts")

        plt.subplots_adjust(hspace=0.5)
        plt.savefig(f"{self.default_root_dir}/plot.png")
        plt.show()

        if not self.is_notebook:
            self._console()

    def _console(self):
        """Print the training progresses to the console."""
        if self.scores["train"]:
            tqdm.write(
                f"iteration {self.iteration_idx} out of {self.num_iterations}.\n"
                f"episode {self.num_validation} training score: "
                f"{self.scores['train'][-1]} out of {self.max_total_rewards}"
            )

        if self.scores["validation"]:
            val_means = [
                round(np.mean(scores).item()) for scores in self.scores["validation"]
            ]
            tqdm.write(
                f"episode {self.num_validation} validation score: {val_means[-1]} "
                f"out of {self.max_total_rewards}"
            )

        if self.scores["test"]:
            tqdm.write(
                f"test score: {np.mean(self.scores['test'])} out of "
                f"{self.max_total_rewards}"
            )

        tqdm.write(
            f"training loss: {self.training_loss[-1]}\nepsilons: {self.epsilons[-1]}\n"
        )
