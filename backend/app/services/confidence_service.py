CONFIDENCE_WEIGHTS = {1: 0.05, 2: 0.5, 3: 1.0, 4: 1.0, 5: 1.0}


def response_weight(confidence: int) -> float:
    if confidence not in CONFIDENCE_WEIGHTS:
        raise ValueError("Confidence must be between 1 and 5")
    return CONFIDENCE_WEIGHTS[confidence]
