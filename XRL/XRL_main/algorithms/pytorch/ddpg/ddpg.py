import sys
import math
import random
from copy import deepcopy
from this import d
import numpy as np
import torch
from torch.optim import Adam
import gym
import time

sys.path.append("/home/xhnfly/Cosmic_rays_X/XRL/")
import XRL_main.algorithms.pytorch.ddpg.core as core
from collections import namedtuple, deque


Transition = namedtuple('Transition',
                        ('obs', 'act', 'rew', 'next_obs', 'done'))

class ReplayMemory(object):

    def __init__(self, capacity):
        self.memory = deque([],maxlen=capacity)

    def push(self, *args):
        """Save a transition"""
        self.memory.append(Transition(*args))

    def sample(self, batch_size):
        return random.sample(self.memory, batch_size)

    def __len__(self):
        return len(self.memory)
    

def ddpg(env_fn, actor_critic=core.MLPActorCritic, ac_kwargs=dict(), seed=0, 
         steps_per_epoch=3000, epochs=100, replay_size=int(1e6), gamma=0.99, 
         polyak=0.995, pi_lr=1e-4, q_lr=1e-4, batch_size=500, start_steps=10000, 
         update_after=1000, update_every=50, act_noise=0.01, num_test_episodes=10, 
         max_ep_len=1000, device= torch.device("cuda" if torch.cuda.is_available() else "cpu")):


    torch.manual_seed(seed)
    np.random.seed(seed)
    env, test_env = env_fn(), env_fn()
    obs_dim = env.observation_space.shape[0]

    print('obs_dim = ', obs_dim)
    act_dim = env.action_space.shape[0]
    print('act_dim = ', act_dim)
    # Action limit for clamping: critically, assumes all dimensions share the same bound!
    act_limit = env.action_space.high[0]
    print('act_limit = ', act_limit)

    # Create actor-critic module and target networks
    ac = actor_critic(env.observation_space, env.action_space, **ac_kwargs)
    ac_targ = deepcopy(ac)

    # Freeze target networks with respect to optimizers (only update via polyak averaging)
    for p in ac_targ.parameters():
        p.requires_grad = False

    memory = ReplayMemory(replay_size)

    # Count variables (protip: try to get a feel for how different size networks behave!)
    var_counts = tuple(core.count_vars(module) for module in [ac.pi, ac.q])

    # Set up function for computing DDPG Q-loss
    def compute_loss_q(data):

        o = torch.cat(data.obs).float()
        a = torch.cat(data.act).float()
        r = torch.cat(data.rew).float()
        o2 =torch.cat(data.next_obs).float()
        d = torch.cat(data.done).float()

        q = ac.q(o,a)


        # Bellman backup for Q function
        with torch.no_grad():
            q_pi_targ = ac_targ.q(o2, ac_targ.pi(o2))
            backup = r + gamma * (1 - d) * q_pi_targ

        # MSE loss against Bellman backup
        loss_q = ((q - backup)**2).mean()

        return loss_q

    # Set up function for computing DDPG pi loss
    def compute_loss_pi(data):

        o = torch.cat(data.obs).float()

        q_pi = ac.q(o, ac.pi(o))

        return -q_pi.mean()

    pi_optimizer = Adam(ac.pi.parameters(), lr=pi_lr)
    q_optimizer = Adam(ac.q.parameters(), lr=q_lr)

    def update(data):
        # First run one gradient descent step for Q.


        q_optimizer.zero_grad()
        loss_q = compute_loss_q(data)

        loss_q.backward()

        q_optimizer.step()


        # Freeze Q-network so you don't waste computational effort 
        # computing gradients for it during the policy learning step.
        for p in ac.q.parameters():
            p.requires_grad = False

        # Next run one gradient descent step for pi.
        pi_optimizer.zero_grad()
        loss_pi = compute_loss_pi(data)
        loss_pi.backward()
        pi_optimizer.step()

        # Unfreeze Q-network so you can optimize it at next DDPG step.
        for p in ac.q.parameters():
            p.requires_grad = True


        # Finally, update target networks by polyak averaging.
        with torch.no_grad():
            for p, p_targ in zip(ac.parameters(), ac_targ.parameters()):
                # NB: We use an in-place operations "mul_", "add_" to update target
                # params, as opposed to "mul" and "add", which would make new tensors.
                p_targ.data.mul_(polyak)
                p_targ.data.add_((1 - polyak) * p.data)


    def get_action(o, noise_scale):
        a = ac.act(torch.tensor(o, dtype=torch.float32, device=device))
        a += noise_scale * torch.randn(act_dim).to(device)
        return torch.clip(a, -act_limit, act_limit)

    def test_agent():
        for j in range(num_test_episodes):
            o, d, ep_ret, ep_len = test_env.reset(), False, 0, 0
            while not(d or (ep_len == max_ep_len)):
                # Take deterministic actions at test time (noise_scale=0)
                a_cpu = get_action(o, 0).cpu().data.numpy()
                o, r, d, _ = test_env.step(a_cpu)
                ep_ret += r
                ep_len += 1

    


    # Prepare for interaction with environment
    total_steps = steps_per_epoch * epochs
    start_time = time.time()
    o, ep_ret, ep_len = env.reset(), 0, 0
    o = torch.tensor([o], device=device)


    # Main loop: collect experience in env and update/log each epoch
    for t in range(total_steps):

        
        # Until start_steps have elapsed, randomly sample actions
        # from a uniform distribution for better exploration. Afterwards, 
        # use the learned policy (with some noise, via act_noise). 
        if t > start_steps:
            a = get_action(o, act_noise)
            a_cpu = a.cpu().data.numpy()
        else:
            a = env.action_space.sample()
            a_cpu = a
            a = torch.tensor([a], device=device)
        # Step the env
        o2, r, d, _ = env.step(a_cpu)
        ep_ret += r
        ep_len += 1
        ep_ret_main = ep_ret/ep_len


        # Ignore the "done" signal if it comes from hitting the time
        # horizon (that is, when it's an artificial terminal signal
        # that isn't based on the agent's state)
        d = False if ep_len==max_ep_len else d

        # a = torch.tensor([a], device=device)
        o2 = torch.tensor([o2], device=device)
        r = torch.tensor([r], device=device)
        d = torch.tensor([d], device=device)

        # Store experience to replay buffer
        memory.push(o, a, r, o2, d)
        # Super critical, easy to overlook step: make sure to update 
        # most recent observation!
        o=o2

        # End of trajectory handling
        if d or (ep_len == max_ep_len):
            o, ep_ret, ep_len = env.reset(), 0, 0
            o = torch.tensor([o], device=device)


        # Update handling
        if t >= update_after and t % update_every == 0:
            print('t = ', t)
            print('main od rewards = ', ep_ret_main)
            for i in range(update_every):

                transitions = memory.sample(batch_size)
                # Transpose the batch (see https://stackoverflow.com/a/19343/3343043 for
                # detailed explanation). This converts batch-array of Transitions
                # to Transition of batch-arrays.
                batch = Transition(*zip(*transitions))

                # print('batch = ', str(batch))
                update(data=batch)

        # End of epoch handling
        if (t+1) % steps_per_epoch == 0:
            epoch = (t+1) // steps_per_epoch

            # Test the performance of the deterministic version of the agent.
            test_agent()



if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--env', type=str, default='Reacher-v2')
    # parser.add_argument('--env', type=str, default='CartPole-v0')
    parser.add_argument('--hid', type=int, default=256)
    parser.add_argument('--l', type=int, default=2)
    parser.add_argument('--gamma', type=float, default=0.99)
    parser.add_argument('--seed', '-s', type=int, default=0)
    parser.add_argument('--epochs', type=int, default=50)
    parser.add_argument('--exp_name', type=str, default='ddpg')
    args = parser.parse_args()

    ddpg(lambda : gym.make(args.env), actor_critic=core.MLPActorCritic,
         ac_kwargs=dict(hidden_sizes=[args.hid]*args.l), 
         gamma=args.gamma, seed=args.seed, epochs=args.epochs, 
         device= torch.device("cuda" if torch.cuda.is_available() else "cpu"))

