import math

from app.services.confidence_service import response_weight


def probability_correct(theta: float, b: float) -> float:
    return 1 / (1 + math.exp(-(theta - b)))


def update_theta(theta: float, observed: int, b: float, learning_rate: float = 0.5, confidence: int = 3) -> tuple[float, float]:
    probability = probability_correct(theta, b)
    weight = response_weight(confidence)
    if confidence == 1 and observed == 1:
        weight = 0.0
    updated = theta + learning_rate * weight * (observed - probability)
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
