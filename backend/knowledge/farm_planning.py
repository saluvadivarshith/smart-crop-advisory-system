"""
Planning attributes used by the "Start a New Farm" crop recommender.

These are deliberately simple, relative ratings (low / medium / high) so a
first-time farmer can understand WHY a crop is or is not suggested. They are
general Indian smallholder characteristics, not guarantees for a specific
field. Spacing values are typical package-of-practices values; the variety
packet and the local KVK recommendation always take priority.

Sources (for the project report):
  * Seasons: Directorate of Economics & Statistics / ICAR crop calendars
    (Kharif ~ June–October, Rabi ~ October/November–March, Zaid ~ March–June).
  * Water, duration, spacing, sowing method: ICAR institute and State
    Agricultural University package-of-practices (e.g. TNAU Agritech portal,
    ICAR-IIPR pulses, ICAR-IIMR millets, ICAR-IIVR vegetables).
"""

SEASONS = {
    "kharif": {
        "name": "Kharif (Monsoon season)",
        "sow_months": [6, 7],
        "grow_months": [6, 7, 8, 9, 10],
        "about": "Sown with the onset of the south-west monsoon (June–July) and harvested around October.",
    },
    "rabi": {
        "name": "Rabi (Winter season)",
        "sow_months": [10, 11, 12],
        "grow_months": [11, 12, 1, 2, 3],
        "about": "Sown after the monsoon (October–December) and harvested around March–April.",
    },
    "zaid": {
        "name": "Zaid (Summer season)",
        "sow_months": [2, 3, 4],
        "grow_months": [3, 4, 5, 6],
        "about": "Short summer season between Rabi and Kharif (March–June). Needs irrigation.",
    },
}

LEVEL = {"low": 1, "medium": 2, "high": 3}

# Planning attributes for every crop the new-farm recommender may suggest.
# perennial / orchard crops are intentionally excluded from first-season suggestions.
CROP_PLANNING = {
    "rice":       {"seasons": ["kharif", "rabi"], "water": "high", "cost": "medium", "labour": "high", "beginner": 2, "method": "transplant", "spacing": "20 × 15 cm", "category": "cereal"},
    "wheat":      {"seasons": ["rabi"], "water": "medium", "cost": "medium", "labour": "low", "beginner": 2, "method": "direct sowing in lines", "spacing": "rows 22.5 cm apart", "category": "cereal"},
    "maize":      {"seasons": ["kharif", "rabi"], "water": "medium", "cost": "medium", "labour": "medium", "beginner": 3, "method": "direct sowing", "spacing": "60 × 20 cm", "category": "cereal"},
    "cotton":     {"seasons": ["kharif"], "water": "medium", "cost": "high", "labour": "high", "beginner": 1, "method": "direct sowing (dibbling)", "spacing": "90 × 60 cm", "category": "fibre"},
    "tomato":     {"seasons": ["kharif", "rabi"], "water": "medium", "cost": "high", "labour": "high", "beginner": 1, "method": "nursery + transplant", "spacing": "60 × 45 cm", "category": "vegetable"},
    "potato":     {"seasons": ["rabi"], "water": "medium", "cost": "high", "labour": "medium", "beginner": 1, "method": "seed tubers on ridges", "spacing": "60 × 20 cm", "category": "vegetable"},
    "chilli":     {"seasons": ["kharif", "rabi"], "water": "medium", "cost": "high", "labour": "high", "beginner": 1, "method": "nursery + transplant", "spacing": "60 × 45 cm", "category": "vegetable"},
    "pepper":     {"seasons": ["rabi"], "water": "medium", "cost": "high", "labour": "high", "beginner": 1, "method": "nursery + transplant", "spacing": "60 × 45 cm", "category": "vegetable"},
    "groundnut":  {"seasons": ["kharif", "rabi", "zaid"], "water": "low", "cost": "medium", "labour": "medium", "beginner": 3, "method": "direct sowing", "spacing": "30 × 10 cm", "category": "oilseed", "legume": True},
    "soybean":    {"seasons": ["kharif"], "water": "low", "cost": "low", "labour": "low", "beginner": 3, "method": "direct sowing", "spacing": "45 × 5 cm", "category": "oilseed", "legume": True},
    "red_gram":   {"seasons": ["kharif"], "water": "low", "cost": "low", "labour": "low", "beginner": 3, "method": "direct sowing", "spacing": "90 × 20 cm", "category": "pulse", "legume": True},
    "green_gram": {"seasons": ["kharif", "zaid"], "water": "low", "cost": "low", "labour": "medium", "beginner": 3, "method": "direct sowing", "spacing": "30 × 10 cm", "category": "pulse", "legume": True},
    "black_gram": {"seasons": ["kharif", "rabi"], "water": "low", "cost": "low", "labour": "medium", "beginner": 3, "method": "direct sowing", "spacing": "30 × 10 cm", "category": "pulse", "legume": True},
    "chickpea":   {"seasons": ["rabi"], "water": "low", "cost": "low", "labour": "low", "beginner": 3, "method": "direct sowing", "spacing": "30 × 10 cm", "category": "pulse", "legume": True},
    "onion":      {"seasons": ["kharif", "rabi"], "water": "medium", "cost": "medium", "labour": "high", "beginner": 2, "method": "nursery + transplant", "spacing": "15 × 10 cm", "category": "vegetable"},
    "brinjal":    {"seasons": ["kharif", "rabi", "zaid"], "water": "medium", "cost": "medium", "labour": "medium", "beginner": 2, "method": "nursery + transplant", "spacing": "60 × 60 cm", "category": "vegetable"},
    "okra":       {"seasons": ["kharif", "zaid"], "water": "medium", "cost": "medium", "labour": "high", "beginner": 3, "method": "direct sowing", "spacing": "45 × 30 cm", "category": "vegetable"},
    "jowar":      {"seasons": ["kharif", "rabi"], "water": "low", "cost": "low", "labour": "low", "beginner": 3, "method": "direct sowing", "spacing": "45 × 15 cm", "category": "millet"},
    "bajra":      {"seasons": ["kharif", "zaid"], "water": "low", "cost": "low", "labour": "low", "beginner": 3, "method": "direct sowing", "spacing": "45 × 15 cm", "category": "millet"},
    "ragi":       {"seasons": ["kharif"], "water": "low", "cost": "low", "labour": "medium", "beginner": 3, "method": "direct sowing or transplant", "spacing": "22.5 × 10 cm", "category": "millet"},
}

