"""
Farm input knowledge base for the "What to Buy" guide.

DESIGN RULES (kept from the rest of the project):
  1. Fertilizer quantities are CALCULATED transparently from (a) a crop's
     general recommended N-P2O5-K2O dose and (b) the nutrient content of
     standard fertilizers. The farmer's own Soil Health Card recommendation,
     if entered, always replaces the general dose.
  2. Pesticides, fungicides and herbicides are recommended only as an
     IPM sequence: cultural practice -> monitoring tools -> biological /
     botanical options -> "registered chemical, if needed". The app never
     names a chemical pesticide or herbicide and never gives a chemical dose,
     because registration, banned lists and label doses vary by crop and
     state and change over time. The farmer is sent to a licensed dealer /
     KVK and told to follow the label.

Sources (for the project report):
  * Fertilizer nutrient content: Fertilizer (Control) Order, 1985, GoI
    (Urea 46% N; DAP 18% N + 46% P2O5; MOP 60% K2O; SSP 16% P2O5 with about
    11% S; zinc sulphate heptahydrate 21% Zn).
  * General recommended doses (RDF): ICAR / State Agricultural University
    package-of-practices. These vary by state, variety and irrigation, so the
    app labels them "general" and asks the farmer to prefer their Soil Health
    Card or KVK figure.
  * Soil-test adjustment (+25% for Low, -25% for High soil rating): the
    soil-test-based fertility-rating approach used by Indian soil-testing
    laboratories (ICAR soil-testing manuals).
  * IPM tools and bio-agents: ICAR-National Research Centre for Integrated
    Pest Management (NCIPM) and Directorate of Plant Protection, Quarantine &
    Storage (DPPQS) IPM packages.
"""

# Standard fertilizers: nutrient fraction and common bag size (kg).
FERTILIZERS = {
    "urea": {"name": "Urea", "N": 0.46, "P2O5": 0.0, "K2O": 0.0, "S": 0.0, "bag_kg": 45},
    "dap":  {"name": "DAP (Di-Ammonium Phosphate)", "N": 0.18, "P2O5": 0.46, "K2O": 0.0, "S": 0.0, "bag_kg": 50},
    "ssp":  {"name": "SSP (Single Super Phosphate)", "N": 0.0, "P2O5": 0.16, "K2O": 0.0, "S": 0.11, "bag_kg": 50},
    "mop":  {"name": "MOP (Muriate of Potash)", "N": 0.0, "P2O5": 0.0, "K2O": 0.60, "S": 0.0, "bag_kg": 50},
}

# General recommended fertilizer dose, kg/ha of N, P2O5, K2O.
# Indicative values only – see module docstring.
GENERAL_RDF = {
    "rice": (120, 60, 40),
    "wheat": (120, 60, 40),
    "maize": (120, 60, 40),
    "cotton": (100, 50, 50),
    "tomato": (100, 50, 50),
    "potato": (150, 80, 100),
    "chilli": (120, 60, 60),
    "pepper": (120, 60, 60),
    "groundnut": (20, 40, 40),
    "soybean": (20, 60, 40),
    "red_gram": (20, 50, 0),
    "green_gram": (20, 40, 0),
    "black_gram": (20, 40, 0),
    "chickpea": (20, 40, 20),
    "onion": (100, 50, 50),
    "brinjal": (100, 50, 50),
    "okra": (100, 50, 50),
    "jowar": (80, 40, 40),
    "bajra": (60, 30, 30),
    "ragi": (60, 30, 30),
}

LEGUMES = {"groundnut", "soybean", "red_gram", "green_gram", "black_gram", "chickpea"}
OILSEEDS = {"groundnut", "soybean"}

# Common pests per crop and the low-cost monitoring tool that fits them.
CROP_PESTS = {
    "tomato": [("Fruit borer", "pheromone_trap"), ("Whitefly (spreads leaf curl virus)", "yellow_trap")],
    "chilli": [("Thrips", "blue_trap"), ("Whitefly and aphids", "yellow_trap"), ("Fruit borer", "pheromone_trap")],
    "pepper": [("Thrips", "blue_trap"), ("Aphids", "yellow_trap")],
    "brinjal": [("Shoot and fruit borer", "pheromone_trap"), ("Whitefly", "yellow_trap")],
    "okra": [("Fruit borer", "pheromone_trap"), ("Whitefly and jassids (spread yellow vein mosaic)", "yellow_trap")],
    "cotton": [("Pink bollworm", "pheromone_trap"), ("Whitefly and jassids", "yellow_trap")],
    "maize": [("Fall armyworm", "pheromone_trap")],
    "rice": [("Yellow stem borer", "pheromone_trap")],
    "groundnut": [("Tobacco caterpillar (Spodoptera)", "pheromone_trap")],
    "soybean": [("Tobacco caterpillar (Spodoptera)", "pheromone_trap")],
    "red_gram": [("Pod borer", "pheromone_trap"), ("Pod borer (natural control by birds)", "bird_perch")],
    "chickpea": [("Pod borer", "pheromone_trap"), ("Pod borer (natural control by birds)", "bird_perch")],
    "green_gram": [("Whitefly (spreads yellow mosaic virus)", "yellow_trap")],
    "black_gram": [("Whitefly (spreads yellow mosaic virus)", "yellow_trap")],
    "onion": [("Thrips", "blue_trap")],
    "potato": [("Aphids", "yellow_trap"), ("Potato tuber moth", "pheromone_trap")],
    "wheat": [("Aphids", "yellow_trap")],
}

