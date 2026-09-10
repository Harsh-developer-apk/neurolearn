import math


def probability_correct(theta: float, b: float) -> float:
    return 1 / (1 + math.exp(-(theta - b)))


def update_theta(theta: float, observed: int, b: float, learning_rate: float = 0.5) -> tuple[float, float]:
    probability = probability_correct(theta, b)
    updated = theta + learning_rate * (observed - probability)
    return clamp_theta(updated), probability


def clamp_theta(theta: float) -> float:
    return max(-3.0, min(3.0, theta))


def ability_label(theta: float) -> str:
    if theta < -1:
        return "Needs Foundation"
    if theta < -0.25:
        return "Developing"
    if theta <= 0.75:
        return "Working"
    if theta <= 1.5:
        return "Proficient"
    return "Advanced"