WATER_SOURCES = {
    "rain_only": {"label": "Rain only (no well or canal)", "level": 1},
    "limited":   {"label": "Limited irrigation (shared well, tank, or a few waterings)", "level": 2},
    "assured":   {"label": "Assured irrigation (own borewell or canal)", "level": 3},
}
BUDGETS = {
    "low":    {"label": "Low — must keep costs minimal", "level": 1},
    "medium": {"label": "Medium", "level": 2},
    "high":   {"label": "Can invest more for higher-value crops", "level": 3},
}
LABOUR = {
    "self":   {"label": "Mostly just me", "level": 1},
    "family": {"label": "Family members help", "level": 2},
    "hired":  {"label": "Can hire workers when needed", "level": 3},
}

# Government support verified against official portals. Eligibility details
# change, so each entry tells the farmer to confirm on the official site.
SCHEMES = [
    {
        "name": "Kisan Call Centre",
        "what": "Free phone advice from agriculture experts in your language, 6 AM–10 PM, all days.",
        "how": "Call toll-free 1800-180-1551.",
        "link": None,
    },
    {
        "name": "Krishi Vigyan Kendra (KVK)",
        "what": "Your district's farm science centre: free training, soil testing help, seeds and bio-inputs, and crop-specific advice.",
        "how": "Find your district KVK on the official KVK portal.",
        "link": "https://kvk.icar.gov.in/",
    },
    {
        "name": "Soil Health Card Scheme",
        "what": "Free soil testing with a card showing your soil's nutrients and fertilizer recommendations for your crops.",
        "how": "Contact your agriculture officer or KVK to get a soil sample collected and tested.",
        "link": "https://soilhealth.dac.gov.in/",
    },
    {
        "name": "PM-KISAN",
        "what": "Income support of ₹6,000 per year in three instalments to eligible land-holding farmer families.",
        "how": "Register through the PM-KISAN portal or your nearest Common Service Centre (CSC). Land records must be in your name.",
        "link": "https://pmkisan.gov.in/",
    },
    {
        "name": "Pradhan Mantri Fasal Bima Yojana (PMFBY)",
        "what": "Low-premium crop insurance against crop loss from natural calamities, pests and diseases.",
        "how": "Enrol before the season's cut-off date through a bank, CSC, or the PMFBY portal.",
        "link": "https://pmfby.gov.in/",
    },
    {
        "name": "Kisan Credit Card (KCC)",
        "what": "Low-interest short-term crop loans for seeds, fertilizer and other farm costs.",
        "how": "Apply at your bank branch or cooperative bank with land and identity documents. Search 'Kisan Credit Card' on the myScheme portal for current details.",
        "link": "https://www.myscheme.gov.in/",
    },
    {
        "name": "e-NAM and Agmarknet (market prices)",
        "what": "Check current mandi prices before choosing a crop and when selling your produce.",
        "how": "Look up your nearest mandi's prices online.",
        "link": "https://agmarknet.gov.in/",
    },
]
