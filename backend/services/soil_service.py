def analyze_soil(data):

    score = 100
    problems = []

    # Nitrogen
    if data["N"] < 250:
        problems.append("Low nitrogen")
        score -= 15

    # Phosphorus
    if data["P"] < 20:
        problems.append("Low phosphorus")
        score -= 10

    # Potassium
    if data["K"] < 120:
        problems.append("Low potassium")
        score -= 10

    # pH
    if data["pH"] < 6.0:
        problems.append("Soil is acidic")
        score -= 10

    elif data["pH"] > 7.5:
        problems.append("Soil is alkaline")
        score -= 10

    # Organic Carbon
    if data["OC"] < 0.5:
        problems.append("Low organic carbon")
        score -= 15

    return {
        "soil_score": max(score, 0),
        "problems": problems
    }