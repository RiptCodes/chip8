"""Reward + feature extraction for Pong: keep the paddle level with the ball."""
import numpy as np


def find_positions(obs):
    """Returns (ball_x, ball_y, paddle_y), any of which may be None."""
    paddle_rows = np.where(obs[:, 0] == 1)[0]
    paddle_y = paddle_rows.mean() if len(paddle_rows) else None

    # ball = anything in the field once paddles and score digits are masked out
    field = obs[:, 2:63].astype(np.uint8).copy()
    field[0:6, 10:50] = 0
    ball_pos = np.argwhere(field)
    if len(ball_pos):
        ball_y = ball_pos[:, 0].mean()
        ball_x = ball_pos[:, 1].mean() + 2
    else:
        ball_y = ball_x = None
    return ball_x, ball_y, paddle_y


def shaped_reward(obs):
    _, ball_y, paddle_y = find_positions(obs)
    if ball_y is None or paddle_y is None:
        return 0.0
    return 1.0 - abs(ball_y - paddle_y) / 32.0
