"""
Soil Health Card reference ranges.

These are the rating limits commonly used for Indian Soil Health Cards and
soil-testing laboratories. They are GENERAL ratings – the right target for a
particular field also depends on crop, soil type and season, which is why the
soil service adds crop-specific notes (pH preference and salt sensitivity) on
top of these ratings.

Sources (for the project report):
  * Soil Health Card Scheme, Dept. of Agriculture & Farmers Welfare, GoI –
    parameter ratings printed on the card (N, P, K, OC, pH, EC).
  * Muhr et al. (1965) "Soil Testing in India" / ICAR soil-testing manuals –
    Low/Medium/High limits for available N, P, K and organic carbon.
  * Lindsay & Norvell (1978), Soil Sci. Soc. Am. J. 42:421-428 – DTPA
    critical limits for Zn, Fe, Cu, Mn (Indian labs commonly use
    Zn 0.6, Fe 4.5, Cu 0.2, Mn 2.0 mg/kg).
  * Berger & Truog (1939) hot-water-soluble boron; critical limit 0.5 mg/kg.
  * Williams & Steinbergs (1959) CaCl2 extractable sulphur; critical 10 mg/kg.
"""

# Units shown on the Soil Health Card.
UNITS = {
    "N": "kg/ha", "P": "kg/ha", "K": "kg/ha",
    "S": "mg/kg", "Zn": "mg/kg", "Fe": "mg/kg", "Cu": "mg/kg",
    "Mn": "mg/kg", "B": "mg/kg",
    "pH": "", "EC": "dS/m", "OC": "%",
}

LABELS = {
    "N": "Nitrogen (N)", "P": "Phosphorus (P)", "K": "Potassium (K)",
    "S": "Sulphur (S)", "Zn": "Zinc (Zn)", "Fe": "Iron (Fe)",
    "Cu": "Copper (Cu)", "Mn": "Manganese (Mn)", "B": "Boron (B)",
    "pH": "Soil pH", "EC": "Electrical Conductivity (EC)", "OC": "Organic Carbon (OC)",
}

# Macronutrients and organic carbon: Low / Medium / High.
LMH_LIMITS = {
    "N": (280, 560),     # available N, kg/ha (alkaline KMnO4 method)
    "P": (10, 25),       # available P, kg/ha (Olsen / Bray)
    "K": (110, 280),     # available K, kg/ha (NH4OAc)
    "OC": (0.50, 0.75),  # organic carbon, % (Walkley-Black)
}

# Secondary and micronutrients: critical (deficiency) limits in mg/kg.
CRITICAL_LIMITS = {
    "S": 10.0,
    "Zn": 0.6,
    "Fe": 4.5,
    "Cu": 0.2,
    "Mn": 2.0,
    "B": 0.5,
}

# Score weights – the main fertility indicators count more.
WEIGHTS = {
    "N": 1.5, "P": 1.5, "K": 1.5, "OC": 1.5, "pH": 1.5, "EC": 1.0,
    "S": 0.75, "Zn": 0.75, "Fe": 0.75, "Cu": 0.75, "Mn": 0.75, "B": 0.75,
}

# Why each parameter matters (farmer-friendly) and the generic next step.
# Next steps deliberately avoid fertilizer names and quantities: dose depends
# on crop, target yield and local recommendations.
PARAMETER_INFO = {
    "N": {
        "why": "Nitrogen helps leaves grow green and strong. Low nitrogen gives pale, yellow lower leaves and weak growth.",
        "low": "Ask your local Krishi Vigyan Kendra (KVK) or agriculture officer for the nitrogen dose for your crop. Adding compost or farmyard manure and growing legumes in rotation also builds soil nitrogen.",
        "high": "Avoid extra nitrogen this season. Too much nitrogen makes soft leafy growth that pests and leaf diseases attack more easily.",
    },
    "P": {
        "why": "Phosphorus is needed for roots, flowering and seed or fruit formation.",
        "low": "Phosphorus is usually applied at sowing or planting time. Ask your KVK or agriculture officer for the right dose for your crop.",
        "high": "Phosphorus is already high. Extra phosphorus is wasted money and can reduce zinc uptake.",
    },
    "K": {
        "why": "Potassium makes plants stronger against drought and disease and improves fruit and grain quality.",
        "low": "Ask your KVK or agriculture officer for the potassium dose for your crop. Returning crop residues and adding compost also supplies some potassium.",
        "high": "Potassium is sufficient. No extra potassium is needed this season.",
    },
    "OC": {
        "why": "Organic carbon shows how much organic matter the soil has. It holds water and nutrients and keeps soil life healthy.",
        "low": "Add farmyard manure, compost or vermicompost, keep crop residues in the field instead of burning them, and grow green manure crops when possible. These are low-cost ways to improve soil.",
        "high": "Organic matter is good. Keep adding residues and manure to maintain it.",
    },
    "S": {
        "why": "Sulphur is needed for protein formation. It is especially important for oilseeds and pulses.",
        "low": "Sulphur is below the critical level. Ask your agriculture officer which sulphur source is suitable for your crop.",
    },
    "Zn": {
        "why": "Zinc deficiency is very common in Indian soils. It causes stunted plants and small, pale or bronze leaves (for example 'khaira' in rice).",
        "low": "Zinc is below the critical level. Zinc deficiency is easy to correct. Ask your KVK for the recommended zinc application for your crop.",
    },
    "Fe": {
        "why": "Iron is needed to make green colour (chlorophyll). Deficiency causes yellowing between veins of young leaves, often in alkaline or calcareous soils.",
        "low": "Iron is below the critical level. Correcting soil pH and adding organic matter helps iron availability. Ask your KVK about foliar correction if symptoms appear.",
    },
    "Cu": {
        "why": "Copper is needed in small amounts for plant enzymes and grain formation.",
        "low": "Copper is below the critical level. Ask your agriculture officer whether correction is needed for your crop.",
    },
    "Mn": {
        "why": "Manganese is needed for photosynthesis. Deficiency causes yellow patches between leaf veins.",
        "low": "Manganese is below the critical level. Ask your agriculture officer whether correction is needed for your crop.",
    },
    "B": {
        "why": "Boron is needed for flowering, pollination and fruit or seed setting. Deficiency causes poor fruit set and cracked or hollow fruits.",
        "low": "Boron is below the critical level. Boron is needed in very small amounts and too much is harmful, so ask your KVK for the exact recommendation.",
    },
    "pH": {
        "why": "pH controls how easily plants can take up nutrients from the soil. Most crops prefer near-neutral soil.",
        "acidic": "Soil is acidic. Liming is the usual correction for strongly acidic soils. Ask your agriculture officer whether lime is needed and how much.",
        "alkaline": "Soil is alkaline. Adding organic matter helps. For strongly alkaline (sodic) soils, ask your agriculture officer about gypsum-based reclamation.",
    },
    "EC": {
        "why": "EC measures salt content in soil. High salts make it hard for roots to take up water and can damage sensitive crops.",
        "high": "Salt level is high. Good drainage, using good-quality irrigation water and choosing salt-tolerant crops help. Get your irrigation water tested if possible.",
    },
}