MONITORING_TOOLS = {
    "yellow_trap": {"name": "Yellow sticky traps", "why": "Attract and trap whiteflies, aphids and jassids so you can see when they increase.", "how": "Hang at or just above crop height. Replace when covered with insects."},
    "blue_trap": {"name": "Blue sticky traps", "why": "Attract and trap thrips.", "how": "Hang at crop height. Replace when covered."},
    "pheromone_trap": {"name": "Pheromone traps with crop-specific lures", "why": "Catch male moths of borers and caterpillars. Rising catches warn you before damage becomes heavy.", "how": "Buy the lure meant for your crop's pest. Change lures as written on the pack."},
    "bird_perch": {"name": "Bird perches (T-shaped sticks)", "why": "Birds sitting on them eat pod borer caterpillars. Practically free.", "how": "Place a few T-shaped sticks slightly above the crop before flowering."},
}

# Biological / botanical options by problem type (no chemical names).
BIO_OPTIONS = {
    "fungal_leaf": [
        ("Pseudomonas fluorescens (bio-fungicide)", "A beneficial bacterium used against many leaf spots and blights."),
    ],
    "soil_borne": [
        ("Trichoderma (bio-fungicide)", "A beneficial fungus for seed and soil treatment against wilt, root rot and damping-off."),
    ],
    "sucking_pest": [
        ("Neem-based products (neem oil / neem seed kernel extract)", "Repel and reduce whiteflies, aphids, jassids and thrips; gentler on natural enemies."),
        ("Beauveria bassiana (bio-insecticide)", "A beneficial fungus that infects sucking pests and some caterpillars."),
    ],
    "caterpillar": [
        ("Bt (Bacillus thuringiensis) bio-insecticide", "Kills young caterpillars that eat it; safe for most beneficial insects."),
        ("NPV (nuclear polyhedrosis virus) for Helicoverpa or Spodoptera", "A pest-specific virus sold by KVKs and bio-input labs."),
        ("Neem-based products", "Discourage egg-laying and feeding by young caterpillars."),
    ],
}

# Which bio-option groups apply to each disease type from diseases.py.
DISEASE_TYPE_TO_BIO = {
    "fungal": ["fungal_leaf"],
    "oomycete": ["fungal_leaf"],
    "bacterial": ["fungal_leaf"],
    "pest (mite)": ["sucking_pest"],
    "viral (spread by whitefly)": ["sucking_pest"],
    "bacterial (spread by psyllid insect)": ["sucking_pest"],
}

BIOFERTILIZERS = {
    "legume": ("Rhizobium culture (strain for your crop)", "Seed treatment that helps the crop fix its own nitrogen from the air."),
    "cereal": ("Azospirillum culture", "Seed or soil treatment that supplies part of the crop's nitrogen."),
    "other": ("Azotobacter culture", "Seed or soil treatment that supplies part of the crop's nitrogen."),
    "all": ("PSB (Phosphate Solubilising Bacteria)", "Makes soil phosphorus more available, so fertilizer phosphorus goes further."),
}

PESTICIDE_SAFETY = [
    "Spray a chemical only when pest or disease damage is clearly increasing, not as routine 'insurance'.",
    "Buy only products with a CIB&RC registration number on the label, from a licensed dealer, with a proper bill.",
    "Tell the dealer your exact crop and problem. Use only a product whose label lists your crop and pest.",
    "Use the dose written on the label. Never mix more than the label says, and never mix products on your own.",
    "Wear gloves, a mask, full sleeves and closed footwear while mixing and spraying. Do not eat, drink or smoke.",
    "Do not spray in strong wind, before rain, or in the hot afternoon. Use the spray windows on the Farm Weather page.",
    "Follow the waiting period (pre-harvest interval) on the label before picking produce.",
    "Keep chemicals locked away from children and food. Never reuse empty containers; puncture and dispose of them safely.",
]

WHERE_TO_BUY = [
    {"name": "Licensed fertilizer and pesticide dealer", "note": "Always ask for a printed bill and check the batch number and expiry date."},
    {"name": "Pradhan Mantri Kisan Samriddhi Kendra (PMKSK)", "note": "Government-designated one-stop shops for fertilizers, seeds and soil testing information."},
    {"name": "Primary Agricultural Credit Society (PACS) / cooperative", "note": "Often sells fertilizers at government-notified prices to members."},
    {"name": "Krishi Vigyan Kendra (KVK) / state agriculture department", "note": "Good source for bio-fertilizers, bio-pesticides, traps and quality seed."},
    {"name": "State Seed Corporation / authorised seed dealer", "note": "Buy seed with a Certified (blue) tag or Truthfully Labelled tag, and keep the bill."},
]
